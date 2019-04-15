
import numpy as np
import datetime as dt
from ray_trace import Point, Ray
from obs_defn import ObsInstantRay

class ObsGEOCARB( ObsInstantRay ):
    """Single observation (or sounding) from GEOCARB satellite
    This observation class only works for 1 species.
    """
    required = ['value','uncertainty','weight_grid','offset_term']
    
    @classmethod
    def create( cls, **kwargs ):
        """kwargs comes from variables in geocarb files.
        min. requirements for kwargs:
        - sounding_id : long_int
        - latitude : float (degrees)
        - longitude : float (degrees)
        - time : datetime object
        - xco2 : float (ppm)
        - xco2_uncertainty : float (ppm)
        - xco2_apriori : float (ppm)
        - co2_profile_apriori : array[ float ] (length=levels, units=ppm)
        - xco2_averaging_kernel : array[ float ] (length=levels)
        - pressure_levels : array[ float ] (length=levels, units=hPa)
        - pressure_weight : array[ float ] (length=levels)
        #- warn_level : NOT CURRENTLY IMPLEMENTED
        """
        newobs = cls( obstype='GEOCARB_sounding' )
        newobs.out_dict['value'] = kwargs['xco2']
        newobs.out_dict['uncertainty'] = kwargs['xco2_uncertainty']

        column_xco2 = ( kwargs['pressure_weight'] *
                        kwargs['xco2_averaging_kernel'] *
                        kwargs['co2_profile_apriori'] )
        newobs.out_dict['offset_term'] = kwargs['xco2_apriori'] - column_xco2.sum()
        newobs.out_dict['sounding_id'] = kwargs['sounding_id']
        #Current version only record CO2 values, TODO: CO
        newobs.spcs = 'CO2'
        newobs.src_data = kwargs.copy()
        return newobs
    
    def model_process( self, model_space ):
        ObsInstantRay.model_process( self, model_space )
        #now created self.out_dict[ 'weight_grid' ]
        return None
    
    def add_visibility( self, proportion, model_space ):
        obs_pressure = np.array( self.src_data[ 'pressure_levels' ] )
        obs_kernel = np.array( self.src_data[ 'xco2_averaging_kernel' ] )
        obs_pweight = np.array( self.src_data[ 'pressure_weight' ] )
        obs_vis = obs_kernel * obs_pweight
        
        #get sample model coordinate at surface
        coord = [ c for c in proportion.keys() if c[2] == 0 ][0]
        
        model_vis = model_space.pressure_convert( obs_pressure, obs_vis, coord )
        
        weight_grid = {}
        for l, weight in enumerate( model_vis ):
            layer_slice = { c:v for c,v in proportion.items() if c[2] == l }
            layer_sum = sum( layer_slice.values() )
            weight_slice = { c: weight*v/layer_sum for c,v in layer_slice.items() }
            weight_grid.update( weight_slice )
        
        return weight_grid
    
    def map_location( self, model_space ):
        assert model_space.gridmeta['GDTYP'] == 2, 'invalid GDTYP'
        #convert source location data into a pair of spacial points
        #GEOCARB assumes a vertical retrieval.
        lat = self.src_data[ 'latitude' ]
        lon = self.src_data[ 'longitude' ]
        
        x1,y1 = model_space.get_xy( lat, lon )
        p1 = ( x1, y1, 0, )
        p2 = ( x1, y1, model_space.max_height, )
        
        self.location = [ p1, p2 ]
        #use generalized function
        return ObsInstantRay.map_location( self, model_space )
    
    def map_time( self, model_space ):
        #convert source time into [ int(YYYYMMDD), int(HHMMSS) ]
        fulltime = self.src_data[ 'time' ]
        day = int( fulltime.strftime( '%Y%m%d' ) )
        time = int( fulltime.strftime( '%H%M%S' ) )
        self.time = [ day, time ]
        #use generalized function
        return ObsInstantRay.map_time( self, model_space )
