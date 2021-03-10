"""
scope_em_file_defn.py

Copyright 2016 University of Melbourne.
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

import os

from fourdvar.params.root_path_defn import store_path

em_path = os.path.join( store_path, 'emulate' )

'''
#list of input structs & emulation files, for each model index.
em_input_struct_fname = [
    os.path.join( em_path, 'quick_test_input.pic' )
]

emulation_fname = [
    os.path.join( em_path, 'quick_test_emulate.npz' )
]
'''
#list of input structs & emulation files, for each model index.
em_input_struct_fname = [
    os.path.join( em_path, 'test_input.pic' )
]

emulation_fname = [
    os.path.join( em_path, 'test_emulate.npz' )
]