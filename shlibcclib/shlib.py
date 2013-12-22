# shlibcc -- shlib file processing and output creation
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections
import re


def get_dict_keys_with_value ( d, values ):
   return [ k for k, v in d.items() if v in values ]



class ShlibModuleException ( Exception ):
   pass

class ShlibModuleSyntaxError ( ShlibModuleException ):
   pass


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

   SECTIONS = [
      # module header
      'header',
      # module licence
      'license',
      # constants/variables that users are expected to set
      'user_constants', 'user_variables',
      # misc definitions (@funcdef etc.)
      'symdef', 'funcdef',
      # shared constants/variables (might be used/referenced by scripts)
      'constants', 'variables',
      # private module variables, usually starting with __<VARNAME>
      'module_vars',
      # functions (private/public/exported)
      # * private functions must not be used by other modules;
      #   their usual naming convention is <namespace>__<function name>()
      #   old-style private functions start with "__" (which is also used
      #   by some non-private functions, e.g. @pragma)
      #
      # * the private/public qualifiers are likely to be dropped
      #   (but not "exported")
      #
      'functions',
      # module variables initialized after declaring the functions
      # (usually variables referencing functions)
      #
      # this is *not* where you call <module>_defsym() etc.
      #
      'module_init_vars',
      # module initialization code
      'module_init',
      # EXPORT_FUNCTIONS block
      'module_export',
      # undefined
      'default',
   ]
   # "null" is a virtual section

   SECTION_ALIASES = {
      'licence'            : 'license',
      'user_const'         : 'user_constants',
      'user_vars'          : 'user_variables',
      'const'              : 'constants',
      'vars'               : 'variables',
      'func'               : 'functions',
      'functions_export'   : 'functions',
      'funcvars'           : 'module_init_vars',
      #'modvars'            : 'module_init_vars',
      'module_features'    : 'module_init_vars',
      'init'               : 'module_init',
      'main'               : 'default',
   }

   SECTION_KEYWORDS  = [ 'header', 'license' ]
   SECTION_KEYWORDS += get_dict_keys_with_value (
      SECTION_ALIASES, SECTION_KEYWORDS
   )


   @classmethod
   def get_section_name (
      cls, name, _SECTIONS=SECTIONS, _ALIAS=SECTION_ALIASES
   ):
      if not name:
         raise ShlibModuleSyntaxError ( "@section needs an arg" )
      else:
         name_low = name.lower().strip ( '_-+=^,;~*><' )

         if not name_low:
            # special alias: non-empty sequence of fill chars
            return 'default'

         elif name_low == 'null':
            return None

         if name_low in _SECTIONS:
            return name_low

         elif name_low in _ALIAS:
            # assert _ALIAS[arglow] in _SECTIONS
            return _ALIAS[name_low]
         else:
            raise ShlibModuleSyntaxError (
               "unknown @section {!r} ({!r})".format ( name_low, name )
            )
   # --- end of get_section_name (...) ---


   def __init__ ( self, module_name, module_fspath, config ):
      super ( ShlibModule, self ).__init__()
      self.name         = module_name
      self.fspath       = module_fspath
      self.config       = config
      self._sections    = dict()

      self._read()
      self._parse()
   # --- end of __init__ (...) ---

   def get_sections ( self ):
      return [ k for k, v in self._sections.items() if v ]
   # --- end of get_sections (...) ---

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

      def get_debug_commands ( type_keyword, arg, sline ):
         if debug_type in { 'echo', 'print', 'stdout' }:
            if arg:
               return [ "echo \"{}\"".format ( arg ) ]
            else:
               return [ "echo" ]

         elif debug_type in { 'stderr', }:
            if arg:
               return [ "echo \"{}\" 1>&2".format ( arg ) ]
            else:
               return [ "echo 1>&2" ]
         elif debug_type in { 'warn', 'error' }:
            if arg:
               return [
                  "echo \"{}: {}\" 1>&2".format ( debug_type.upper(), arg )
               ]
            else:
               return [ "echo 1>&2" ]

         else:
            raise ShlibModuleSyntaxError (
               "unknown @debug_<type> statement {!r}".format (
                  sline
               )
            )
      # --- end of get_debug_commands (...) ---

      def gen_varcheck_lines ( arg, empty_ok ):
         def iter_varnames():
            if arg:
               for varname in arg.split():
                  if varname[0] == '$':
                     raise ShlibModuleSyntaxError (
                        "@VARCHECK: invalid varname {!r}".format ( varname )
                     )
                  else:
                     yield varname
         # --- end of iter_varnames (...) ---

         have_any_varname = False

         if empty_ok:
            for varname in iter_varnames():
               yield ": ${" + varname + "?}"
               have_any_varname = True
         else:
            for varname in iter_varnames():
               yield ": ${" + varname + ":?}"
               have_any_varname = True

         if have_any_varname:
            # empty line after @varcheck
            yield None
      # --- end of gen_varcheck_lines (...) ---

      def strip_lines ( lines, section ):
         if not lines:
            return None
         elif self.name == '__main__' and not self.config.strip_main:
            retgen = lines
         elif self.config.strip_comments:
            retgen = strip_comments ( lines )
         elif self.config.strip_virtual and not contains_code ( lines ):
            retgen = list()
         elif self.config.strip_dev_comments:
            retgen = strip_dev_comments ( lines )
         else:
            retgen = lines
         return list ( strip_repeated_newline ( retgen ) )
      # --- end of strip_lines (...) ---

      keep_safety_checks   = self.config.keep_safety_checks
      enable_debug_code    = self.config.enable_debug_code
      section_keywords     = self.SECTION_KEYWORDS
      discard_virtual_line = lambda x: None
      reindent_line        = lambda line, arg: (
         ( line.partition('#')[0] + arg ) if arg else ""
      )

      sections             = { k: [] for k in self.SECTIONS }
      section              = 'default'
      add_line_to_section  = sections[section].append

      # TODO: create a parser class

      for line in self._lines:
         sline = line.strip()
         if not sline:
            add_line_to_section ( line )
         elif sline[0] == '#':
            # "# x", "# x #", ...
            line_parts = sline.strip ( '#' ).strip().split ( None, 1 )
            if line_parts and line_parts[0] and line_parts[0][0] == '@':
               keyword = line_parts[0][1:].lower()
               arg     = line_parts[1] if len ( line_parts ) > 1 else None

               if not keyword:
                  add_line_to_section ( line )

               elif keyword in { 'section', 'sections' }:
                  section = self.get_section_name ( arg )
                  if section is None:
                     add_line_to_section = discard_virtual_line
                  else:
                     add_line_to_section = sections[section].append

               elif keyword in section_keywords:
                  add_line_to_section = sections[keyword].append
                  if arg:
                     add_line_to_section ( '# ' + arg )

               elif keyword in { 'double_tap', 'safety_check' }:
                  if keep_safety_checks == 'c':
                     add_line_to_section ( line )
                  elif keep_safety_checks == 'y':
                     add_line_to_section ( reindent_line ( line, arg ) )

               elif keyword in { 'varcheck', 'vcheck' }:
                  if keep_safety_checks == 'c':
                     add_line_to_section ( line )
                  elif keep_safety_checks == 'y':
                     for varcheck_line in gen_varcheck_lines ( arg, False ):
                        add_line_to_section (
                           reindent_line ( line, varcheck_line )
                        )

               elif keyword in { 'varcheck_emptyok', 'vchecke' }:
                  if keep_safety_checks == 'c':
                     add_line_to_section ( line )
                  elif keep_safety_checks == 'y':
                     for varcheck_line in gen_varcheck_lines ( arg, True ):
                        add_line_to_section (
                           reindent_line ( line, varcheck_line )
                        )

               elif keyword == 'debug':
                  if enable_debug_code == 'c':
                     add_line_to_section ( line )
                  elif enable_debug_code == 'y':
                     add_line_to_section ( reindent_line ( line, arg ) )

               elif keyword[:6] == 'debug_':
                  if enable_debug_code == 'c':
                     add_line_to_section ( line )
                  elif enable_debug_code == 'y':
                     debug_type  = keyword[6:]
                     for dbg_arg in get_debug_commands (
                        debug_type, arg, sline
                     ):
                        add_line_to_section ( reindent_line ( line, dbg_arg ) )
                   # -- end if <enable_debug_code>
               else:
                  add_line_to_section ( line )

            else:
               add_line_to_section ( line )
         else:
            add_line_to_section ( line )
            pass
      # -- end for

      for section, raw_lines in sections.items():
         lines = strip_lines ( raw_lines, section )
         self._sections [section] = lines or None
   # --- end of parse (...) ---

   def to_str ( self, section ):
      if section == 'raw':
         return '\n'.join ( self._lines )
      else:
         entry = self._sections [section]
         return ( '\n'.join ( str(k) for k in entry ) ) if entry else None
   # --- end of to_str (...) ---

   def __str__ ( self ):
      return '\n'.join (
         filter (
            None,
            ( self.to_str ( k ) for k in self._sections.keys() )
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

      if self.config.restrict_sections is not None:
         want_sections = [
            k for k in ShlibModule.SECTIONS
               if k in self.config.restrict_sections
         ]
      else:
         want_sections = ShlibModule.SECTIONS


      for section in want_sections:
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
               if section == 'default':
                  if enclose_modules:
                     yield "### begin module {} ###".format ( m.name )
                     yield EMPTY_STR
                     yield _str
                     yield EMPTY_STR
                     yield "### end module {} ###".format ( m.name )
                  else:
                     yield _str

               elif section == 'license':
                  yield "### license for " + m.name
                  yield _str

               else:
                  yield "### module " + m.name
                  if _str[0] == '#':
                     yield EMPTY_STR
                  yield _str


         if not section_empty:
            #yield EMPTY_STR
            if section != 'default':
               yield EMPTY_STR
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

# --- end of ShlibFile ---
