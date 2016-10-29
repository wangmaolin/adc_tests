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
#Decide where we're going to send the data, and from which addresses:
#dest_ip  =192*(2**24) + 168*(2**16) + 0*(2**8) + 32
dest_ip1 = 192*(2**24)+168*(2**16)+0*(2**8)+15
dest_ip2 = 192*(2**24)+168*(2**16)+0*(2**8)+115
dest_ip3 = 192*(2**24)+168*(2**16)+0*(2**8)+16
dest_ip4 = 192*(2**24)+168*(2**16)+0*(2**8)+116
dest_ip5 = 192*(2**24)+168*(2**16)+0*(2**8)+17
dest_ip6 = 192*(2**24)+168*(2**16)+0*(2**8)+117
dest_ip7 = 192*(2**24)+168*(2**16)+0*(2**8)+18
dest_ip8 = 192*(2**24)+168*(2**16)+0*(2**8)+118
fabric_port=160
fabric_port_wrong = 160       
source_ip1 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 71
source_ip2 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 72
source_ip3 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 75
source_ip4 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 74
source_ip5 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 75
source_ip6 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 76
source_ip7 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 77
source_ip8 = 192*(2**24) + 168*(2**16) + 0*(2**8) + 78

#mac_base=(2<<40) + (2<<32)
#dest_mac = 20015998369792
#source_mac = 20015998304256
dest_mac = 78187493632
source_mac1 = 78187493376
source_mac2 = 78187493377
source_mac3 = 78187493378
source_mac4 = 78187493379
source_mac5 = 78187493380
source_mac6 = 78187493381
source_mac7 = 78187493382
source_mac8 = 78187493383

tx_core_name1 = 'ten_Gbe0'
tx_core_name2 = 'ten_Gbe1'
tx_core_name3 = 'ten_Gbe2'
tx_core_name4 = 'ten_Gbe3'
tx_core_name5 = 'ten_Gbe4'
tx_core_name6 = 'ten_Gbe5'
tx_core_name7 = 'ten_Gbe6'
tx_core_name8 = 'ten_Gbe7'

#rx_core_name = 'gbe3'
pkt_period = 1024 #1024 #3413#5000#4824#350#70#230#130800#16384  #how often to send another packet in FPGA clocks (200MHz)
payload_len = 1024 # 16#128#1024#128   #how big to make each packet in 64bit words
#inter_gap = 1  #collect data at ? th data point

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
        global roach, boffile, zdok_n, clk_rate, tone_freq, tone_amp
        cls._roach = roach
        cls._dut = boffile
        cls._zdok_n = zdok_n
        cls._clk_rate = clk_rate
        cls._tone_freq = tone_freq
        cls._tone_amp = tone_amp


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
        #adc5g.get_snapshot(self._roach, 'scope_raw_%d_snap' % self._zdok_n)
        self.assertEqual(ret, "ok")
        #self._roach.write_int('delay_fifo_enable', 0)
        #self._roach.write_int('delay_fifo_en_tri', 0)
 

class TestBasics(TestBase):

    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()

        cls._devices = DevList(cls._roach.listdev())

    def test_clk_rate(self):
        "estimate clock rate, should be within 1 MHz of expected"
        rate = self._roach.est_brd_clk()
        print "\nTESTING FREQ RATE:  ~~~~~", rate
       # self.assertLess(rate, self._clk_rate/8. + 1.0)
        #self.assertGreater(rate, self._clk_rate/8. - 1.0)

    def test_has_adc_controller(self):
        "confirm the design has the ADC SPI controller"
        self.assertIn('adc5g_controller', self._devices)
        
    def test_has_scope(self):
        "confirm the design has the needed scope"
        self.assertIn('snap_bram', self._devices)
        self.assertIn('snap_ctrl', self._devices)
        self.assertIn('snap_status', self._devices)


class TestCalibrationSimple(TestBase):

    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
        SNAPNAME = 'snap'
        #logger.debug("calibration: 1 time")
        print "calibration: 1 time"
        cls._optimal_phase, cls._glitches = adc5g.calibrate_mmcm_phase(
            cls._roach, cls._zdok_n, [SNAPNAME])

        #logger.debug( cls._optimal_phase)
        print cls._optimal_phase
        count = 0
        while (cls._optimal_phase is None and count < 20):
            #logger.debug(  "Re-program the FPGA")
            print "Re-program the FPGA"
            ret = cls._roach.progdev(cls._dut)
            #logger.debug(ret)
            print ret
            
            print "calibration: ", count+2, " time"
            #logger.debug("calibration %d time"%(count+2))
            cls._optimal_phase, cls._glitches = adc5g.calibrate_mmcm_phase(
                cls._roach, cls._zdok_n, [SNAPNAME])
            count = count + 1
            

    def test_optimal_solution_found(self):
        "test if calibration finds optimal MMCM phase"
        self.assertIsNotNone(self._optimal_phase)


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
	BOFFILE ='adcethvfullv64zdk1_2015_Oct_09_1201.bof' #'adcethvfullv64_2015_Sep_09_0946.bof' #'adcethvfullv61_2015_Sep_02_1653.bof' #'adc5g_test_2014_Jul_21_2138.bof'#1649.bof' #'adc5g_test_rev2.bof'
	ROACH = '192.168.100.182'  #182 or 2
	#ROACH = '10.0.1.213'
	SNAPNAME = 'snap'#'scope_raw_0_snap'

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

class TestGBE(TestBase):
    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()
        
    def test_1link_up(self):
       # global dest_ip, dest_mac, fabric_port, rx_core_name
       # gbe0_link = bool(self._roach.read_int('gbe3_linkup'))
       # self.assertNotEqual(gbe0_link, 0)
        #gbe3_link = bool(self._roach.read_int('gbe_linkup'))
        #self.assertNotEqual(gbe3_link, 0)   
        print 'done1'
        
    def test_2with_config(self):
        #Configuring receiver core
       # global dest_ip
       # self._roach.tap_start('tap03',rx_core_name,dest_mac,dest_ip,fabric_port)
        #Configuring transmitter core
	global source_ip
	self._roach.tap_start('tap1',tx_core_name1,source_mac1,source_ip1,fabric_port)
	self._roach.tap_start('tap2',tx_core_name2,source_mac2,source_ip2,fabric_port)
	self._roach.tap_start('tap3',tx_core_name3,source_mac3,source_ip3,fabric_port)
	self._roach.tap_start('tap4',tx_core_name4,source_mac4,source_ip4,fabric_port)
	self._roach.tap_start('tap5',tx_core_name5,source_mac5,source_ip5,fabric_port)
	self._roach.tap_start('tap6',tx_core_name6,source_mac6,source_ip6,fabric_port)
	self._roach.tap_start('tap7',tx_core_name7,source_mac7,source_ip7,fabric_port)
	self._roach.tap_start('tap8',tx_core_name8,source_mac8,source_ip8,fabric_port)

        print dest_ip1
	print dest_ip2
        #Setting-up destination addresses...
        self._roach.write_int('dest_ip0',dest_ip1)
	self._roach.write_int('dest_ip1',dest_ip2)
	self._roach.write_int('dest_ip2',dest_ip3)
	self._roach.write_int('dest_ip3',dest_ip4)
	self._roach.write_int('dest_ip4',dest_ip5)
	self._roach.write_int('dest_ip5',dest_ip6)
	self._roach.write_int('dest_ip6',dest_ip7)
	self._roach.write_int('dest_ip7',dest_ip8)


        self._roach.write_int('dest_port0',fabric_port)
        self._roach.write_int('dest_port1',fabric_port)
        self._roach.write_int('dest_port2',fabric_port)
        self._roach.write_int('dest_port3',fabric_port)
	self._roach.write_int('dest_port4',fabric_port)
        self._roach.write_int('dest_port5',fabric_port)
        self._roach.write_int('dest_port6',fabric_port)
        self._roach.write_int('dest_port7',fabric_port)

        #Resetting cores and counters
        self._roach.write_int('rst', 3)
	time.sleep(2)
        self._roach.write_int('rst', 0)
        print 'done2'
        
        
    def test_3start_capture(self):
        #self._roach.write_int('delay_fifo_en_tri', 1)
        #self._roach.write_int('delay_fifo_en_tri', 0)
        #time.sleep(3)

        #self._roach.write_int('delay_fifo_enable', 1)
       	print 'Setting-up packet source...',
    	sys.stdout.flush()
    	self._roach.write_int('pktsim_period',pkt_period)
    	self._roach.write_int('pktsim_payload_len',payload_len)
	self._roach.write_int('pktsim_test_or_adc',1) # sharat 0 for test counter 1 for ADC
	#self._roach.write_int('pkt_sim_inter_gap1',inter_gap)

	self._roach.write_int('pktsim1_period',pkt_period)
        self._roach.write_int('pktsim1_payload_len',payload_len)
        self._roach.write_int('pktsim1_test_or_adc',1) #sharat 0 for adc test 1 for adc
	#self._roach.write_int('pkt_sim1_inter_gap1',inter_gap)

 
        #self._roach.write_int('delay_fifo_en_tri', 1)
        #self._roach.write_int('delay_fifo_en_tri', 0)

        print 'done3'
        time.sleep(2)
	self._roach.write_int('enable', 1)
       # self._roach.write_int('pktsim1_enable1', 1)

	#self._roach.write_int('delay_fifo_enable', 0)      
        
class TestSnapshot(TestBase):
    @classmethod
    def setUpClass(cls):
        TestBase.setUpClass()

        cls._sample_rate = cls._clk_rate * 2.
        cls._tone_per = int(round(cls._sample_rate / cls._tone_freq))
        #cls._raw = adc5g.get_snapshot(cls._roach, 'delay_fifo_snap', False, 0 )
        #cls._raw2 = adc5g.get_snapshot(cls._roach, 'snap', False, 0)
        
        #cls._raw = list(samp for samp in cls._raw)
        #cls._raw2 = list(samp for samp in cls._raw2)
        #print "THE AMPLITUDE: ", cls._raw
        #print "THE AMPLITUDE2: ", cls._raw2
        #cls._bias = (cls._raw[0] + cls._raw[cls._tone_per/2])/2.
        #cls._amp = sqrt((cls._raw[0]-cls._bias)**2 + (cls._raw[cls._tone_per/4]-cls._bias)**2)
        
        #cls._phase = atan2((cls._raw[0]-cls._bias)/cls._amp, (cls._raw[125]-cls._bias)/cls._amp)
        #cls._fit = list(cls._amp*sin(t*2*pi/cls._tone_per + cls._phase) + cls._bias \
                        #for t in range(len(cls._raw)))
        #cls._roach.write_int('delay_fifo_enable', 0)  

    def test_total_bias(self):
        "check the overall bias of the signal"
        #self.assertLess(abs(self._bias), 5.)

    def test_total_amplitude(self):
        "check the amplitude of the signal"
        #self.assertLess(abs(self._amp - self._tone_amp), 5.)
        
    def test_total_noise(self):
        "check the total noise level"
        #noise = list(self._raw[i]-self._fit[i] for i in range(len(self._raw)))
        #noise_lvl = sqrt(sum(nsamp**2 for nsamp in noise)/len(noise))
        #self.assertLess(noise_lvl, 5.)
        

ORDERED_TEST_CASES = [
    TestSetup,
    TestProgramming,
    TestBasics,
    TestCalibration,
    #TestCalibrationSimple,
    #TestInitialSPIControl,
    TestGBE,
    TestSnapshot,
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
    global roach, boffile, zdok_n, clk_rate, tone_freq, tone_amp
    parser = OptionParser()
    parser.add_option("-v", action="store_true", dest="verbose",
                      help="use verbose output while testing")
    parser.add_option("-r", "--remote",
                      dest="remote", metavar="HOST:PORT",
                      help="run tests remotely over katcp using HOST and PORT")
    parser.add_option("-b", "--boffile",
                      dest="boffile", metavar="BOFFILE", default="adcethvfullv61_2015_Sep_02_1653.bof", #adcethvfullv2_2014_Dec_11_1649.bof",
								#adcethvfullv1_2014_Dec_04_1703.bof", 
							         #"adcethvfullv1_2014_Oct_09_1231.bof",
                      help="test using the BOFFILE bitcode")
    parser.add_option("-z", "--zdok",
                      dest="zdok_n", metavar="ZDOK", type='int', default=0,
                      help="test the ADC in the ZDOK port")
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
    run_tests(verbosity)


if __name__ == "__main__":
    main()
