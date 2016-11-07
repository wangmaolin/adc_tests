import sys
import numpy as np
import unittest
from math import pi, sqrt, sin, atan2
from optparse import OptionParser
import time

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
        self.assertLess(rate, self._clk_rate/8. + 1.0)
        self.assertGreater(rate, self._clk_rate/8. - 1.0)

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
        print "calibration: 1 time"
        cls._optimal_phase, cls._glitches = adc5g.calibrate_mmcm_phase(
            cls._roach, cls._zdok_n, ['scope_raw_%d_snap' % cls._zdok_n])

        count = 0
        while (cls._optimal_phase is None and count < 20):
            print "Re-program the FPGA"
            ret = cls._roach.progdev(cls._dut)
            print ret

            print "calibration: ", count+2, " time"
            cls._optimal_phase, cls._glitches = adc5g.calibrate_mmcm_phase(
                cls._roach, cls._zdok_n, ['scope_raw_%d_snap' % cls._zdok_n])
            count = count + 1


    def test_optimal_solution_found(self):
        "test if calibration finds optimal MMCM phase"
        self.assertIsNotNone(self._optimal_phase)


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
	
    def test_output(self):
        "test output snapshot"
	background=np.array(self._raw[0:8*336])
	background=np.resize(background,(8,336))
	background=np.average(background,axis=0)
	imgraw=np.array(self._raw[0:48*336])
	imgraw=np.resize(imgraw,(48,336))
	imgsub=imgraw-background[None,:]
	imgabs=np.absolute(imgsub)
	linsum=np.sum(imgabs,axis=1)
	bgmean=np.mean(linsum)
	bgstd=np.std(linsum)
	print bgmean
	print bgstd
        print ""
        print "========================================="
        print "test signal Amp(min - max): " + str(0.5*(max(self._raw)-min(self._raw)))
        print "========================================="

        print "output the snapshot"
        snapoutput=open('snapshot','w')
        for item in self._raw:
            snapoutput.write("%s\n" % item)
        snapoutput.close()


ORDERED_TEST_CASES = [
    TestSetup,
    TestProgramming,
    TestBasics,
    TestCalibration,
    TestInitialSPIControl,
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
                      dest="boffile", metavar="BOFFILE", default="adc5g_test_2015_Nov_15_2344.bof",
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
