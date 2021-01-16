#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import math
import sys
from os import listdir, remove, rename
from os.path import abspath, basename, exists, isfile, join, splitext
from string import ascii_letters, digits, printable
from tinyscript.helpers import pause

from .base import *
from .decompressor import *


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
        files = kwargs.get("files", [])
        super(Compressor, self).__init__(**kwargs)
        for f in files:
            self._hashes[basename(f)] = hashlib.sha256_file(f)
        # setup the compressor
        self.charset = kwargs.get("charset", ascii_letters + digits)
        self.n = kwargs.get("n", 8)
        self.rounds = max(1, kwargs.get("rounds", 1000))
        files = sorted([f for f in files if exists(f)])
        if len(files) == 0:
            self.logger.error("No existing file to be archived")
            sys.exit(2)
        # split the data to be embedded if relevant
        self.data, data, self.chunks = [], kwargs.get("data"), 1
        if data is not None:
            self.chunks = min(kwargs.get("chunks", 10),
                              len(data),
                              self.rounds - 1)
            n = int(math.ceil(float(len(data)) / self.chunks))
            self.data = data[::-1]
            self.data = [self.data[i:i+n] for i in range(0, len(data), n)]
        self._bad_formats, self._wrong_formats = [], []
        self._to_temp_dir(*files, move=kwargs.get("move", False))
        # initialize internal state
        self.files = files
        self._used_formats = []
        self._last = None
        self._pbar = kwargs.get("pbar", lambda x: None)
        # compress input files
        self.__compress()
        if len(self.files) == 0:
            return
        # if required, check for correct compression ; retry if relevant
        if kwargs.get("fix", False) and not self.__without_error():
            # if integrity error, simply retry
            self._to_orig_dir(move=False)
            c = Compressor(**kwargs)
            return
        a = self.files[0]
        # tear down the decompressor
        self._to_orig_dir()
        if self.round > 0:
            self.logger.info("Rounds : {}".format(self.round))
            l = list(sorted(set(self._used_formats)))
            self.logger.info("Algos  : {}".format(len(l)))
            self.logger.debug("[i] Used algorithms: {}".format(",".join(l)))
            self.logger.info("Archive: {}".format(a))
        # reverse bytes if needed
        if kwargs.get("reverse", False):
            with open(a, 'wb+') as f:
                content = f.read()[::-1]
                f.seek(0)
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
        ext = self.ext
        if ext is None:
            self.logger.critical("No valid compression algorithm available")
            if len(self._bad_formats) > 0:
                self.logger.error("Bad formats:\n- {}"
                                  .format("\n- ".join(self._bad_formats)))
            if len(self._wrong_formats) > 0:
                self.logger.error("Wrong formats:\n- {}"
                                  .format("\n- ".join(self._wrong_formats)))
            return False
        self.logger.debug(ext)
        tname = "{}.{}".format(name, ext)
        try:
            # snapshot files listing, compress and get the difference
            old = set(listdir("."))
            import os
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
            self._used_formats.append(ext)
            return True
        except PatoolError as e:
            s = str(e)
            if "unknown archive format" in s:
                self.logger.debug("[!] Unknown format")
                self._bad_formats.append(ext)
            elif "could not find an executable program" in s or \
                ("archive format" in s and "not supported" in s):
                self.logger.debug("[!] No tool for this format")
                self._bad_formats.append(ext)
            elif "file " in s and " was not found" in s:
                self.logger.warning("[!] Bad input file")
                f = s.split("`")[1].split("'")[0]
                self.files.remove(f)
                if len(self.files) == 0:
                    self.logger.critical("Nothing more to compress")
                    sys.exit(1)
            else:
                self.logger.debug("[!] Patool error ({})".format(s))
                self._wrong_formats.append(ext)
            return self.__rec_compress(clean=clean, **kwargs)
    
    def __without_error(self):
        """
        This decompresses the newly created archive to check for file integrity
         and returns whether the compression was done without error.
        """
        d = Decompressor(archive=self.files[0], logger=self.logger, silent=True,
                         temp_dir="/tmp/recursive-decompression")
        if self.rounds != d.rounds:
            self.logger.debug("[!] integrity check failed (different rounds)")
            return False
        for fp, h_before in self._hashes.items():
            h_after = (d._hashes.get(fp) or [None])[0]
            if h_before != h_after:
                self.logger.debug("[!] integrity check failed (bad file)")
                return False
        self.logger.debug("[i] integrity check passed")
        return True
