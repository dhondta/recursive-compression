""" Recursive (de)compression module.
"""
import patoolib
from tinyscript import code

from .compressor import Compressor
from .decompressor import Decompressor


__all__ = ["Compressor", "Decompressor"]


# patch patoolib.util.backtick at runtime to silent annoying subprocess messages
code.replace(patoolib.util.backtick,
             "stdout=subprocess.PIPE)",
             "stdout=subprocess.PIPE, stderr=subprocess.PIPE)")
# patch patoolib.util.log_info at runtime to silent annoying log messages
code.replace(patoolib.util.log_info,
             "print(\"patool:\", msg, file=out)",
             "pass")
# patch patoolib.util.run at runtime to silent annoying subprocess.call messages
code.replace(patoolib.util.run,
             "kwargs['stdout'] = devnull",
           "kwargs['stdout'] = devnull\n            kwargs['stderr'] = devnull")
# patch patoolib.util.guess_mime_file to force mime DB guess for some formats
code.replace(patoolib.util.guess_mime_file,
             "if ext.lower() in ('.alz',):",
             "if ext.lower() in ('.alz','.bz2','.gz','.xz'):")
