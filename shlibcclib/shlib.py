# shlibcc -- shlib file processing and output creation
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections
import re

class TextLines ( collections.deque ):

   def discard ( self ):
      while self and not self [0]:
         self.popleft()
   # --- end of discard (...) ---

   def discard_end ( self ):
      while self and not self [-1]:
         self.pop()
   # --- end of discard_end (...) ---

# --- end of TextLines ---

class TextFileLines ( TextLines ):

   def __init__ ( self, fspath ):
      with open ( fspath, 'rt' ) as FH:
         lines = [ l.rstrip() for l in FH.readlines() ]

      super ( TextFileLines, self ).__init__ ( lines )
      self.discard()
      self.discard_end()
   # --- end of __init__ (...) ---

   def pop ( self, *args, **kwargs ):
      ret = super ( TextFileLines, self ).pop ( *args, **kwargs )
      self.discard_end()
      return ret
   # --- end of pop (...) ---

   def popleft ( self, *args, **kwargs ):
      ret = super ( TextFileLines, self ).popleft ( *args, **kwargs )
      self.discard()
      return ret
   # --- end of popleft (...) ---

# --- end of TextFileLines ---

#~ class ShellVariable ( object ):
#~
   #~ def __init__ ( self, name, value, comment=None, use_param_expansion=True ):
      #~ self.name                = name
      #~ self.value               = value
      #~ self.comment             = None
      #~ self.use_param_expansion = use_param_expansion
   #~ # --- end of __init__ (...) ---
#~
   #~ def _varstr ( self ):
      #~ if self.use_param_expansion:
         #~ return '{name}="{value}"'.format ( name=self.name, value=self.value )
      #~ else:
         #~ return "{name}='{value}'".format ( name=self.name, value=self.value )
   #~ # --- end of _varstr (...) ---
#~
   #~ def __str__ ( self ):
      #~ if self.comment:
         #~ return self.comment + '\n' + self._varstr()
      #~ else:
         #~ return self._varstr()
   #~ # --- end of __str__ (...) ---
#~
#~ # --- end of ShellVariable ---
#~
#~
#~ class ShellConstant ( object ):
#~
   #~ def _varstr ( self ):
      #~ return 'readonly ' + super ( ShellConstant, self )._varstr()
   #~ # --- end of _varstr (...) ---
#~
#~ # --- end of ShellConstant ---
#~
#~
#~ class SymbolTable ( object ):
#~
   #~ def __init__ ( self, is_const ):
      #~ self.is_const = is_const
      #~ self._sym     = collections.OrderedDict()
   #~ # --- end of __init__ (...) ---
#~
   #~ def __str__ ( self ):
      #~ return '\n'.join (
         #~ str ( var ) for var in self._sym.values()
      #~ )
   #~ # --- end of __str__ (...) ---
#~
#~ # --- end of SymbolTable ---


class ShlibModule ( object ):

   RE_INCLUDE_PROTECTION = re.compile (
      '^\s*if\s+\[{1,2}\s+\-z\s+..*__HAVE_..*__.*\s+\]{1,2}'
   )

   def __init__ ( self, module_name, module_fspath, config ):
      super ( ShlibModule, self ).__init__()
      self.name         = module_name
      self.fspath       = module_fspath
      self.config       = config

      self._header      = None
      self._variables   = None
      self._constants   = None
      self._functions   = collections.OrderedDict()
      self._module_init = None
      self._default     = list()

      self._read()
      self._parse()
   # --- end of __init__ (...) ---

   def _read ( self ):
      lines = TextFileLines ( self.fspath )

      if lines:
         if len ( lines [0] ) > 2 and lines [0][:2] == '#!':
            lines.popleft()

         if (
            self.RE_INCLUDE_PROTECTION.match ( lines [0] ) and
            lines [1][:9]  == 'readonly ' and
            lines [-1][:2] == 'fi'
         ) :
            lines.popleft()
            lines.popleft()
            lines.pop()
         # -- if;

      self._lines = lines
   # --- end of _read (...) ---

   def _parse ( self ):
      def strip_comments ( lines ):
         for line in lines:
            sline = line.lstrip()
            if not sline or sline[0] != '#':
               yield line
      # --- end of strip_comments (...) ---

      def contains_code ( lines ):
         for line in lines:
            sline = line.lstrip()
            if sline and not sline[0] == '#':
               return True
         return False
      # --- end of strip_virtual (...) ---

      def strip_dev_comments ( lines ):
         for line in lines:
            if line [:2] == '##' and ( len ( line ) < 3 or line [2] != '#' ):
               pass
            else:
               yield line
      # --- end of strip_dev_comments (...) ---

      def strip_repeated_newline ( lines ):
         last_line_empty = True
         for line in lines:
            if line:
               last_line_empty = False
               yield line
            elif not last_line_empty:
               last_line_empty = True
               yield line
      # --- end of strip_repeated_newline (...) ---

      if self.name == '__main__' and not self.config.strip_main:
         result = self._lines
      elif self.config.strip_comments:
         result = strip_comments ( self._lines )
      elif self.config.strip_virtual and not contains_code ( self._lines ):
         result = list()
      elif self.config.strip_dev_comments:
         result = strip_dev_comments ( self._lines )
      else:
         result = self._lines

      self._default = list ( strip_repeated_newline ( result ) )
   # --- end of parse (...) ---

   def to_str ( self, section ):
      if section == 'default':
         return '\n'.join ( self._default )

      elif section == 'raw':

         return '\n'.join ( self._lines )

      else:
         val = getattr ( self, '_' + section )
         return str ( val ) if val else None

   # --- end of to_str (...) ---

   def __str__ ( self ):
      return '\n'.join (
         filter (
            None,
            (
               self.to_str ( k ) for k in (
                  'header', 'constants', 'variables', 'functions',
                  'default', 'module_init'
               )
            )
         )
      )
   # --- end of __str__ (...) ---

# --- end of ShlibModule ---

class ShlibFile ( object ):

   def __init__ ( self, config, header=None ):
      self._module_order = list()
      self._modules      = dict()
      self.config        = config
      self.header        = header
      self.defsym        = None
      self.pre_header    = None
      self.footer        = None
   # --- end of __init__ (...) ---

   def add_module ( self, module_name, module_fspath ):
      assert module_name not in self._modules

      module = ShlibModule ( module_name, module_fspath, self.config )

      self._module_order.append ( module_name )
      self._modules [module_name] = module
      return True
   # --- end of add_module (...) ---

   def set_header ( self, header ):
      self.header = header
   # --- end of set_header (...) ---

   def set_module_order ( self, module_order ):
      if __debug__:
         new_order = list ( module_order )

         if len ( new_order ) >= len ( self._module_order ):
            names = set ( new_order )

            for name in self._module_order:
               if name not in names:
                  raise AssertionError()
            else:
               self._module_order = new_order

         else:
            raise AssertionError()

      else:
         self._module_order = list ( module_order )
   # --- end of set_module_order (...) ---

   def generate_lines ( self ):
      EMPTY_STR = ""
      modules   = [ self._modules [key] for key in self._module_order ]

      def iterate_str_lines ( var, newline_end=True, newline_begin=False ):
         if not var:
            pass
         elif isinstance ( var, str ):
            if newline_begin: yield EMPTY_STR
            yield var
            if newline_end: yield EMPTY_STR
         elif hasattr ( var, '__iter__' ):
            if newline_begin: yield EMPTY_STR
            for s in var:
               yield str ( s )
            if newline_end: yield EMPTY_STR
         else:
            if newline_begin: yield EMPTY_STR
            yield str ( var )
            if newline_end: yield EMPTY_STR
      # --- end of iterate_str_lines (...) ---

      for s in iterate_str_lines ( self.pre_header ):
         yield s

      for s in iterate_str_lines ( self.header, newline_end=False ):
         yield s


      if self.defsym:
         yield self.defsym

      first_section   = True
      enclose_modules = self.config.enclose_modules

      for section in (
         'header', 'constants', 'variables', 'functions',
         'default', 'module_init'
      ):
         section_empty = True

         for m in modules:
            _str = m.to_str ( section )
            if _str:
               if section_empty:
                  if first_section:
                     first_section = False
                  else:
                     yield EMPTY_STR

                  if section != 'default':
                     yield "##### begin section {} #####".format ( section )

                  section_empty = False


               yield EMPTY_STR
               if enclose_modules:
                  yield "### begin module {} ###".format ( m.name )
                  yield EMPTY_STR
                  yield _str
                  yield EMPTY_STR
                  yield "### end module {} ###".format ( m.name )
               else:
                  yield _str


         if not section_empty:
            #yield EMPTY_STR
            if section != 'default':
               yield "##### end section {} #####".format ( section )

      # -- for;

      for s in iterate_str_lines ( self.footer, True, True ):
         yield s
   # --- end of generate_lines (...) ---

   def __str__ ( self ):
      return '\n'.join ( self.generate_lines() )
   # --- end of __str__ (...) ---

   def write ( self, fh_or_fspath ):
      def write_into ( fh ):
         for line in self.generate_lines():
            fh.write ( line )
            fh.write ( '\n' )
      # --- end of write_into (...) ---

      if isinstance ( fh_or_fspath, str ):
         with open ( fh_or_fspath, 'wt' ) as FH:
            write_into ( FH )
      else:
         write_into ( fh_or_fspath )
   # --- end of write (...) ---
