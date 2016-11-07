import sys
import adc5g
import corr
import time
import pylab
import numpy as np

BOFFILE = 'dumy_2015_Sep_15_1223.bof'
ROACH = '192.168.100.182'  #182 or 2

def br(x):
    return np.binary_repr(x, width=8)

r = corr.katcp_wrapper.FpgaClient(ROACH)
time.sleep(0.1)

r.progdev(BOFFILE)
