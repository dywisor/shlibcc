import sys

DEBUG_PRINT = True

def debug_print ( _str ):
   if DEBUG_PRINT:
      sys.stderr.flush()
      sys.stderr.write ( "debug: " )
      sys.stderr.write ( _str )
      sys.stderr.write ( "\n" )
