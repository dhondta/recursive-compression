#!/usr/bin/env python
# -*- coding: UTF-8 -*-
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
    :param logger:  logging
    """
    not_first = ["lzma", "xz"]
    
    def __init__(self, *files, **kwargs):
        super(Compressor, self).__init__(kwargs.pop("logger"))
        # setup the compressor
        self.charset = kwargs.pop("charset", ascii_letters + digits)
        self.n = kwargs.pop("n", 8)
        self.rounds = kwargs.pop("rounds", 1000)
        self.files = sorted([f for f in files if exists(f)])
        if len(self.files) == 0:
            self.logger.error("No existing file to be archived")
            sys.exit(2)
        self._bad_formats = []
        self._last = None
        self._pbar = kwargs.pop("pbar")
        self._to_temp_dir(*self.files, move=kwargs.pop("move", False))
        # compress input files
        self.__compress()
        # tear down the decompressor
        if self.round > 0:
            self.logger.info("Rounds:  {}".format(self.round))
            self.logger.info("Archive: {}".format(self.files[0]))
        self._to_orig_dir()
    
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
        name, new = None, None
        for i in (self._pbar(self.rounds) or range(self.rounds)):
            if Base.interrupted:
                break
            self.round = i + 1
            # compress files
            self.logger.debug("Compressing '{}'..."
                              .format(new or "', '".join(self.files)))
            new = self.__rec_compress(self.name, self.files)
            # cleanup previous archive
            if i > 0:
                f = self.files[0]
                remove(f)
            self.files = [new]
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
    
    def __rec_compress(self, name, files, **kwargs):
        # choose a random compression algorithm amongst available ones
        try:
            ext = self.ext
            self.logger.debug(ext)
            tname = "{}.{}".format(name, ext)
            old = set(listdir("."))
            compress(tname, files, **kwargs)
            tname = self.__new_archive(old)
            name, _ = splitext(tname)
            rename(tname, name)
            return name
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
            return self.__rec_compress(name, files, **kwargs)
