
import os

from fourdvar.params.root_path_defn import store_path

#full path to the prior file used by user_driver.get_background
#prior_file = os.path.join( store_path, 'input/prior.ncf' )
prior_file = os.path.join( store_path, 'input/prior_6day.nc' )

#full path to the obs file used by user_driver.get_observed
#obs_file = os.path.join( store_path, 'input/observed.pickle.zip' )
obs_file = os.path.join( store_path, 'input/observed_6day_omit_26_22.pic.gz' )

#include model initial conditions in solution
inc_icon = False
