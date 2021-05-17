"""
calc_forcing.py

Copyright 2016 University of Melbourne.
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import numpy as np

from fourdvar.datadef import AdjointForcingData
import fourdvar.params.model_data as model_data

def calc_forcing( w_residual ):
    """
    application: calculate the adjoint forcing values from the weighted residual of observations
    input: ObservationData  (weighted residuals)
    output: AdjointForcingData
    """
    force_arr = np.zeros( model_data.gradient.shape[1:] )
    for o_val, w_dict in zip( w_residual.value, w_residual.weight_grid ):
        for coord, weight in w_dict.items():
            (row,col,) = coord
            force_arr[row,col] += (o_val * weight)
    
    return AdjointForcingData.create_new( force_arr )
