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

This tool relies on [Tinyscript](https://github.com/dhondta/tinyscript) and allows to recursively decompress nested archives according to various decompression algorithms.


## Installation

```session
$ sudo pip install recursive-decompressor
```

 > **Behind a proxy ?**
 > 
 > Do not forget to add option `--proxy=http://[user]:[pwd]@[host]:[port]` to your pip command.


## Quick Start

### Help

```session
$ recursive-decompressor --help
usage: recursive-decompressor [-d] [-k N] [-h] [-v] archive

RecursiveDecompressor v1.6
Author   : Alexandre D'Hondt
Copyright: © 2019 A. D'Hondt
License  : GNU Affero General Public License v3.0
Training : ZSIS CTF - Trivia - Shining (4 points)

This tool allows to recursively decompress an archive, using multiple Linux
 decompression tools. It currently supports the following tools:
- 7za
- arj
- bzip2
- gunzip
- lzma
- tar
- unrar
- unxz
- unzip

positional arguments:
  archive         input archive

optional arguments:
  -d              display last decompressed file in terminal (default: False)
  -k N, --keep N  keep the last N levels of archives (default: 1)

extra arguments:
  -h, --help      show this help message and exit
  -v, --verbose   verbose mode (default: False)

Usage examples:
  recursive-decompressor archive.zip
  recursive-decompressor archive.zip -d
  recursive-decompressor archive.zip -d -k 3

```
