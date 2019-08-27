#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from collections import deque
from os import listdir, remove, rename
from os.path import basename, exists, isdir, join, splitext
from string import printable

from .base import *


__all__ = ["Decompressor"]


HASH_EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class Decompressor(Base):
    """
    This handles decompression according to multiple algorithms in a temporary
     folder. It only keeps a low number of previously decompressed files not to
     consume to much space on the disks. Also, if multiple files are present in
     an archive, it handles the first one from this instance and opens new ones
     for handling the next files.
    
    :param archive: archive path or filename
    :param display: display the final result at the end of the decompression
    :param delete:  move the in-scope archive to the temporary folder, do not
                     simply copy it
    :param logger:  logging
    """
    cleanup_len = 2
    
    def __init__(self, **kwargs):
        archive = kwargs.get("archive", None)
        display = kwargs.get("display", False)
        move = kwargs.get("delete", False)
        super(Decompressor, self).__init__(**kwargs)
        aname = basename(archive)
        # setup the decompressor
        if self.cwd == self.temp_dir:
            self.logger.warning("Decompressing from the input location ; this"
                                " may cause unexpected errors")
        self.__cleanup = deque([], self.cleanup_len)
        self.__disp = display
        self.archives = [aname]
        self.data = ""
        self.last = aname
        self._to_temp_dir(archive, move=move)
        # decompress until it cannot be anymore
        self.rounds = 0
        while len(self.archives) > 0:
            self.__decompress()
        # try to reverse bytes if first round did not decompress
        if self.rounds == 1 and len(self._hashes) == 1:
            self.rounds = 0
            self.archives = list(self._hashes.keys())
            self._to_orig_dir()
            self._to_temp_dir(archive, move=move)
            self.logger.debug("Reversing bytes...")
            # TODO: improve file reversing
            #  (problem: file should be reversed by block to also handle huge
            #             archives)
            with open(aname, 'rb') as f:
                content = f.read()
            with open(aname, 'wb') as f:
                f.write(content[::-1])
            while len(self.archives) > 0:
                self.__decompress()
        files = sorted(list(self._hashes.keys()))
        # tear down the decompressor
        if self.rounds > 0 and not Base.interrupted and not self._silent:
            l = list(sorted(set(self._used_formats)))
            if len(l) == 0:
                self.logger.error("Decompression failed")
                self.logger.warning("If you are sure this is an archive, it "
                                    "maybe obfuscated with an unknown encoding")
                self._to_orig_dir()
                return
            self.logger.info("Rounds: {}".format(self.rounds))
            self.logger.info("Algos : {}".format(len(l)))
            self.logger.debug("[i] Used algorithms: {}".format(",".join(l)))
            self.logger.info("File{}".format(["  :", "s :"][len(files) > 1]))
            for f in files:
                h, c = self._hashes[f]
                print("- {} ({}){}".format(f, h, ["", " x{}".format(c)][c > 1]))
            if len(self.data) > 0:
                try:
                    d = codecs.decode(b(self.data), 'hex_codec')[::-1]
                    getattr(self.logger, "success", self.logger.info) \
                        ("Data: {}".format(d))
                except:
                    pass
        self._to_orig_dir()

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
        if Base.interrupted:
            shutil.move(a, Decompressor.ensure_new(join(self.cwd, a)))
            self.logger.debug(magic)
            return
        # rename file with its archive extension if relevant
        new = "{}.{}".format(self.temp_name, ext)
        rename(a, new)
        self.__cleanup.append((a, new))
        # now decompress
        old = set(listdir("."))
        self.logger.debug("Decompressing '{}' ({})...".format(a, magic))
        self.__new_files(old, a, new, decompress(new))
        if ext is not None:
            self._used_formats.append(ext)
        if Base.interrupted:
            shutil.move(new, Decompressor.ensure_new(join(self.cwd, a)))
            return
        self.rounds += 1
        # cleanup old archives
        if len(self.__cleanup) == self.__cleanup.maxlen:
            try:
                remove(self.__cleanup.popleft()[1])
            except OSError:  # occurs when the decompression tool already
                pass         #  removed the old archive by itself
    
    def __new_files(self, old, arch_name, temp_name, target):
        """
        This determines and updates the list of decompressed files for the next
         iteration.
        
        :param old:       previous directory listing
        :param arch_name: original archive name
        :param temp_name: new archive name
        :param target:    extracted target name
        """
        tn = splitext(temp_name)[0]
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
        warn = not self._silent
        if self.rounds == 0 and len(new) == 0:
            rename(temp_name, arch_name)
            new = [arch_name]
            warn = False
        # now sort decompressed files, displaying usual files if relevant and
        #  adding new archives to the list for future decompression
        for f in new:
            _, ext = Decompressor.format(f)
            if ext is None:
                h = hashlib.sha256_file(f)
                # if empty file, consider it as hidden data
                if h == HASH_EMPTY:
                    self.data += f
                    remove(f)
                    self.logger.debug("=> {}".format(f))
                    continue
                if len(new) == 1 and self.last[1] in self.not_multiple:
                    f = self.last[0]
                    if not exists(f):
                        shutil.move(self.__cleanup[-1][1], f)
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
                nf, nfp = f, join(self.cwd, f)
                while True:
                    old_h, c = self._hashes.get(nf) or (None, 0)
                    # if same hashes, increment count ; if count=0, create entry
                    if old_h == h or c == 0:
                        self._hashes[nf] = (h, c + 1)
                        shutil.move(nf, nfp)
                        if warn:
                            self.logger.warning("File found: {}".format(nf))
                        break
                    # otherwise, update filename to something not existing
                    else:
                        nfp = Decompressor.ensure_new(join(self.cwd, nf))
                        nf = basename(nfp)
                        # and re-control that it does not exist in files list
                        # NOTE: we do care about files with same hashes as the
                        #        filename could be valuable information ; so, we
                        #        don't check if the hash matches this of another
                        #        file in the self._hashes dictionary
            else:
                # handle here the case when an archive [filename].[ext]
                #  decompresses to [filename]
                if f == tn:
                    shutil.move(f, arch_name)
                    f = arch_name
                self.last = (f, ext)
                self.archives.insert(0, f)
            self.logger.debug("=> {}".format(f))
