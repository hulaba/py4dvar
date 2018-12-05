
import logging
import os

import _get_root
from fourdvar.params.root_path_defn import root_path, short_path
from fourdvar.params.cmaq_config import is_large_sim

#levels in acending order: DEBUG, INFO, WARNING, ERROR, CRITICAL
#to_screen_level = logging.INFO
to_screen_level = logging.INFO
#to_file_level = logging.DEBUG
to_file_level = logging.DEBUG

#format strings:
to_screen_format = '%(name)s - %(levelname)s - %(message)s'
#to_file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
to_file_format = '%(name)s - %(levelname)s - %(message)s'

logfile_name = 'full_report.log'

reset_logfile = True

project_name = os.path.split( root_path )[1]

if is_large_sim is True:
    logfile = os.path.join( short_path, logfile_name )
else:
    logfile = os.path.join( root_path, logfile_name )

if reset_logfile is True and os.path.isfile( logfile ):
    os.remove( logfile )

base_logger = logging.getLogger( project_name )
base_logger.setLevel( logging.DEBUG )

to_screen_handle = logging.StreamHandler()
to_file_handle = logging.FileHandler( logfile )
to_screen_handle.setLevel( to_screen_level )
to_file_handle.setLevel( to_file_level )

to_screen_formatter = logging.Formatter( to_screen_format )
to_file_formatter = logging.Formatter( to_file_format )

to_screen_handle.setFormatter( to_screen_formatter )
to_file_handle.setFormatter( to_file_formatter )
base_logger.addHandler( to_screen_handle )
base_logger.addHandler( to_file_handle )

base_logger.debug( 'Logging setup finished.' )

def get_logger( filepath ):
    """
    framework: return a modules logger
    input: string (always submodules __file__ keyword)
    output: logging.Logger object (for writing)
    """
    #suffix = '.py' or '.pyc'
    modpath = os.path.realpath( filepath )
    suffix = ''
    suffix_list = ['.py', '.pyc']
    for s in suffix_list:
        if modpath.endswith( s ):
            suffix = s
    assert suffix != '', '{} not a python file'.format( modpath )
    assert modpath.startswith( root_path ), '{} not a submodule of project {}'.format( modpath, root_path )
    namelist = []
    path_slice = modpath[ len(root_path):-len(suffix) ]
    while True:
        head, tail = os.path.split( path_slice )
        if tail == '':
            break
        namelist.append( tail )
        path_slice = head
    namelist.append( project_name )
    namelist.reverse()
    logger_name = '.'.join( namelist )
    return logging.getLogger( logger_name )
