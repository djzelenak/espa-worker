
import os
import sys
import copy
import unittest
import logging
from mock import patch
from mocks import mock_api_response, mock_invalid_response
import processing
from processing.logging_tools import EspaLogging, LevelFilter
from processing.utilities import convert_json
from processing import parameters, config, config_utils, processor, product_formatting

EspaLogging.configure_base_logger()
# Initially set to the base logger
base_logger = EspaLogging.get_logger('base')

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add logging to stdout and stderr
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)
stdout_handler.addFilter(LevelFilter(10, 20))
base_logger.addHandler(stdout_handler)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)
stderr_handler.setFormatter(formatter)
stderr_handler.addFilter(LevelFilter(30, 50))
base_logger.addHandler(stderr_handler)

class TestProcessor(unittest.TestCase):
    def setUp(self):
        self.cfg = config.config()
        self.params = mock_api_response[0]
        self.params['product_id'] = self.params['scene']

        self.scene_to_instance = {
            'LC08': 'LC08_L1TP_128058_20160608_20170324_01_T1',
            'LT08': 'LT08_L1GT_116217_20130815_20170503_01_T2',
            'LO08': 'LO08_L1GT_024027_20130406_20170310_01_T2',
            'LE07': 'LE07_L1TP_024028_20190531_20190627_01_T1',
            'LT05': 'LT05_L1TP_023028_20111001_20160830_01_T1',
            'MOD': 'MOD09GA.A2019221.h11v04.006.2019223030533',
            'MYD': 'MYD09GA.A2019221.h11v04.006.2019223030533',
            'VNP': 'VNP09GA.A2019221.h11v04.001.2019222084825'
        }

    def tearDown(self):
        pass

    def test_convert_json(self):
        """
        Make sure that we can read the JSON and convert it to a list or dict object
        """
        data = convert_json(mock_api_response)
        self.assertTrue(type(data) is str)

        data = convert_json(data)
        self.assertTrue(type(data) in (dict, list))

    def test_parameters_valid(self):
        """
        Make sure our parameters testing works
        """
        self.assertTrue(parameters.test_for_parameter(self.params, 'options'))

    def test_parameters_invalid(self):
        """
        Make sure our paremeters testing works for catching invalid data
        """
        self.assertFalse(parameters.test_for_parameter(mock_invalid_response, 'options'))

    def test_env_vars_set(self):
        """
        Make sure that we are setting the environment variables required for processing
        """
        config.export_environment_variables(self.cfg)
        
        for _env in self.cfg.keys():
            self.assertTrue(_env.upper() in os.environ.keys())

    def test_get_pigz_num_threads(self):
        """
        Make sure we can get the configured number of pigz threads
        """
        self.assertTrue(type(config_utils.retrieve_pigz_cfg()) is str)

    def test_sensor_not_implemented(self):
        """
        Make sure that we catch a sensor that is not implemented
        """
        params = copy.deepcopy(self.params)
        params['product_id'] = self.scene_to_instance['LT08']
        with self.assertRaises(NotImplementedError):
            pp = processor.get_instance(self.cfg, params)
            del pp

    @patch('processing.processor.EspaLogging.get_logger')
    def test_get_instance(self, mock_logger):
        """
        Test that a sensor processing class instance is returned
        """
        params = copy.deepcopy(self.params)
        for code, scene in self.scene_to_instance.items():
            if code != 'LT08':
                params['product_id'] = scene
                pp=processor.get_instance(self.cfg, params)
                if code == 'LT05' or code == 'LT04':
                    self.assertTrue(type(pp) == processing.processor.LandsatTMProcessor)
                if code == 'LE07':
                    self.assertTrue(type(pp) == processing.processor.LandsatETMProcessor)
                if code == 'LC08':
                    self.assertTrue(type(pp) == processing.processor.LandsatOLITIRSProcessor)
                if code == 'LO08':
                    self.assertTrue(type(pp) == processing.processor.LandsatOLIProcessor)
                if code == 'VNP':
                    self.assertTrue(type(pp) == processing.processor.VIIRSProcessor)
                if code == 'MOD':
                    self.assertTrue(type(pp) == processing.processor.ModisTERRAProcessor)
                if code == 'MYD':
                    self.assertTrue(type(pp) == processing.processor.ModisAQUAProcessor)

    @patch('processing.processor.EspaLogging.get_logger')
    @patch('processing.processor.os.path.exists')
    @patch('processing.processor.os.getcwd')
    def test_check_work_dir(self, mock_getcwd, mock_exists, mock_logger):
        test_path = '/mnt/mesos/sandbox'
        mock_exists.return_value = True
        proc = processor.ProductProcessor(self.cfg, self.params)
        # Expect to return the input test_path unchanged
        result = proc.check_work_dir(test_path)
        self.assertEqual(test_path, result)

        test_path = ''
        mock_result = '/home/somewhere'
        mock_getcwd.return_value = mock_result
        mock_exists.return_value = False
        # Expect to return the mock current work dir
        result = proc.check_work_dir(test_path)
        self.assertEqual(mock_result, result)
