#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from collections import deque
from os import listdir, remove, rename
from os.path import basename, isdir, join

from .base import *


__all__ = ["Decompressor"]


class Decompressor(Base):
    """
    This handles decompression according to multiple algorithms in a temporary
     folder. It only keeps a low number of previously decompressed files not to
     consume to much space on the disks. Also, if multiple files are present in
     an archive, it handles the first one from this instance and opens new ones
     for handling the next files.
    
    :param archive: archive path or filename
    :param display: display the final result at the end of the decompression
    :param move:    move the in-scope archive to the temporary folder, do not
                     simply copy it
    :param logger:  logging
    """
    cleanup_len = 2
    
    def __init__(self, archive, display=False, move=False, logger=None):
        super(Decompressor, self).__init__(logger)
        aname = basename(archive)
        # setup the decompressor
        self.__cleanup = deque([], self.cleanup_len)
        self.__disp = display
        self.archives = [aname]
        self.results = []
        self._to_temp_dir(aname, move=move)
        # decompress until it cannot be anymore
        self.rounds = 0
        while len(self.archives) > 0:
            self.__decompress()
        files = sorted(self.files.keys())
        # tear down the decompressor
        if self.rounds > 0 and not Base.interrupted:
            self.logger.info("Rounds: {}".format(self.rounds))
            self.logger.info("File{}".format(["  :", "s :"][len(files) > 1]))
            for f, i in sorted(self.files.items(), key=lambda x: x[0]):
                h, c = i
                print("- {} ({}){}".format(f, h, ["", " x{}".format(c)][c > 1]))
        if Base.interrupted:
            self.__copy()
        self._to_orig_dir()
    
    def __copy(self, archive=None):
        """
        Shortcut for copying an archive from the temporary folder.
        """
        _ = self.archives if archive is None else [archive]
        for a in _:
            n = Decompressor.ensure_new(join(self.cwd, a))
            try:
                shutil.copy(a, n)
            except IOError:  # can occur when a tool removes the archive once
                pass         #  decompressed

    def __decompress(self):
        """
        This decompresses the first archive from the current list of in-scope
         archives. If more than one archive must be handled, it recursively
         opens new instances of Decompressor.
        
        :return: first filename from the decompressed archive (None if the
                  current file to be decompressed cannot be handled by a
                  decompressor ; i.e. if it is the final decompressed data,
                  unless it is compressed with an out-of-scope decompressor)
        """
        a = self.archives.pop()
        magic, ext = Decompressor.format(a)
        if ext is None or Base.interrupted:
            shutil.move(a, Decompressor.ensure_new(join(self.cwd, a)))
            self.logger.debug(magic)
            return
        # rename file with its archive extension if relevant
        new = "{}.{}".format(a, ext) if ext not in a else a
        if new != a:
            rename(a, new)
        self.__cleanup.append(new)
        # now decompress
        old = set(listdir("."))
        self.logger.debug("Decompressing '{}'...".format(new))
        self.__new_files(old, decompress(new))
        if Base.interrupted:
            shutil.move(a, Decompressor.ensure_new(join(self.cwd, a)))
            return
        self.rounds += 1
        # cleanup old archives
        if len(self.__cleanup) == self.__cleanup.maxlen:
            try:
                remove(self.__cleanup.popleft())
            except OSError:  # occurs when the decompression tool already
                pass         #  removed the old archive by itself
    
    def __new_files(self, old, archive=None):
        """
        This determines and updates the list of decompressed files for the next
         iteration.
        
        :param old:     previous directory listing
        :param archive: new archive name
        """
        # find the decompressed file by a diff with the old directory listing
        new = list(set(listdir(".")) - old)
        # if the result is a folder ; the archive is assumed to have been
        #  decompressed to this folder, then move every file to the current dir
        if len(new) == 1 and isdir(new[0]):
            for f in listdir(new[0]):
                rename(join(new[0], f), f)
            shutil.rmtree(new[0])
        # find the decompressed files by a diff with the old directory listing
        new = list(set(listdir(".")) - old)
        # now sort decompressed files, displaying usual files if relevant and
        #  adding new archives to the list for future decompression
        for f in new:
            ext = Decompressor.format(f)
            if ext is None:
                if self.__disp:
                    try:
                        with open(f, 'rb') as fr:
                            c = fr.read().strip().decode()
                            n = sum([str(_) in printable for _ in c])
                            if float(n) / len(c) < .9:
                                c = "<<< Non-printable content >>>"
                            getattr(self.logger, "success", self.logger.info)(c)
                    except:
                        pass
                h, nf, nfp = hashlib.sha256_file(f), f, join(self.cwd, f)
                while True:                
                    oh, c = self.files.get(nf) or (None, 0)
                    # if same hashes, increment count ; if count=0, create entry
                    if oh == h or c == 0:
                        self.files[nf] = (h, c + 1)
                        shutil.move(nf, nfp)
                        break
                    # otherwise, update filename to something not existing
                    else:
                        nfp = Decompressor.ensure_new(join(self.cwd, nf))
                        nf = basename(nfp)
                        # and re-control that it does not exist in files list
                        # NOTE: we do care about files with same hashes as the
                        #        filename could be valuable information ; so, we
                        #        don't check if the hash matches this of another
                        #        file in the self.files dictionary
            else:
                self.archives.insert(0, f)
            self.logger.debug("=> {}".format(f))
