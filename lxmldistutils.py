# Based on the version from Pyrex, cleaned up
# Added feature to allow include path option to support pxd files better

import distutils.command.build_ext
import Pyrex.Compiler.Main
from Pyrex.Compiler.Errors import PyrexError
from distutils.dep_util import newer
import os
import sys

def replace_suffix(path, new_suffix):
    return os.path.splitext(path)[0] + new_suffix

class build_ext(distutils.command.build_ext.build_ext):

  description = ("compile Pyrex scripts, then build C/C++ extensions "
                 "(compile/link to build directory)")

  def finalize_options(self):
      distutils.command.build_ext.build_ext.finalize_options(self)

  def swig_sources(self, sources):
      if not self.extensions:
          return
      
      pyx_sources = [source for source in sources
                     if source.endswith('.pyx')]
      other_sources = [source for source in sources
                       if not source.endswith('.pyx')]
      c_sources = []

      for pyx in pyx_sources:
          # should I raise an exception if it doesn't exist?
          if os.path.exists(pyx):
              source = pyx
              target = replace_suffix(source, '.c')
              c_sources.append(target)
              if newer(source, target) or self.force:
                  self.pyrex_compile(source)
      return c_sources + other_sources

  def pyrex_compile(self, source):
      options = Pyrex.Compiler.Main.CompilationOptions(
          show_version=0,
          use_listing_file=0,
          errors_to_stderr=1,
          include_path=self.get_pxd_include_paths(),
          c_only=1,
          obj_only=1,
          output_file=None)
      
      result = Pyrex.Compiler.Main.compile(source, options)
      if result.num_errors <> 0:
          sys.exit(1)

  def get_pxd_include_paths(self):
      """Override this to return a list of include paths for pyrex.
      """
      return []
