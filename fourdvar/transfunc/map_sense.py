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
        
        rhoj_interp = np.zeros(target_shape)
        for r in range(reps):
            frac = float(2*r+1) / float(2*reps)
            rhoj_interp[r:-1:reps,...] = (1-frac)*rhoj[:-1,...] + frac*rhoj[1:,...]
        rhoj_interp[-1,...] = rhoj[-1,...]
        unit_array = (ppm_scale*kg_scale*mwair) / (rhoj_interp*lay_thick)
        
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
    #- PhysicalAdjointData params exist
    #- template.emis & template.sense_emis are compatible
    #- template.icon & template.sense_conc are compatible
    datelist = dt.get_datelist()
    PhysicalAdjointData.assert_params()
    #all spcs use same dimension set, therefore only need to test 1.
    test_spc = PhysicalAdjointData.spcs[0]
    test_fname = dt.replace_date( template.emis, dt.start_date )
    mod_shape = ncf.get_variable( test_fname, test_spc ).shape    
    
    #phys_params = ['tstep','nstep','nlays_icon','nlays_emis','nrows','ncols','spcs']
    #icon_dict = { spcs: scale_value }
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
            icon_dict[ spc ] = (sense_data * icon_data).sum()

    daysec = 24*60*60
    t = int( ncf.get_attr( test_fname, 'TSTEP' ) )
    m_tstep = 3600*( t//10000 ) + 60*( (t//100) % 100 ) + ( t%100 )

    p_tstep = [ t for t in PhysicalAdjointData.tstep ]
    msg = 'physical & model input emis TSTEP incompatible.'
    assert all([ t % m_tstep == 0 for t in p_tstep ]), msg

    e_count = [ p//m_tstep for p in p_tstep ] #emis count per phys timestep
    t = 0 #current phys time index
    m_len = daysec // m_tstep #No. emis steps per model day
    emis_pattern = 'emis.<YYYYMMDD>'
    for date in datelist:
        p_ind = [] #time index of phys data
        m_slice = [0] #No. repeats of phys index above (for today)
        r = 0
        #drain phys reps until a full day is filled, record which index's used
        while r < m_len:
            p_ind.append( t )
            s = min(e_count[t],m_len)
            m_slice.append( r+s )
            r += s
            e_count[t] -= s
            if e_count[t] <= 0:
                t += 1
        m_slice = [ (t0,t1) for t0,t1 in zip(m_slice[:-1],m_slice[1:]) ]
        #check index & rep
        assert (np.diff( p_ind ) == 1).all(), "index out of alignment"
        assert m_slice[-1][1] == m_len, "m_slice doesn't cover all emis timesteps"

        # get sensitivity data
        label = dt.replace_date( emis_pattern, date )
        sense_fname = sensitivity.file_data[ label ][ 'actual' ]
        sense_data_dict = ncf.get_variable( sense_fname, PhysicalAdjointData.spcs )
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
            sense_arr = sdata[ :-1, :mlay, :, : ]
            model_arr = sense_arr.reshape((mstep-1,-1,mlay,mrow,mcol)).sum(axis=1)
            play = PhysicalAdjointData.nlays_emis
            model_arr = model_arr[ :, :play, :, : ]

            #add p_rep model_arr steps to p_ind physical timstep
            for ind, (start,end) in zip( p_ind, m_slice ):
                phys_arr = model_arr[ start:end, ... ].sum( axis=0 )
                emis_dict[ spc ][ ind, ... ] += phys_arr
    
    if inc_icon is False:
        icon_dict = None
    return PhysicalAdjointData( icon_dict, emis_dict )
