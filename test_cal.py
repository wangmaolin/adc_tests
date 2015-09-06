import logging, logging.handlers
import sys
import adc5g
import corr
import time
import pylab
import numpy as np

BOFFILE = 'adc5g_test_rev2.bof'
ROACH = '10.0.1.213'
SNAPNAME = 'scope_raw_0_snap'

def br(x):
    return np.binary_repr(x, width=8)

r = corr.katcp_wrapper.FpgaClient(ROACH)
time.sleep(0.1)

r.progdev(BOFFILE)

adc5g.set_test_mode(r, 0, counter=False)
adc5g.sync_adc(r)
adc5g.calibrate_all_delays(r, 0, snaps=[SNAPNAME], verbosity=5)
#adc5g.calibrate_mmcm_phase(r, 0, ['snap'])
#adc5g.unset_test_mode(r, 0)
#a, b, c, d = adc5g.get_test_vector(r, ['snap'])
a, b, c, d = adc5g.get_test_vector(r, [SNAPNAME])
#x = adc5g.get_snapshot(r, 'scope_raw_0_snap')
#a = x[0::4]
#b = x[1::4]
#c = x[2::4]
#d = x[3::4]

for i in range(32):
    print br(a[i]), br(b[i]), br(c[i]), br(d[i])

for cn, core in enumerate([a,b,c,d]):
    pylab.plot(np.array(core) & 0xf, label='%d'%cn)
pylab.legend()
pylab.show()

