
import os
import copy
import unittest
from mocks import mock_api_response, mock_invalid_response
from processing.main import convert_json
from processing import parameters, config, utilities, config_utils, settings

class TestProcessing(unittest.TestCase):
    def setUp(self):
        self.cfg = config.config()

    def tearDown(self):
        pass

    def test_convert_json(self):
        """
        Make sure that we can read the JSON and convert it to a list object
        :return:
        """
        input = convert_json(mock_api_response)
        self.assertTrue(type(input) is list)

    def test_parameters_valid(self):
        """
        Make sure our parameters testing works
        :return:
        """
        input = convert_json(mock_api_response)
        self.assertTrue(parameters.test_for_parameter(input[0], 'options'))

    def test_parameters_invalid(self):
        """
        Make sure our paremeters testing works for catching invalid data
        :return:
        """
        input = convert_json(mock_invalid_response)
        self.assertFalse(parameters.test_for_parameter(input[0], 'options'))

    def test_env_vars_set(self):
        """
        Make sure that we are setting the environment variables required for processing
        :return: 
        """
        config.export_environment_variables(self.cfg)
        
        for _env in self.cfg.keys():
            self.assertTrue(os.environ.get(_env) is not None)

    def test_get_pigz_num_threads(self):
        """
        Make sure we can get the configured number of pigz threads
        :return:
        """
        self.assertTrue(type(config_utils.retrieve_pigz_cfg()) is str)
