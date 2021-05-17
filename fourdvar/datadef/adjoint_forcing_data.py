"""
adjoint_forcing_data.py

Copyright 2016 University of Melbourne.
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import numpy as np
import os

from fourdvar.datadef.abstract._fourdvar_data import FourDVarData
from fourdvar.util.archive_handle import get_archive_path
import fourdvar.util.netcdf_handle as ncf

class AdjointForcingData( FourDVarData ):
    """application
    """
    archive_name = 'adjoint_forcing.nc'
    def __init__( self, value ):
        """
        application: create an instance of AdjointForcingData
        input: None
        output: None
        """
        # most work handled by the create_new classmethod.
        self.value = np.array( value )
        return None
    
    def archive( self, path=None ):
        """
        extension: save copy of files to archive/experiment directory
        input: string or None
        output: None
        """
        save_path = get_archive_path()
        if path is None:
            path = self.archive_name
        save_path = os.path.join( save_path, path )
        if os.path.isfile( save_path ):
            os.remove( save_path )

        (nrow,ncol,) = self.value.shape
        dim_dict = {'ROW':nrow,'COL':ncol}
        var_dict = { 'FORCING': ('f4', ('ROW','COL',), self.value[:]) }
        root = ncf.create( save_path, dim=dim_dict, var=var_dict, is_root=True )
        root.close()
        return None
        
    @classmethod
    def create_new( cls, data ):
        """
        application: create an instance of AdjointForcingData from template with new data
        input: user-defined
        output: AdjointForcingData
        
        eg: new_forcing =  datadef.AdjointForcingData( filelist )
        """
        return cls( data )

    #OPTIONAL
    @classmethod
    def load_from_archive( cls, dirname ):
        """
        extension: create an AdjointForcingData from previous archived files.
        input: string (path/to/file)
        output: AdjointForcingData
        """
        pathname = os.path.realpath( dirname )
        value = ncf.get_variable( pathname, 'FORCING' )
        return cls( value )
    
    def cleanup( self ):
        """
        application: called when forcing is no longer required
        input: None
        output: None
        
        eg: old_forcing.cleanup()
        
        notes: called after test instance is no longer needed, used to delete files etc.
        """
        # function needed but can be left blank
        return None
