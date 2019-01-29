
from __future__ import absolute_import

import glob
from netCDF4 import Dataset
import os

import context
from fourdvar.params.root_path_defn import store_path
import fourdvar.util.file_handle as fh
from model_space import ModelSpace
from obsOCO2_defn import ObsOCO2
import super_obs_util as so_util

#-CONFIG-SETTINGS---------------------------------------------------------

#'filelist': source = list of OCO2-Lite files
#'directory': source = directory, use all files in source
#'pattern': source = file_pattern_string, use all files that match pattern
source_type = 'directory'

source = os.path.join( store_path, 'obs_oco2_data' )
#source = os.path.join( store_path, 'obs_1day' )

output_file = './oco2_observed.pic.gz'

#if true interpolate between 2 closest time-steps, else assign to closet time-step
interp_time = False

#--------------------------------------------------------------------------

model_grid = ModelSpace.create_from_fourdvar()

if source_type.lower() == 'filelist':
    filelist = [ os.path.realpath( f ) for f in source ]
elif source_type.lower() == 'pattern':
    filelist = [ os.path.realpath( f ) for f in glob.glob( source ) ]
elif source_type.lower() == 'directory':
    dirname = os.path.realpath( source )
    filelist = [ os.path.join( dirname, f )
                 for f in os.listdir( dirname )
                 if os.path.isfile( os.path.join( dirname, f ) ) ]
else:
    raise TypeError( "source_type '{}' not supported".format(source_type) )

root_var = [ 'sounding_id',
             'latitude',
             'longitude',
             'time',
             'solar_zenith_angle',
             'sensor_zenith_angle',
             'xco2_quality_flag',
             'xco2',
             'xco2_uncertainty',
             'xco2_apriori',
             'pressure_levels',
             'co2_profile_apriori',
             'xco2_averaging_kernel',
             'pressure_weight' ]
sounding_var = [ 'solar_azimuth_angle', 'sensor_azimuth_angle', 'operation_mode' ]
retrieval_var = ['surface_type']

obslist = []
for fname in filelist:
    print 'read {}'.format( fname )
    var_dict = {}
    with Dataset( fname, 'r' ) as f:
        size = f.dimensions[ 'sounding_id' ].size
        for var in root_var:
            var_dict[ var ] = f.variables[ var ][:]
        for var in sounding_var:
            var_dict[ var ] = f.groups[ 'Sounding' ].variables[ var ][:]
        for var in retrieval_var:
            var_dict[ var ] = f.groups[ 'Retrieval' ].variables[ var ][:]
    print 'found {} soundings'.format( size )
    
    sounding_list = []
    for i in range( size ):
        src_dict = { k: v[i] for k,v in var_dict.items() }
        lat = src_dict['latitude']
        lon = src_dict['longitude']
        if so_util.max_quality_only is True and src_dict['xco2_quality_flag'] != 0:
            pass
        elif model_grid.lat_lon_inside( lat=lat, lon=lon ):
            if so_util.group_by_second is True:
                src_dict['sec'] = int( src_dict['time'] )
            sounding_list.append( src_dict )
    del var_dict

    if so_util.group_by_second is True:
        sec_list = list( set( [ s['sec'] for s in sounding_list ] ) )
        merge_list = []
        for sec in sec_list:
            sounding = so_util.merge_second( [ s
                       for s in sounding_list if s['sec'] == sec ] )
            merge_list.append( sounding )
        sounding_list = merge_list

    for sounding in sounding_list:
        obs = ObsOCO2.create( **sounding )
        obs.interp_time = interp_time
        obs.model_process( model_grid )
        if obs.valid is True:
            obslist.append( obs.get_obsdict() )

if so_util.group_by_column is True:
    obslist = [ o for o in obslist if so_util.is_single_column(o) ]
    col_list = list( set( [ so_util.get_col_id(o) for o in obslist ] ) )
    merge_list = []
    for col in col_list:
        obs = so_util.merge_column( [ o for o in obslist
                                      if so_util.get_col_id(o) == col ] )
        merge_list.append( obs )
    obslist = merge_list

if len( obslist ) > 0:
    domain = model_grid.get_domain()
    datalist = [ domain ] + obslist
    fh.save_list( datalist, output_file )
    print 'recorded observations to {}'.format( output_file )
else:
    print 'No valid observations found, no output file generated.'
