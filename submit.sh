#!/bin/bash

#PBS -N py4dvar
#PBS -l walltime=24:00:00
#PBS -l mem=32GB
#PBS -l ncpus=16
#PBS -q express
#PBS -l wd
#PBS -l jobfs=5GB

#module use /g/data3/hh5/public/modules
#module load conda/analysis27

python runscript.py >& output.txt
