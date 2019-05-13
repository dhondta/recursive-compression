#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import codecs
import logging
import shutil
from magic import from_file as get_magic
from os import chdir, getcwd, listdir, makedirs
from os.path import basename, exists, join, splitext
from patoolib import create_archive, extract_archive, ArchivePrograms
from patoolib.util import PatoolError
from random import choice
from signal import getsignal, signal, SIGINT
from six import b
from tinyscript import hashlib
from tinyscript.helpers import silent


__all__ = ["b", "codecs", "compress", "decompress", "hashlib", "shutil", "Base",
           "PatoolError"]


SHORTNAMES = {'bzip2': "bz2", 'gzip': "gz"}
SUBSTITUTIONS = {'shell': "shar", '7-zip': "7z"}
COMPR_FORMATS = [SHORTNAMES.get(k, k) for k, v in ArchivePrograms.items()\
                 if v.get('create') is not None or None in v.keys()]
DECOMPR_FORMATS = [k for k, v in ArchivePrograms.items() \
                   if v.get('extract') is not None or None in v.keys()]


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
        return args[0], extract_archive(*args, **kwargs)
    except PatoolError:
        return args[0], None


class Base(object):
    """ Dummy base class for setting up an interrupt handler. """
    files = {}
    interrupted = False
    not_multiple = ["bzip2", "lzma", "shell", "xz"]
    temp_dir = "/tmp/recursive-compression"

    def __init__(self, formats=None, logger=None):
        if logger is None:
            logger = logging.getLogger("main")
            logger.addHandler(logging.NullHandler())
        self.cwd = getcwd()
        self.logger = logger
        self._id = 0
        self._last = None
        self.__sigint_handler = getsignal(SIGINT)
        signal(SIGINT, self.__interrupt)
        self.__valid_formats = [f for f in COMPR_FORMATS if f in formats] \
                         if formats not in [None, "*", "all"] else COMPR_FORMATS
    
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
    def arch_name(self):
        """
        Choose a non-existing random archive filename.
        """
        if self.round == 1 and len(self.files) == 1:
            return self.files[0]
        name = "".join(choice(self.charset) for i in range(self.n))
        while exists(name):
            name = "".join(choice(self.charset) for i in range(self.n))
        return name
    
    @property
    def ext(self):
        """
        Choose a random valid archive extension.
        """
        algos = set(self.__valid_formats).difference(set(self._bad_formats)) \
                                         .difference(set(self._wrong_formats))
        if len(self.files) > 1:
            algos = algos.difference(set(self.not_multiple))
        if len(algos) == 0:
            return
        ext = choice(list(algos - set([self._last] if len(algos) > 1 else [])))
        self._last = ext
        return ext
    
    @property
    def temp_name(self):
        """
        Choose a non-existing random temporary archive filename.
        
        Note: This is aimed to avoid collisions when an archive is decompressed
               to its own name without its extension while another previous
               archive exists with the same name.
        """
        a, n = "0123456789abcdef", 64
        filenames = [f for f, e in [splitext(fn) for fn in listdir(".")]]
        name = "".join(choice(a) for i in range(n))
        while name in filenames:
            name = "".join(choice(a) for i in range(n))
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
            if t in DECOMPR_FORMATS:
                return " ".join(m), SHORTNAMES.get(t, t)
        return " ".join(m), None
