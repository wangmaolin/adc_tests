import numpy as np
import adc5g as adc
import corr
import time
import sys
import struct
import pylab
import fit_cores
import rww_tools
import scipy.optimize


def snap(r,name,format='L',man_trig=True,wait_period=10):
    n_bytes = struct.calcsize('=%s'%format)
    d = r.snapshot_get(name, man_trig=man_trig, wait_period=wait_period)
    return np.array(struct.unpack('>%d%s'%(d['length']/n_bytes,format),d['data']))

def uint2int(d,bits,bp,complex=False):
    if complex:
        dout_r = (np.array(d) & (((2**bits)-1)<<bits)) >> bits
        dout_i = np.array(d) & ((2**bits)-1)
        dout_r = uint2int(dout_r,bits,bp,complex=False)
        dout_i = uint2int(dout_i,bits,bp,complex=False)
        return dout_r + 1j*dout_i
    else:
        dout = np.array(d,dtype=float)
        dout[dout>(2**(bits-1))] -= 2**bits
        dout /= 2**bp
        return dout


if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser()
    p.set_usage('%prog [options]')
    p.set_description(__doc__)
    p.add_option('-p', '--skip_prog', dest='prog_fpga',action='store_false', default=True,
        help='Skip FPGA programming (assumes already programmed).  Default: program the FPGAs')
    #p.add_option('-e', '--skip_eq', dest='prog_eq',action='store_false', default=True, 
    #    help='Skip configuration of the equaliser in the F engines.  Default: set the EQ according to config file.')
    p.add_option('-v', '--verbosity', dest='verbosity',type='int', default=0,
        help='Verbosity level. Default: 0')
    p.add_option('-r', '--roach', dest='roach',type='str', default='192.168.0.111',
        help='ROACH IP address or hostname. Default: 192.168.0.111')
    p.add_option('-b', '--boffile', dest='boffile',type='str', default='ami_fx_sbl_wide.bof',
        help='Boffile to program. Default: ami_fx_sbl_wide.bof')
    p.add_option('-N', '--n_trials', dest='n_trials',type='int', default=2,
        help='Number of snap/fit trials. Default: 2')
    p.add_option('-c', '--clockrate', dest='clockrate', type='float', default=None,
        help='Clock rate in MHz, for use when plotting frequency axes. If none is given, rate will be estimated from FPGA clock')
    p.add_option('-f', '--testfreq', dest='testfreq', type='float', default=25.0,
        help='sine wave test frequency input in MHz. Default = 25')

    opts, args = p.parse_args(sys.argv[1:])

    print 'Connecting to %s'%opts.roach
    r = corr.katcp_wrapper.FpgaClient(opts.roach)
    time.sleep(0.2)
    print 'ROACH is connected?', r.is_connected()

    rww_tools.roach2 = r
    rww_tools.snap_name='snapshot_adc0'
    rww_tools.samp_freq=4000.
    FNAME = 'snapshot_adc0_raw.dat'

    if opts.prog_fpga:
        print 'Programming ROACH with boffile %s'%opts.boffile
        r.progdev(opts.boffile)
        time.sleep(0.5)

    print 'Estimating clock speed...'
    clk_est = r.est_brd_clk()
    print 'Clock speed is %d MHz'%clk_est
    if opts.clockrate is None:
        clkrate = clk_est*16
    else:
        clkrate = opts.clockrate

    if opts.prog_fpga:
        print 'Calibrating ADCs'
        adc.calibrate_all_delays(r,0,snaps=['snapshot_adc0'],verbosity=opts.verbosity)
        #adc.calibrate_all_delays(r,1,snaps=['snapshot_adc1'],verbosity=opts.verbosity)

    print 'clearing OGP'
    rww_tools.clear_ogp()
    print 'sleeping for 5s'
    time.sleep(5)

    #Do the calibration
    print 'doing calibration'
    ogp, sinad = rww_tools.dosnap(fr=opts.testfreq,name=FNAME,rpt=opts.n_trials,donot_clear=False)

    ogp = ogp[3:]
    print 'OGP:',ogp
    print 'SINAD:',sinad

    np.savetxt('ogp',ogp,fmt='%8.4f')

    print 'Setting ogp'
    rww_tools.set_ogp('ogp')
    print 'done'


    exit()
    
    


