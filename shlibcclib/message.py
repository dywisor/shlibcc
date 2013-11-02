import sys

DEBUG_PRINT = True

def debug_print ( _str, force_print=False ):
   if force_print or DEBUG_PRINT:
      sys.stderr.flush()
      sys.stderr.write ( "debug: " )
      sys.stderr.write ( _str )
      sys.stderr.write ( "\n" )

def force_debug_print ( _str ):
   debug_print ( _str, True )
