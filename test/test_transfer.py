
import sys
import copy
import unittest
import logging
from mock import patch, mock_open, call
from mocks import mock_api_response

from processing import config, transfer
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

class TestTransfer(unittest.TestCase):
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

    @patch('processing.transfer.EspaLogging.get_logger')
    @patch('processing.transfer.shutil.copyfile')
    def test_transfer_file_copy(self, mock_copyfile, mock_logger):
        mock_copyfile.return_value = None

        transfer.transfer_file(source_host='localhost',
                               source_file='/source/file.tar.gz',
                               destination_host='localhost',
                               destination_file='/dest/file.tar.gz',
                               source_username='bilbo',
                               source_pw='pw',
                               destination_username='bilbo',
                               destination_pw='pw')

        mock_copyfile.assert_called_once_with('/source/file.tar.gz', '/dest/file.tar.gz')

    @patch('processing.transfer.EspaLogging.get_logger')
    @patch('processing.transfer.remote_copy_file_to_file')
    def test_transfer_file_remote_copy(self, mock_file_to_file, mock_logger):
        mock_file_to_file.return_value = None

        transfer.transfer_file(source_host='host_1',
                               source_file='/source/file.tar.gz',
                               destination_host='host_1',
                               destination_file='/dest/file.tar.gz',
                               source_username='bilbo',
                               source_pw='pw',
                               destination_username='bilbo',
                               destination_pw='pw')

        mock_file_to_file.assert_called_once_with('host_1', '/source/file.tar.gz', '/dest/file.tar.gz')

    @patch('processing.transfer.EspaLogging.get_logger')
    @patch('processing.transfer.ftp_from_remote_location')
    def test_ftp_from_remote_location(self, mock_ftp_from_remote_location, mock_logger):
        mock_ftp_from_remote_location.return_value = None

        transfer.transfer_file(source_host='host_1',
                               source_file='/source/file.tar.gz',
                               destination_host='host_2',
                               destination_file='/dest/file.tar.gz',
                               source_username='bilbo',
                               source_pw='pw',
                               destination_username=None,
                               destination_pw=None)

        mock_ftp_from_remote_location.assert_called_once_with('bilbo', 'pw', 'host_1',
                                                              '/source/file.tar.gz', '/dest/file.tar.gz')

    @patch('processing.transfer.EspaLogging.get_logger')
    @patch('processing.transfer.ftp_to_remote_location')
    def test_ftp_to_remote_location(self, mock_ftp_to_remote_location, mock_logger):
        mock_ftp_to_remote_location.return_value = None

        transfer.transfer_file(source_host='host_1',
                               source_file='/source/file.tar.gz',
                               destination_host='host_2',
                               destination_file='/dest/file.tar.gz',
                               source_username=None,
                               source_pw=None,
                               destination_username='bilbo',
                               destination_pw='pw')

        mock_ftp_to_remote_location.assert_called_once_with('bilbo', 'pw', '/source/file.tar.gz',
                                                            'host_2', '/dest/file.tar.gz')

