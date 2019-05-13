[![PyPi](https://img.shields.io/pypi/v/recursive-decompressor.svg)](https://pypi.python.org/pypi/recursive-decompressor/)
[![Python Versions](https://img.shields.io/pypi/pyversions/recursive-decompressor.svg)](https://pypi.python.org/pypi/recursive-decompressor/)
[![Platform](https://img.shields.io/badge/platform-linux-yellow.svg)](https://pypi.python.org/pypi/recursive-decompressor/)
[![Known Vulnerabilities](https://snyk.io/test/github/dhondta/recursive-decompressor/badge.svg?targetFile=requirements.txt)](https://snyk.io/test/github/dhondta/recursive-decompressor?targetFile=requirements.txt)
[![Requirements Status](https://requires.io/github/dhondta/recursive-decompressor/requirements.svg?branch=master)](https://requires.io/github/dhondta/recursive-decompressor/requirements/?branch=master)
[![License](https://img.shields.io/pypi/l/recursive-decompressor.svg)](https://pypi.python.org/pypi/recursive-decompressor/)


## Table of Contents

   * [Introduction](#introduction)
   * [Installation](#installation)
   * [Quick Start](#quick-start)


## Introduction

This tool relies on [Tinyscript](https://github.com/dhondta/tinyscript) and allows to recursively (de)compress nested archives according to various decompression algorithms implemented in [Patool](https://github.com/wummel/patool).


## Installation

```session
$ sudo pip install recursive-compression
```

 > **Behind a proxy ?**
 > 
 > Do not forget to add option `--proxy=http://[user]:[pwd]@[host]:[port]` to your pip command.


## Quick Start

### Compression

```session
$ rec-comp -h
usage: rec-comp [-c CHARSET] [-d] [-n NCHARS] [-r ROUNDS] [-h] [-p] [--stats]
                [--timings] [-v]
                files [files ...]

RecComp v1.0
Author   : Alexandre D'Hondt
Copyright: © 2019 A. D'Hondt
License  : GNU Affero General Public License v3.0

This tool allows to recursively compress an archive relying on Patool, a Python
 library supporting various archive formats.

Note: Password-protected compression is not supported.

positional arguments:
  files                 files to be archived

optional arguments:
  -c CHARSET            character set of random archive name (default: abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789)
  -d                    delete input files (default: False)
  -f FORMATS            compression algorithms (default: all)
  -n NCHARS             length of random archive name (default: 8)
  -r ROUNDS, --rounds ROUNDS
                        number of compression rounds (default: 10)
  --reverse             reverse byte order (default: False)

data options:
  --data DATA           data to be embedded (default: None)
  --chunks CHUNKS       number of chunks the data should be split in (default: 10)

extra arguments:
  -h, --help            show this help message and exit
  -p, --progress        progress mode (default: False)
  -v, --verbose         verbose mode (default: False)

timing arguments:
  --stats               display execution time stats at exit (default: False)
  --timings             display time stats during execution (default: False)

Usage examples:
  rec-comp file1 file2 file3 -r 10
  rec-comp file -c abcd -n 10
  rec-comp -p

```

```session
$ rec-comp file1 file2 file3 -r 10 -p
100%|██████████| 10/10 [00:05<00:00,  1.94it/s]
12:34:56 [INFO] Rounds:  10
12:34:56 [INFO] Archive: Vdpxp8Qy

```


### Decompression

```session
$ rec-decomp -h
usage: rec-decomp [-d] [-p] [-h] [--stats] [--timings] [-v] archive

RecDecomp v2.1
Author   : Alexandre D'Hondt
Copyright: © 2019 A. D'Hondt
License  : GNU Affero General Public License v3.0
Training : ZSIS CTF - Trivia - Shining (4 points)

This tool allows to recursively decompress an archive relying on Patool, a
 Python library supporting various archive formats.

Note: Password-protected compression is not supported yet. If the tool freezes
       while decompressing, it may be necessary to press enter to submit a blank
       password, which will stop decompression.

positional arguments:
  archive        input archive

optional arguments:
  -d             delete input archive (default: False)
  -p             print resulting file, if possible (default: False)

extra arguments:
  -h, --help     show this help message and exit
  -v, --verbose  verbose mode (default: False)

timing arguments:
  --stats        display execution time stats at exit (default: False)
  --timings      display time stats during execution (default: False)

Usage examples:
  rec-decomp archive.zip
  rec-decomp archive.zip -d

```

```session
$ rec-decomp Vdpxp8Qy 
12:34:56 [INFO] Rounds: 10
12:34:56 [INFO] Files :
- file1 (8d5e08e1bbc49f59b208e0288e220ac0fc336ac0779852cb823c910ae03b5bc4)
- file2 (9f07ec2f89cbec2696574d26238a2d876cfe1249909cc5de2f171ae9ede3e475)
- file3 (60bf2a298af8b71b7fcc0e726c4f75d78c73949c9562cf0c1a2bbeadeeca8ee4)

```
