
import unittest
from mock import patch
from processing import product_formatting


class TestFormatting(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch('processing.product_formatting.EspaLogging.get_logger')
    @patch('processing.product_formatting.utilities.execute_cmd')
    @patch('processing.product_formatting.os.rename', lambda x, y: None)
    @patch('processing.product_formatting.os.chdir', lambda x: None)
    @patch('processing.product_formatting.glob.glob', lambda x: [])
    def test_reformat_gtiff(self, mock_execute_cmd, mock_logger):
        mock_execute_cmd.return_value = 'cmd output'

        work_dir = '/work_dir'
        xml_filename = 'LC08_L1TP_128058_20160608_20170324_01_T1.xml'
        base_name = xml_filename.rstrip('.xml')

        cmd = ' '.join(['convert_espa_to_gtif', '--del_src_files',
                        '--xml', xml_filename,
                        '--gtif', base_name])

        product_formatting.reformat(metadata_filename=xml_filename,
                                    work_directory=work_dir,
                                    input_format='envi',
                                    output_format='gtiff')

        mock_execute_cmd.assert_called_with(cmd)

    @patch('processing.product_formatting.EspaLogging.get_logger')
    @patch('processing.product_formatting.utilities.execute_cmd')
    @patch('processing.product_formatting.os.rename', lambda x, y: None)
    @patch('processing.product_formatting.os.chdir', lambda x: None)
    @patch('processing.product_formatting.glob.glob', lambda x: [])
    def test_reformat_netcdf(self, mock_execute_cmd, mock_logger):
        mock_execute_cmd.return_value = 'cmd output'
        work_dir = '/work_dir'
        xml_filename = 'LC08_L1TP_128058_20160608_20170324_01_T1.xml'
        base_name = xml_filename.replace('.xml', '.nc')

        cmd = ' '.join(['convert_espa_to_netcdf', '--del_src_files',
                        '--xml', xml_filename,
                        '--netcdf', base_name])

        product_formatting.reformat(metadata_filename=xml_filename,
                                    work_directory=work_dir,
                                    input_format='envi',
                                    output_format='netcdf')

        mock_execute_cmd.assert_called_with(cmd)

    @patch('processing.product_formatting.EspaLogging.get_logger')
    @patch('processing.product_formatting.utilities.execute_cmd')
    @patch('processing.product_formatting.os.rename', lambda x, y: None)
    @patch('processing.product_formatting.os.chdir', lambda x: None)
    @patch('processing.product_formatting.glob.glob', lambda x: [])
    def test_reformat_hdf(self, mock_execute_cmd, mock_logger):

        mock_execute_cmd.return_value = 'cmd output'

        work_dir = '/work_dir'
        xml_filename = 'LC08_L1TP_128058_20160608_20170324_01_T1.xml'
        base_name = xml_filename.replace('.xml', '.hdf')

        cmd = ' '.join(['convert_espa_to_hdf', '--del_src_files',
                        '--xml', xml_filename,
                        '--hdf', base_name])

        product_formatting.reformat(metadata_filename=xml_filename,
                                    work_directory=work_dir,
                                    input_format='envi',
                                    output_format='hdf-eos2')

        mock_execute_cmd.assert_called_with(cmd)

    @patch('processing.product_formatting.EspaLogging.get_logger')
    @patch('processing.product_formatting.utilities.execute_cmd')
    def test_no_reformat(self, mock_execute_cmd, mock_logger):
        mock_execute_cmd.return_value = 'cmd output'

        work_dir = '/work_dir'
        xml_filename = 'LC08_L1TP_128058_20160608_20170324_01_T1.xml'

        product_formatting.reformat(metadata_filename=xml_filename,
                                    work_directory=work_dir,
                                    input_format='envi',
                                    output_format='envi')

        mock_execute_cmd.assert_not_called()

    @patch('processing.product_formatting.EspaLogging.get_logger')
    @patch('processing.product_formatting.utilities.execute_cmd', lambda x: None)
    @patch('processing.product_formatting.os.rename', lambda x, y: None)
    @patch('processing.product_formatting.os.chdir', lambda x: None)
    @patch('processing.product_formatting.glob.glob', lambda x: x)
    def test_invalid_reformat(self, mock_logger):
        work_dir = '/work_dir'
        xml_filename = 'LC08_L1TP_128058_20160608_20170324_01_T1.xml'
        with self.assertRaises(ValueError):
            product_formatting.reformat(metadata_filename=xml_filename,
                                        work_directory=work_dir,
                                        input_format='gtiff',
                                        output_format='envi')
