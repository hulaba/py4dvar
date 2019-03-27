"""
application: convert output of adjoint function to sensitivities to physical variables
like all transform in transfunc this is referenced from the transform function
eg: transform( sensitivity_instance, datadef.PhysicalAdjointData ) == condition_adjoint( sensitivity_instance )
"""
from __future__ import absolute_import

import numpy as np

from fourdvar.datadef import SensitivityData, PhysicalAdjointData
import fourdvar.params.cmaq_config as cmaq_config
from fourdvar.params.input_defn import inc_icon
import fourdvar.params.template_defn as template
import fourdvar.util.date_handle as dt
import fourdvar.util.netcdf_handle as ncf

unit_key = 'units.<YYYYMMDD>'
unit_convert_dict = None

def get_unit_convert():
    """
    extension: get unit conversion dictionary for sensitivity to each days emissions
    input: None
    output: dict ('units.<YYYYMMDD>': np.ndarray( shape_of( template.sense_emis ) )
    
    notes: SensitivityData.emis units = CF/(ppm/s)
           PhysicalAdjointData.emis units = CF/(mol/(s*m^2))
    """
    global unit_key
    
    #physical constants:
    #molar weight of dry air (precision matches cmaq)
    mwair = 28.9628
    #convert proportion to ppm
    ppm_scale = 1E6
    #convert g to kg
    kg_scale = 1E-3
    
    unit_dict = {}
    #all spcs have same shape, get from 1st
    tmp_spc = ncf.get_attr( template.sense_emis, 'VAR-LIST' ).split()[0]
    target_shape = ncf.get_variable( template.sense_emis, tmp_spc )[:].shape
    #layer thickness constant between files
    lay_sigma = list( ncf.get_attr( template.sense_emis, 'VGLVLS' ) )
    #layer thickness measured in scaled pressure units
    lay_thick = [ lay_sigma[ i ] - lay_sigma[ i+1 ] for i in range( len( lay_sigma ) - 1 ) ]
    lay_thick = np.array(lay_thick).reshape(( 1, len(lay_thick), 1, 1 ))
    
    for date in dt.get_datelist():
        met_file = dt.replace_date( cmaq_config.met_cro_3d, date )
        #slice off any extra layers above area of interest
        rhoj = ncf.get_variable( met_file, 'DENSA_J' )[ :, :len( lay_thick ), ... ]
        #assert timesteps are compatible
        assert (target_shape[0]-1) >= (rhoj.shape[0]-1), 'incompatible timesteps'
        assert (target_shape[0]-1) % (rhoj.shape[0]-1) == 0, 'incompatible timesteps'
        reps = (target_shape[0]-1) // (rhoj.shape[0]-1)
        
        rhoj_mapped = rhoj[ :-1, ... ].repeat( reps, axis=0 )
        rhoj_mapped = np.append( rhoj_mapped, rhoj[ -1:, ... ], axis=0 )
        unit_array = (ppm_scale*kg_scale*mwair) / (rhoj_mapped*lay_thick)
        
        day_label = dt.replace_date( unit_key, date )
        unit_dict[ day_label ] = unit_array
    return unit_dict

def map_sense( sensitivity ):
    """
    application: map adjoint sensitivities to physical grid of unknowns.
    input: SensitivityData
    output: PhysicalAdjointData
    """
    global unit_convert_dict
    global unit_key
    if unit_convert_dict is None:
        unit_convert_dict = get_unit_convert()
    
    #check that:
    #- date_handle dates exist
    #- PhysicalAdjointData params exist
    #- template.emis & template.sense_emis are compatible
    #- template.icon & template.sense_conc are compatible
    datelist = dt.get_datelist()
    PhysicalAdjointData.assert_params()
    #all spcs use same dimension set, therefore only need to test 1.
    test_spc = PhysicalAdjointData.spcs[0]
    test_fname = dt.replace_date( template.emis, dt.start_date )
    mod_shape = ncf.get_variable( test_fname, test_spc ).shape    
    
    #phys_params = ['tsec','nstep','nlays_icon','nlays_emis','nrows','ncols','spcs']
    #icon_dict = { spcs: np.ndarray( nlays_icon, nrows, ncols ) }
    #emis_dict = { spcs: np.ndarray( nstep, nlays_emis, nrows, ncols ) }
    
    #create blank constructors for PhysicalAdjointData
    p = PhysicalAdjointData
    if inc_icon is True:
        icon_dict = { spc: 1. for spc in p.spcs }
    emis_shape = ( p.nstep, p.nlays_emis, p.nrows, p.ncols, )
    emis_dict = { spc: np.zeros( emis_shape ) for spc in p.spcs }
    del p
    
    #construct icon_dict
    if inc_icon is True:
        i_sense_label = dt.replace_date( 'conc.<YYYYMMDD>', datelist[0] )
        i_sense_fname = sensitivity.file_data[ i_sense_label ][ 'actual' ]
        i_sense_vars = ncf.get_variable( i_sense_fname, icon_dict.keys() )
        icon_vars = ncf.get_variable( template.icon, icon_dict.keys() )
        for spc in PhysicalAdjointData.spcs:
            sense_data = i_sense_vars[ spc ][ 0, ... ]
            icon_data = icon_vars[ spc ] [ 0, ... ]
            msg = 'conc_sense and template.icon are incompatible'
            assert sense_data.shape == icon_data.shape, msg
            icon_dict[ spc ] = (sense_data * icon_data).mean()
    
    p_daysize = float(24*60*60) / PhysicalAdjointData.tsec
    emis_pattern = 'emis.<YYYYMMDD>'
    for i,date in enumerate( datelist ):
        label = dt.replace_date( emis_pattern, date )
        sense_fname = sensitivity.file_data[ label ][ 'actual' ]
        sense_data_dict = ncf.get_variable( sense_fname, PhysicalAdjointData.spcs )
        start = int( i * p_daysize )
        end = int( (i+1) * p_daysize )
        if start == end:
            end += 1
        for spc in PhysicalAdjointData.spcs:
            unit_convert = unit_convert_dict[ dt.replace_date( unit_key, date ) ]
            sdata = sense_data_dict[ spc ][:] * unit_convert
            sstep, slay, srow, scol = sdata.shape
            #recast to match mod_shape
            mstep, mlay, mrow, mcol = mod_shape
            msg = 'emis_sense and ModelInputData {} are incompatible.'
            assert ((sstep-1) >= (mstep-1)) and ((sstep-1) % (mstep-1) == 0), msg.format( 'TSTEP' )
            assert slay >= mlay, msg.format( 'NLAYS' )
            assert srow == mrow, msg.format( 'NROWS' )
            assert scol == mcol, msg.format( 'NCOLS' )
            fac = (sstep-1) // (mstep-1)
            tmp = np.array([ sdata[ i::fac, 0:mlay, ... ]
                             for i in range( fac ) ]).mean( axis=0 )
            #adjoint prepare_model
            msg = 'ModelInputData and PhysicalAdjointData.{} are incompatible.'
            assert ((mstep-1) >= (end-start)) and ((mstep-1) % (end-start) == 0), msg.format('nstep')
            assert mlay >= PhysicalAdjointData.nlays_emis, msg.format( 'nlays_emis' )
            assert mrow == PhysicalAdjointData.nrows, msg.format( 'nrows' )
            assert mcol == PhysicalAdjointData.ncols, msg.format( 'ncols' )
            fac = (mstep-1) // (end-start)
            pdata = np.array([ tmp[ i:-1:fac, 0:PhysicalAdjointData.nlays_emis, ... ]
                               for i in range( fac ) ]).sum( axis=0 )
            emis_dict[ spc ][ start:end, ... ] += pdata.copy()
    
    if inc_icon is False:
        icon_dict = None
    return PhysicalAdjointData( icon_dict, emis_dict )
