#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
import shutil
from magic import from_file as get_magic
from os import chdir, getcwd, makedirs
from os.path import basename, exists, join, splitext
from patoolib import create_archive, extract_archive, ArchivePrograms
from patoolib.util import PatoolError
from random import choice
from signal import getsignal, signal, SIGINT
from tinyscript import hashlib
from tinyscript.helpers import silent


__all__ = ["compress", "decompress", "hashlib", "shutil", "Base", "PatoolError"]


SHORTNAMES = {'bzip2': "bz2", 'gzip': "gz"}
SUBSTITUTIONS = {'shell': "shar"}
VALID_COMPR_FORMATS = [SHORTNAMES.get(k, k) for k, v in \
                       ArchivePrograms.items() if v.get('create') is not None]
VALID_DECOMPR_FORMATS = [k for k, v in ArchivePrograms.items() \
                         if v.get('extract') is not None]


@silent
def compress(*args, **kwargs):
    """ Alias for patool.create_archive, silencing verbose messages. """
    kwargs['verbosity'] = -1
    return create_archive(*args, **kwargs)


@silent
def decompress(*args, **kwargs):
    """ Alias for patool.extract_archive, silencing verbose messages. """
    kwargs['verbosity'] = -1
    try:
        return extract_archive(*args, **kwargs)
    except PatoolError:
        return args[0]


class Base(object):
    """ Dummy base class for setting up an interrupt handler. """
    files = {}
    interrupted = False
    temp_dir = "/tmp/reccomp-{}"

    def __init__(self, logger=None):
        if logger is None:
            logger = logging.getLogger("main")
            logger.setHandler(logging.NullHandler())
        self.cwd = getcwd()
        self.logger = logger
        self._id = 0
        self.__sigint_handler = getsignal(SIGINT)
        signal(SIGINT, self.__interrupt)
    
    def __interrupt(self, *args):
        """
        Custom handler for setting internal state to interrupted when SIGINT is
         received.
        """
        Base.interrupted = True
        signal(SIGINT, self.__sigint_handler)
    
    def _to_orig_dir(self):
        """
        This changes directory back to the original one and removes the
         temporary folder.
        """
        chdir(self.cwd)
        shutil.rmtree(self.temp_dir)
    
    def _to_temp_dir(self, *files, **kwargs):
        """
        This creates a temporary folder, copies (moves if kwargs['move']=True)
         the specified files to this folder and then change directory to this.
        
        :param files: files to be copied/moved
        :param move:  whether files should be moved or not
        """
        move = kwargs.pop("move", False)
        if exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        makedirs(self.temp_dir)
        for fp in files:
            fn = basename(fp)
            getattr(shutil, ["copy", "move"][move])(fp, join(self.temp_dir, fn))
        chdir(self.temp_dir)
    
    @property
    def ext(self):
        """
        Choose a random valid archive extension.
        """
        ext = choice(VALID_COMPR_FORMATS)
        while ext in self._bad_formats or ext == self._last or \
            (self.round == 1 and ext in self.not_first):
            if self.round == 1 and ext in self.not_first:
                self.logger.debug(ext)
                self.logger.debug("[!] This format can't be used at round 1")
            ext = choice(VALID_COMPR_FORMATS)
        self._last = ext
        return ext
    
    @property
    def name(self):
        """
        Choose a non-existing random filename.
        """
        name = "".join(choice(self.charset) for i in range(self.n))
        while exists(name):
            name = "".join(choice(self.charset) for i in range(self.n))
        return name
    
    @staticmethod
    def ensure_new(filename):
        """
        Simple function to ensure a filename that does not exist yet.
        
        :param filename: source filename
        :return:         destination filename, guaranteed unique
        """
        i = 0
        while exists(filename):
            arch, ext = splitext(filename)
            try:
                p = arch.split("-")
                i = int(p[-1])
                arch = "-".join(p[:-1])
            except ValueError:
                pass
            i += 1
            filename = "{}-{}{}".format(arch, i, ext)
        return filename        
    
    @staticmethod
    def format(archive):
        """
        This determines the archive format.
        
        :param archive: filename
        :return:        archive extension if filename is an archive, else None
        """
        m = get_magic(archive).split(",", 1)[0].split()
        ext = None
        for t in m:
            t = t.lower()
            t = SUBSTITUTIONS.get(t, t)
            if t in VALID_DECOMPR_FORMATS:
                return m, SHORTNAMES.get(t, t)
        return m, None
