
import sys
import copy
import unittest
import logging
from mock import patch, mock_open, call
from mocks import mock_api_response

from processing import config, distribution, staging
from processing.logging_tools import EspaLogging, LevelFilter

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

class TestStaging(unittest.TestCase):
    def setUp(self):
        self.cfg = config.config()
        self.params = mock_api_response[0]
        self.params['product_id'] = self.params['scene']

        self.test_product_full_path = '/destination_directory/product_name'
        self.test_product_full_path_tar = '{0}.tar.gz'.format(self.test_product_full_path)
        self.test_cksum_prod_filename = 'product_name.tar.gz'
        self.test_cksum_filename = 'product_name.md5'
        self.test_cksum_full_path = '/destination_directory/{0}'.format(self.test_cksum_filename)
        # This is meant to match with the output set by mock_execute_cmd
        self.test_cksum_value = 'cmd {0}'.format(self.test_cksum_prod_filename)

    def tearDown(self):
        pass

    @patch('processing.staging.EspaLogging.get_logger')
    @patch('processing.staging.utilities.execute_cmd')
    @patch('processing.staging.retrieve_pigz_cfg')
    def test_untar_data(self, mock_pigz_cfg, mock_execute_cmd, mock_logger):

        pigz_str = '1'
        destination = '/destination'
        mock_pigz_cfg.return_value = pigz_str
        mock_execute_cmd.return_value = 'cmd output'

        cmd = ' '.join(['unpigz -p ', pigz_str, ' < ', self.test_product_full_path_tar,
                        ' | tar', '--directory', destination,
                        ' -xv'])

        staging.untar_data(source_file=self.test_product_full_path_tar,
                           destination_directory=destination)

        mock_execute_cmd.assert_called_once_with(cmd)
