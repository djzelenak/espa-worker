
import sys
import copy
import unittest
import logging
from mock import patch, mock_open, call
from mocks import mock_api_response

from processing import config, distribution
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

class TestDistribution(unittest.TestCase):
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

    @patch('processing.distribution.EspaLogging.get_logger')
    @patch('processing.distribution.utilities.create_directory')
    @patch('processing.distribution.utilities.execute_cmd')
    @patch('processing.distribution.utilities.tar_files')
    @patch('processing.distribution.os.chdir')
    @patch('processing.distribution.os.chmod')
    @patch('__builtin__.open', new=mock_open(read_data='data'), create=False)
    def test_package_product(self, mock_os_chmod, mock_os_chdir,
                             mock_tar_files, mock_execute_cmd,
                             mock_create_directory, mock_logger):
        """
        Make sure we call package_product correctly
        """
        mock_execute_cmd.return_value = 'cmd output'
        mock_create_directory.return_value = None
        mock_tar_files.return_value = self.test_product_full_path_tar
        mock_os_chdir.return_value = None
        mock_os_chmod.return_value = None

        product_full_path, cksum_full_path, cksum_value = \
            distribution.package_product(True, '/source_directory', '/destination_directory', 'product_name')

        self.assertTrue(product_full_path == self.test_product_full_path_tar and
                        cksum_full_path == self.test_cksum_full_path and
                        cksum_value == self.test_cksum_value)

    @patch('processing.distribution.EspaLogging.get_logger')
    @patch('processing.distribution.utilities.execute_cmd')
    @patch('processing.distribution.transfer.transfer_file')
    def test_transfer_product(self, mock_transfer_file, mock_execute_cmd, mock_logger):
        """
        Test that the transfer_product function is called and behaves as expected
        TODO: assert_called_with for mock_transfer_file and mock_execute_cmd ?
        """
        mock_execute_cmd.return_value = 'cmd output'
        mock_transfer_file.return_value = None

        (cksum_value, destination_product_file, destination_cksum_file) = \
            distribution.transfer_product(immutability=True,
                                          destination_host='http://1.2.3.4',
                                          destination_directory='/destination_directory',
                                          destination_username='bilbo',
                                          destination_pw='frodo',
                                          product_filename='product_name.tar.gz',
                                          cksum_filename='product_name.md5')

        self.assertTrue(cksum_value == 'cmd output' and
                        destination_product_file == self.test_product_full_path_tar and
                        destination_cksum_file == self.test_cksum_full_path)

    @patch('processing.distribution.EspaLogging.get_logger')
    @patch('processing.distribution.package_product')
    @patch('processing.distribution.utilities.execute_cmd')
    def test_distribute_product_local(self, mock_execute_cmd, mock_package_product, mock_logger):
        """
        Make sure the local product distribution is functioning as expected given certain inputs
        """
        mock_package_product.return_value = (self.test_product_full_path_tar,
                                             self.test_cksum_full_path,
                                             self.test_cksum_value)
        mock_execute_cmd.return_value = 'cmd output'

        (product_file, cksum_file) = distribution.distribute_product_local(True,
                                                                           'product_name',
                                                                           '/source_path',
                                                                           '/packaging_path')

        self.assertTrue(product_file == self.test_product_full_path_tar and
                        cksum_file == self.test_cksum_full_path)

    @patch('processing.distribution.EspaLogging.get_logger')
    @patch('processing.distribution.Environment')
    @patch('processing.distribution.utilities.get_cache_hostname')
    @patch('processing.distribution.package_product')
    @patch('processing.distribution.transfer_product')
    def test_distribute_product_remote(self, mock_transfer_product, mock_package_product,
                                       mock_get_cache_hostname, MockEnvironment,
                                       mock_logger):
        """
        Make sure the remote product distribution is functioning as expected given certain inputs
        """
        params = copy.deepcopy(self.params)
        params['options']['destination_pw'] = 'destination_pw'
        params['options']['destination_username'] = 'destination_username'
        env = MockEnvironment()
        env.get_cache_host_list.return_value = ['host_1', 'host_2']
        mock_get_cache_hostname.return_value = 'hostname'
        mock_package_product.return_value = (self.test_product_full_path_tar,
                                             self.test_cksum_full_path,
                                             self.test_cksum_value)
        mock_transfer_product.return_value = (self.test_cksum_value,
                                              self.test_product_full_path_tar,
                                              self.test_cksum_full_path)

        (product_file, cksum_file) = distribution.distribute_product_remote(True,
                                                                            'product_name',
                                                                            '/source_path',
                                                                            '/packaging_path',
                                                                            '/cache_path',
                                                                            params)

        self.assertTrue(product_file == self.test_product_full_path_tar and
                        cksum_file == self.test_cksum_full_path)

    @patch('processing.distribution.EspaLogging.get_logger')
    @patch('processing.distribution.os.chdir')
    @patch('processing.distribution.utilities.execute_cmd')
    @patch('processing.distribution.transfer.transfer_file')
    def test_distribute_statistics_remote(self, mock_transfer_file, mock_execute_cmd, mock_chdir, mock_logger):
        """
        Make sure that distribute_statistics_remote runs as expected
        """
        mock_chdir.return_value = None
        mock_execute_cmd.return_value = 'cmd output'
        mock_transfer_file.return_value = None

        distribution.distribute_statistics_remote(immutability=True,
                                                  product_id='product_id',
                                                  source_path='/source',
                                                  destination_host='hostname',
                                                  destination_path='/destination',
                                                  destination_username='bilbo',
                                                  destination_pw='password')

        mock_transfer_file.assert_called_once_with('localhost', 'stats/product_id*', 'hostname',
                                                   '/destination/stats',
                                                   destination_pw='password',
                                                   destination_username='bilbo')

    @patch('processing.distribution.EspaLogging.get_logger')
    @patch('processing.distribution.os.chdir')
    @patch('processing.distribution.utilities.create_directory')
    @patch('processing.distribution.utilities.execute_cmd')
    @patch('processing.distribution.glob.glob')
    @patch('processing.distribution.shutil.copyfile')
    def test_distribute_statistics_local(self, mock_copyfile, mock_glob, mock_execute_cmd,
                                         mock_create_directory, mock_chdir, mock_logger):
        """
        Make sure that distribute_statistics_local runs as expected
        """
        mock_chdir.return_value = None
        mock_create_directory.return_value = None
        mock_execute_cmd.return_value = 'cmd output'
        mock_copyfile.return_value = None
        mock_glob.return_value = ['stats/band_1.csv', 'stats/band_2.csv', 'stats/band_3.csv']

        distribution.distribute_statistics_local(immutability=True,
                                                 product_id='product_id',
                                                 source_path='/source',
                                                 destination_path='/destination')
        calls = [call('stats/band_1.csv', '/destination/stats/band_1.csv'),
                 call('stats/band_2.csv', '/destination/stats/band_2.csv'),
                 call('stats/band_3.csv', '/destination/stats/band_3.csv')]

        mock_copyfile.assert_has_calls(calls, any_order=True)