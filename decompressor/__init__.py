#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import shutil
import sys
from collections import deque
from os import chdir, getcwd, getpid, kill, listdir, makedirs, remove
from os.path import basename, exists, join
from signal import getsignal, signal, SIGINT
from six import b, u
from string import printable
from subprocess import check_output as chout, CalledProcessError, PIPE


__all__ = ["RecursiveDecompressor"]


def check_output(*args, **kwargs):
    try:
        return chout(list(map(b, args[0])), *args[1:], **kwargs)
    except (AttributeError, CalledProcessError):  # can occur when Ctrl+C
        pass


class RecursiveDecompressor(object):
    """
    This handles decompression according to multiple algorithms in a temporary
     folder. It only keeps a low number of previously decompressed files not to
     consume to much space on the disks. Also, if multiple files are present in
     an archive, it handles the first one from this instance and opens new ones
     for handling the next files.
    
    :param archive: archive path or filename
    :param keep:    number of archive levels to be kept after decompression
    :param display: display the final result at the end of the decompression
    :param move:    move the in-scope archive to the temporary folder, do not
                     simply copy it
    :param logger:  logging
    """
    cleanup_len = 2
    cwd = getcwd()
    formats = {
        "7-zip archive data":    (["7za", "e"], "7z"),
        "ARJ archive data":      (["arj", "e"], "arj"),
        "bzip2 compressed data": (["bzip2", "-df"], "bz2"),
        "POSIX tar archive":     (["tar", "-xvf"], "tar"),
        "RAR archive data":      (["unrar", "e"], "rar"),
        "XZ compressed data":    (["unxz", "-df"], "xz"),
        "LZMA compressed data":  (["lzma", "-df"], "lzma"),
        "gzip compressed data":  (["gunzip", "-df"], "gz"),
        "Zip archive data":      (["unzip"], "zip"),
    }
    temp_dir = "/tmp/recursive-decompressor-{}"
    
    def __init__(self, archive, keep=1, display=False, move=False, logger=None):
        self.logger = logger
        if self.__check() > 0:
            if logger is not None:
                logger.critical("Some tools are not installed ; please install"
                                " them before continuing")
            sys.exit(1)
        # setup the decompressor
        self.__sigint_handler = getsignal(SIGINT)
        signal(SIGINT, self.__interrupt)
        self.__id = 0
        self.__cleanup = deque([], max(keep, self.cleanup_len))
        self.__disp, self.__keep = display, keep
        self.__result = False
        self._interrupted = False
        self.temp_dir = RecursiveDecompressor.temp_dir.format(self.__id)
        while exists(self.temp_dir):
            self.__id += 1
            self.temp_dir = RecursiveDecompressor.temp_dir.format(self.__id)
        makedirs(self.temp_dir)
        archive_name, self._result = basename(archive), None
        getattr(shutil, ["copy", "move"][move]) \
            (archive, join(self.temp_dir, archive_name))
        chdir(self.temp_dir)
        self.archives = [archive_name]
        # decompress until it cannot be anymore
        RecursiveDecompressor.count = 0
        while self.decompress() is not None:
            continue
        # tear down the decompressor
        if not self._interrupted:
            if keep > 0:
                self.__copy()
            for i in range(keep):
                self.__copy(self.__cleanup.pop())
        else:
            self.__copy(self.__cleanup[-1])
        chdir(self.cwd)
        shutil.rmtree(self.temp_dir)
    
    def __check(self):
        """
        This checks if the decompression tools are installed.
        
        :return: number of non-installed tools
        """
        e = 0
        for cmd, _ in self.formats.values():
            tool = cmd[0]
            bad = True
            for cmd in [[tool], [tool, "--version"], [tool, "-v"]]:
                try:
                    check_output(cmd, stdin=PIPE, stderr=PIPE)
                    bad = False
                    break
                except:
                    pass
            if bad:
                e += 1
                m = "'{}' is not installed".format(tool)
                if self.logger is not None:
                    self.logger.warning(m)
                else:
                    print(m)
        return e
    
    def __copy(self, archive=None):
        """
        Shortcut for copying an archive from the temporary folder.
        """
        _ = self.archives if archive is None else [archive]
        for a in _:
            try:
                shutil.copy(a, join(self.cwd, a))
            except IOError:  # can occur when a tool removes the archive once
                pass         #  decompressed
    
    def __interrupt(self, *args):
        """
        Custom handler for setting internal state to interrupted when SIGINT is
         received.
        """
        self._interrupted = True
        signal(SIGINT, self.__sigint_handler)
    
    def decompress(self):
        """
        This decompresses the first archive from the current list of in-scope
         archives. If more than one archive must be handled, it recursively
         opens new instances of RecursiveDecompressor.
        
        :return: first filename from the decompressed archive (None if the
                  current file to be decompressed cannot be handled by a
                  decompressor ; i.e. if it is the final decompressed data,
                  unless it is compressed with an out-of-scope decompressor)
        """
        if self._interrupted:
            return
        for i, archive in enumerate(self.archives[:]):
            if i > 0:
                # start a new recursive decompression (other temporary folder)
                child = RecursiveDecompressor(archive, self.__keep, self.__disp,
                                              True)
                if child._interrupted:
                    kill(getpid(), SIGINT)
                # then come back to the current temporary folder
                chdir(self.temp_dir)
                continue
            # check for archive format
            ft = check_output(["file", archive], stderr=PIPE).strip()
            ft = b(" ").join(ft.split(b(':'), 1)[1].split()[:3]).rstrip(b(','))
            ft = ft.decode()
            if self.logger is not None:
                self.logger.debug(ft)
            try:
                cmd, ext = self.formats[ft]
            except KeyError:  # if the archive format is unknown, stop recursion
                if self.logger is not None:
                    self.logger.warn("Nothing more to decompress")
                    self.logger.info("Files: {}"
                                     .format(", ".join(self.archives)))
                self.__cleanup.append(archive)
                if self.__disp:
                    try:
                        with open(archive, 'rb') as f:
                            content = f.read().strip().decode()
                            n = sum([str(c) in printable for c in content])
                            if float(n) / len(content) < .9:
                                content = "<<< Non-printable content >>>"
                            if self.logger is not None:
                                self.logger.success(content)
                            else:
                                print(content)
                    except Exception as e:
                        if self.logger is not None:
                            self.logger.failure(str(e))
                return
            # if the extension must be enforced, update archive's filename
            if ext is not None:
                if not ext.startswith("."):
                    ext = "." + ext
                if not archive.endswith(ext):
                    shutil.move(archive, archive + ext)
                    archive += ext
            self.__cleanup.append(archive)
            # now decompress, finding the decompressed file by applying a diff
            #  with the old directory listing
            old = set(listdir("."))
            if self.logger is not None:
                self.logger.info("Decompressing '{}'...".format(archive))
            try:
                _ = check_output(list(cmd) + [archive], stdin=PIPE, stderr=PIPE)
            except:
                pass
            self.archives = list(set(listdir(".")) - old) or [archive]
            if self.logger is not None:
                for a in self.archives:
                    self.logger.debug("=> {}".format(a))
        if len(self.__cleanup) == self.__cleanup.maxlen:
            try:
                remove(self.__cleanup.popleft())
            except OSError:  # occurs when the decompression tool already
                pass         #  removes the old archive by itself
        return self.archives[0]
