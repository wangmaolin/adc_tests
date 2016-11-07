import sys
import adc5g
import corr 
import time
import pylab
import numpy as np
import unittest
import time, struct, sys, logging, socket
from struct import pack, unpack
from math import pi, sqrt, sin, atan2
from optparse import OptionParser

import adc5g

try:
    from corr import katcp_wrapper
    REMOTE_POSSIBLE = True
except ImportError:
    REMOTE_POSSIBLE = False
class BofList(list):

    def __repr__(self):
        size = self.__len__()
        return "%d available BOF files" % size


class DevList(list):

    def __repr__(self):
        size = self.__len__()
        return "%d software accessible devices" % size


class ADC5GTestResult(unittest.TextTestResult):

    def getDescription(self, test):
        return test.shortDescription()


class TestBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global roach, boffile, zdok_n, clk_rate, tone_freq, tone_amp, tv
        cls._roach = roach
        cls._dut = boffile
        cls._zdok_n = zdok_n
        cls._clk_rate = clk_rate
        cls._tone_freq = tone_freq
        cls._tone_amp = tone_amp
	cls._tv = tv


class TestSetup(TestBase):

    def test_connected(self):
        "test roach connectivity"
        self.assertTrue(self._roach.is_connected())

    def test_ping(self):
        "test roach pingability"
        self.assertTrue(self._roach.ping())

    def test_listbof(self):
        "check if requested bof is available"
        bofs = BofList(self._roach.listbof())
        self.assertIn(self._dut, bofs)


class TestProgramming(TestBase):

    def test_progdev(self):
        "program the requested bof"
        ret = self._roach.progdev(self._dut)
        print "\nprogram bof"
        self.assertEqual(ret, "ok")
 

class TestBasics(TestBase):

    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()

        cls._devices = DevList(cls._roach.listdev())

    def test_clk_rate(self):
        "estimate clock rate, should be within 1 MHz of expected"
        rate = self._roach.est_brd_clk()
        print "\nTESTING FREQ RATE:  ~~~~~", rate

    def test_has_adc_controller(self):
        "confirm the design has the ADC SPI controller"
        self.assertIn('adc5g_controller', self._devices)
        
    def test_has_scope(self):
        "confirm the design has the needed scope"
        self.assertIn('scope_raw_%d_snap_bram' % self._zdok_n, self._devices)
        self.assertIn('scope_raw_%d_snap_ctrl' % self._zdok_n, self._devices)
        self.assertIn('scope_raw_%d_snap_status' % self._zdok_n, self._devices)

class TestCalibration(TestBase):

    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
 	adc5g.set_test_mode(cls._roach,0)
        adc5g.set_test_mode(cls._roach,1)

        #adc5g.set_test_mode(cls._roach,1)
        print "\nSETTING SYN"
        #adc5g.sync_adc(self._roach)
       # cls._optimal_phase, cls._glitches = adc5g.calibrate_mmcm_phase(
            #cls._roach, cls._zdok_n, ['scope_raw_%d_snap_bram' % cls._zdok_n])
        #    cls._roach, cls._zdok_n, ['snap']) 
        #BOFFILE = 'adc5g_test.bof'
	ROACH = '192.168.100.182'  #182 or 2
	#ROACH = '10.0.1.213'
	SNAPNAME ='scope_raw_0_snap'

	def br(x):
	    return np.binary_repr(x, width=8)

	r = corr.katcp_wrapper.FpgaClient(ROACH)
	time.sleep(0.1)

	#r.progdev(BOFFILE)

	adc5g.set_test_mode(r, 0, counter=False)
	adc5g.sync_adc(r)
	adc5g.calibrate_all_delays(r, 0, snaps=[SNAPNAME], verbosity=5)
#	adc5g.calibrate_mmcm_phase(r, 0, [SNAPNAME])

	#adc5g.calibrate_mmcm_phase(r, 0, ['snap'])
	adc5g.unset_test_mode(r, 0)
	#a, b, c, d = adc5g.get_test_vector(r, ['snap'])
	a, b, c, d = adc5g.get_test_vector(r, [SNAPNAME])
	#x = adc5g.get_snapshot(r, 'scope_raw_0_snap')
	#a = x[0::4]
	#b = x[1::4]
	#c = x[2::4]
	#d = x[3::4]
	
	for i in range(32):
	    print br(a[i]), br(b[i]), br(c[i]), br(d[i])

#	for cn, core in enumerate([a,b,c,d]):
#	    pylab.plot(np.array(core) & 0xf, label='%d'%cn)
#	pylab.legend()
	#pylab.show()
#	adc5g.unset_test_mode(roach, 0)
 #       adc5g.unset_test_mode(roach, 1)
#	time.sleep(4)
	print "\ntest finished"
#	r.progdev(BOFFILE)
    def test_optimal_solution_found(self):
        "test if calibration finds optimal MMCM phase"
       	#self.assertIsNotNone(self._optimal_phase)
	adc5g.unset_test_mode(roach, 0)
        adc5g.unset_test_mode(roach, 1)
        time.sleep(5)

class TestInitialSPIControl(TestBase):

    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
        cls._control_dict = adc5g.get_spi_control(cls._roach, cls._zdok_n)

    def assertControlParameterIs(self, param, value, msg=None):
        if self._control_dict[param] != value:
            standardMsg = "Control parameter '%s' is not %r" % (param, value)
            self.fail(self._formatMessage(msg, standardMsg))

    def test_adc_mode(self):
        "mode must be single-input A"
        self.assertControlParameterIs('adcmode', 8)

    def test_bandwidth(self):
        "bandwidth should be set to full 2 GHz"
        self.assertControlParameterIs('bdw', 3)

    def test_gray_code(self):
        "gray code should be enabled"
        self.assertControlParameterIs('bg', 1)

    def test_demux(self):
        "demux should be 1:1"
        self.assertControlParameterIs('dmux', 1)

    def test_full_scale(self):
        "full scale should be set to 500 mVpp"
        self.assertControlParameterIs('fs', 0)

    def test_standby(self):
        "board should be in full active mode"
        self.assertControlParameterIs('stdby', 0)

    def test_ramp_disabled(self):
        "ramp mode is off"
        self.assertControlParameterIs('test', 0)

class TestSnapshot(TestBase):
    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
        cls._raw = adc5g.get_snapshot(cls._roach, 'scope_raw_%d_snap' % cls._zdok_n)
    def test_threshold(self):
        "calculate detection threshold"	
    def test_output(self):
        "test output snapshot"
        print ""
        print "========================================="
        print "test signal Amp(min - max): " + str(0.5*(max(self._raw)-min(self._raw)))
        print "========================================="

        print "output the snapshot"
        snapoutput=open('snapshot','w')
        for item in self._raw:
            snapoutput.write("%s\n" % item)
        snapoutput.close()
 
class TestGBE(TestBase):
    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
       
    def test_link_config(self):
        "config eth link"
	print "config eth interface of FPGA"
	dest_ip0 = 192*(2**24)+168*(2**16)+0*(2**8)+15
	dest_ip1 = 192*(2**24)+168*(2**16)+0*(2**8)+115
	dest_ip2 = 192*(2**24)+168*(2**16)+0*(2**8)+16
	dest_ip3 = 192*(2**24)+168*(2**16)+0*(2**8)+116
	fabric_port=160
	source_ip0 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 71
	source_ip1 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 72
	source_ip2 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 75
	source_ip3 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 74
	dest_mac = 78187493632
	source_mac0 = 78187493376
	source_mac1 = 78187493377
	source_mac2 = 78187493378
	source_mac3 = 78187493379

	tx_core_name0 = 'ethout_ten_Gbe0'
	tx_core_name1 = 'ethout_ten_Gbe1'
	tx_core_name2 = 'ethout_ten_Gbe2'
	tx_core_name3 = 'ethout_ten_Gbe3'

	self._roach.tap_start('tap0',tx_core_name0,source_mac0,source_ip0,fabric_port)
	self._roach.tap_start('tap1',tx_core_name1,source_mac1,source_ip1,fabric_port)
	self._roach.tap_start('tap2',tx_core_name2,source_mac2,source_ip2,fabric_port)
	self._roach.tap_start('tap3',tx_core_name3,source_mac3,source_ip3,fabric_port)

        #Setting-up destination addresses...
        self._roach.write_int('ethout_dest_ip0',dest_ip0)
	self._roach.write_int('ethout_dest_ip1',dest_ip1)
	self._roach.write_int('ethout_dest_ip2',dest_ip2)
	self._roach.write_int('ethout_dest_ip3',dest_ip3)


        self._roach.write_int('ethout_dest_port0',fabric_port)
        self._roach.write_int('ethout_dest_port1',fabric_port)
        self._roach.write_int('ethout_dest_port2',fabric_port)
        self._roach.write_int('ethout_dest_port3',fabric_port)

        #Resetting cores and counters
        self._roach.write_int('ethout_rst', 3)
	time.sleep(2)
        self._roach.write_int('ethout_rst', 0)
        print 'link config done'

class TestDetect(TestBase):
    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
        
    def test_start_capture(self):
       	"reset config detect logic"
        self._roach.write_int('tv',self._tv)
	print 'write detect threshold value'
	print self._tv
        self._roach.write_int('adc_enable',1)
	print 'detect enable'


ORDERED_TEST_CASES = [
    TestSetup,
    TestProgramming,
    TestBasics,
    TestCalibration,
    TestInitialSPIControl,
    TestSnapshot,
    TestGBE,
    TestDetect,
    ]


def print_tests(option, opt, value, parser):
    msg = ''
    loader = unittest.TestLoader()
    for i, test_case in enumerate(ORDERED_TEST_CASES):
        if test_case.__doc__:
            msg += "\r\n%d. %s\r\n" % (i, test_case.__doc__)
        else:
            msg += "\r\n%d. %s\r\n" % (i, test_case.__name__)
        for j, name in enumerate(loader.getTestCaseNames(test_case)):
            test = getattr(test_case, name)
            if hasattr(test_case, '__doc__'):
                msg += " .%d %s\r\n" % (j, test.__doc__)
            else:
                msg += " .%d %s\r\n" % (j, name)
    print msg
    sys.exit()


def run_tests(verbosity):
    loader = unittest.TestLoader()
    full_suite = unittest.TestSuite(list(loader.loadTestsFromTestCase(test) for test in ORDERED_TEST_CASES))
    runner = unittest.TextTestRunner(verbosity=verbosity, failfast=True, resultclass=ADC5GTestResult)
    runner.run(full_suite)


def main():
    global roach, boffile, zdok_n, clk_rate, tone_freq, tone_amp, tv
    parser = OptionParser()
    parser.add_option("-v", action="store_true", dest="verbose",
                      help="use verbose output while testing")
    parser.add_option("-r", "--remote",
                      dest="remote", metavar="HOST:PORT",
                      help="run tests remotely over katcp using HOST and PORT")
    parser.add_option("-b", "--boffile",
                      dest="boffile", metavar="BOFFILE", default="maolintest.bof",
                      help="test using the BOFFILE bitcode")
    parser.add_option("-z", "--zdok",
                      dest="zdok_n", metavar="ZDOK", type='int', default=0,
                      help="test the ADC in the ZDOK port")
    parser.add_option("-t", "--threshold",
                      dest="tv", metavar="TV", type='int', default=125,
                      help="threshold value for detection")
    parser.add_option("-c", "--clk-rate",
                      dest="clk_rate", metavar="CLK_MHZ", type='float', default=2500.0,
                      help="specify the input clock frequency in MHz")
    parser.add_option("-f", "--tone-freq",
                      dest="tone_freq", metavar="TONE_FREQ_MHZ", type='float', default=10.0,
                      help="specify the input tone frequency in MHz")
    parser.add_option("-a", "--tone-amp",
                      dest="tone_amp", metavar="TONE_AMP_FS", type='float', default=0.64,
                      help="specify the input tone amplitude in units of full-scale")
    parser.add_option("-l", "--list", action="callback", callback=print_tests,
                      help="list info on the tests that will be run")
    (options, args) = parser.parse_args()
    if options.verbose:
        verbosity = 2
    else:
        verbosity = 1
    if options.remote:
        if REMOTE_POSSIBLE:
            roach = katcp_wrapper.FpgaClient(*options.remote.split(':'))
            roach.wait_connected(1)
        else:
            raise ImportError("corr package was not found, "
                              "remote operation not possible!")
    else:
        roach = adc5g.LocalRoachClient()
    boffile = options.boffile
    zdok_n = options.zdok_n
    clk_rate = options.clk_rate
    tone_freq = options.tone_freq
    tone_amp = options.tone_amp * 128.
    tv = options.tv

    run_tests(verbosity)


if __name__ == "__main__":
    main()
