#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import math
import sys
from os import listdir, remove, rename
from os.path import exists, isfile, join, splitext
from string import ascii_letters, digits, printable

from .base import *


__all__ = ["Compressor"]


class Compressor(Base):
    """
    This handles compression according to multiple algorithms to the destination
     folder.
    
    :param files:   list of files to be archived
    :param charset: charset to be used for generating random archive names
    :param n:       length of random archive names
    :param rounds:  number of compression rounds
    :param reverse: reverse byte order
    :param logger:  logging
    :param data:    hidden data to be embedded in the nested archives
    :param chunks:  number of chunks the data is to be split in
    """
    def __init__(self, **kwargs):
        files = kwargs.pop("files", [])
        super(Compressor, self).__init__(formats=kwargs.pop("formats"),
                                         logger=kwargs.pop("logger"))
        # setup the compressor
        self.charset = kwargs.pop("charset", ascii_letters + digits)
        self.n = kwargs.pop("n", 8)
        self.rounds = max(1, kwargs.pop("rounds", 1000))
        self.files = sorted([f for f in files if exists(f)])
        if len(self.files) == 0:
            self.logger.error("No existing file to be archived")
            sys.exit(2)
        self._bad_formats = []
        self._wrong_formats = []
        self._last = None
        self._pbar = kwargs.pop("pbar", lambda x: None)
        self._to_temp_dir(*self.files, move=kwargs.pop("move", False))
        # split the data to be embedded if relevant
        self.data, data, self.chunks = [], kwargs.pop("data"), 1
        if data is not None:
            self.chunks = min(kwargs.pop("chunks", 10),
                              len(data),
                              self.rounds - 1)
            n = int(math.ceil(float(len(data)) / self.chunks))
            self.data = data[::-1]
            self.data = [self.data[i:i+n] for i in range(0, len(data), n)]
        # compress input files
        self.__compress()
        a = self.files[0]
        # tear down the decompressor
        if self.round > 0:
            self.logger.info("Rounds:  {}".format(self.round))
            self.logger.info("Archive: {}".format(a))
        self._to_orig_dir()
        # reverse bytes if needed
        if kwargs.pop("reverse", False):
            with open(a, 'rb') as f:
                content = f.read()[::-1]
            with open(a, 'wb') as f:
                f.write(content)
    
    def __compress(self):
        """
        This compresses input files with the given number of compression rounds
         using a random algorithm from the list.
        
        :param files: files to be compressed
        :return: first filename from the decompressed archive (None if the
                  current file to be decompressed cannot be handled by a
                  decompressor ; i.e. if it is the final decompressed data,
                  unless it is compressed with an out-of-scope decompressor)
        """
        name = None
        step = max(1, self.rounds // self.chunks)
        for i in (self._pbar(self.rounds) or range(self.rounds)):
            if Base.interrupted:
                break
            # format embedded data chunk if relevant
            if len(self.data) > 0 and i > 0 and self.round % step == 0:
                a = codecs.encode(b(self.data.pop()), 'hex_codec')
                with open(a, 'wb') as f:
                    f.write(b(""))
                self.files.append(a)
            self.round = i + 1
            # compress files
            self.logger.debug("Compressing '{}'..."
                              .format("', '".join(self.files)))
            if not self.__rec_compress(clean=i > 0):
                return
        for f in self.files:
            shutil.move(f, join(self.cwd, f))
    
    def __new_archive(self, old):
        """
        This determines the name of the new compressed archive.
        
        :param old:     previous directory listing
        """
        # find the decompressed file by a diff with the old directory listing
        new = list(set(listdir(".")) - old)
        new = list(filter(isfile, new))
        # if we don't just have one more item, we have a problem...
        if len(new) == 0:
            raise Exception("No new file")
        elif len(new) > 1:
            raise Exception("Too much new files")
        self.logger.debug("=> {}".format(new[0]))
        return new[0]
    
    def __rec_compress(self, **kwargs):
        """
        This recursively tries to compress the input files with a compression
         algorithm randomly chosen from the available ones until it succeeds.
         It relies on Patool.
        """
        name = self.arch_name
        clean = kwargs.pop("clean", True)
        # choose a random compression algorithm amongst available ones
        try:
            ext = self.ext
            if ext is None:
                self.logger.critical("No valid compression algorithm available")
                self.logger.error("Bad formats:\n- {}"
                                  .format("\n- ".join(self._bad_formats)))
                self.logger.error("Wrong formats:\n- {}"
                                  .format("\n- ".join(self._wrong_formats)))
                return False
            self.logger.debug(ext)
            tname = "{}.{}".format(name, ext)
            # snapshot files listing, compress and get the difference
            old = set(listdir("."))
            compress(tname, self.files, **kwargs)
            tname = self.__new_archive(old)
            name, _ = splitext(tname)
            rename(tname, name)
            # cleanup previous files
            if clean:
                for f in self.files:
                    if name != f:
                        remove(f)
            self.files = [name]
            self._wrong_formats = []
            return True
        except PatoolError as e:
            if "unknown archive format" in str(e):
                self.logger.debug("[!] Unknown format")
                self._bad_formats.append(ext)
            elif "could not find an executable program" in str(e) or \
                ("archive format" in str(e) and "not supported" in str(e)):
                self.logger.debug("[!] No tool for this format")
                self._bad_formats.append(ext)
            else:
                self.logger.debug("[!] Patool error")
                self._wrong_formats.append(ext)
            return self.__rec_compress(**kwargs)
