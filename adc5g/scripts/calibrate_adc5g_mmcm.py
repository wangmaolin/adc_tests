import corr
import adc5g
import sys
import time
from optparse import OptionParser

p = OptionParser()
p.set_usage('%prog ROACH [options]')
p.set_description(__doc__)
p.add_option('-a', '--adcs', dest='adcs', type='string', default="0,1",
    help='Comma separated, spaceless list of ADCs to snap. Default:"0,1"')
p.add_option('--psrange', dest='psrange', type='int', default=100,
    help='Number of mmcm phase steps to scan. Default = 100. Check the eye \
          pattern carefully if you start changing this or your FPGA speed')

opts, args = p.parse_args(sys.argv[1:])

try:
    r = corr.katcp_wrapper.FpgaClient(sys.argv[1])
    time.sleep(0.01)
except IndexError:
    raise Exception("Index Error: Usage: %prog ROACH [options]")

adcs = map(int, opts.adcs.split(','))
n_adcs = len(adcs)

for an, adc in enumerate(adcs):
    if adc not in [0,1]:
        raise Exception("Zdok index %d is not 0 or 1"%adc)
    print 'Calibrating MMCM for ADC %s'%adc
    chosen, sweep = adc5g.calibrate_mmcm_phase(r, adc, ['P%d_DC'%adc], ps_range=100) 
    print 'Eye Scan (X=bad, 0=good, *=chosen delay):'
    for vn, v in enumerate(sweep):
        if vn == chosen: print '*',
        elif v == 0: print '0',
        else: print 'X',
    print ''

    # After calibration, do a few snaps to check for glitches. Just in case...
    for i in range(4):
        if adc5g.check_for_glitches(r, adc, ['P%d_DC'%adc]) != 0:
            raise Exception("After calibration glitch test FAILED!")
    
    print "ADC %d passed calibration and readback check!"%adc

