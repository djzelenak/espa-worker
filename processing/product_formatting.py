
"""
Description: Alters product extents, projections and pixel sizes.

License: NASA Open Source Agreement 1.3
"""

import os
import glob


import settings
import utilities
from logging_tools import EspaLogging


def reformat(metadata_filename, work_directory, input_format, output_format):
    """
    Description:
      Re-format the bands to the specified format using our raw binary tools
      or gdal, whichever is appropriate for the task.

      Input espa:
          Output Formats: envi(espa), gtiff, and hdf
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    # Don't do anything if they match
    if input_format == output_format:
        return

    # Change to the working directory
    current_directory = os.getcwd()
    os.chdir(work_directory)

    try:
        # Convert from our internal ESPA/ENVI format to GeoTIFF
        if input_format == 'envi' and output_format == 'gtiff':
            gtiff_name = metadata_filename.rstrip('.xml')
            # Call with deletion of source files
            cmd = ' '.join(['convert_espa_to_gtif', '--del_src_files',
                            '--xml', metadata_filename,
                            '--gtif', gtiff_name])

            output = ''
            try:
                output = utilities.execute_cmd(cmd)

                # Rename the XML file back to *.xml from *_gtif.xml
                meta_gtiff_name = metadata_filename.split('.xml')[0]
                meta_gtiff_name = ''.join([meta_gtiff_name, '_gtif.xml'])

                os.rename(meta_gtiff_name, metadata_filename)
            finally:
                if len(output) > 0:
                    logger.info(output)

            # Remove all *.tfw files that are likely present
            files_to_remove = glob.glob('*.tfw')
            if len(files_to_remove) > 0:
                cmd = ' '.join(['rm', '-f'] + files_to_remove)
                logger.info(' '.join(['REMOVING TFW DATA COMMAND:', cmd]))

                output = ''
                try:
                    output = utilities.execute_cmd(cmd)
                finally:
                    if len(output) > 0:
                        logger.info(output)

        # Convert from our internal ESPA/ENVI format to HDF
        elif input_format == 'envi' and output_format == 'hdf-eos2':
            # convert_espa_to_hdf
            hdf_name = metadata_filename.replace('.xml', '.hdf')
            # Call with deletion of source files
            cmd = ' '.join(['convert_espa_to_hdf', '--del_src_files',
                            '--xml', metadata_filename,
                            '--hdf', hdf_name])

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
                # Rename the XML file back to *.xml from *_hdf.xml
                meta_name = metadata_filename.replace('.xml', '_hdf.xml')
                os.rename(meta_name, metadata_filename)
                # Remove .hdf.hdr file - it will likely be there if all of the
                # bands in the HDF have the same resolution
                files_to_remove = glob.glob('*.hdf.hdr')
                if len(files_to_remove) > 0:
                    cmd = ' '.join(['rm', '-f'] + files_to_remove)
                    logger.info(' '.join(['REMOVING HDF.HDR COMMAND:', cmd]))
                    output = ''
                    try:
                        output = utilities.execute_cmd(cmd)
                    finally:
                        if len(output) > 0:
                            logger.info(output)
            finally:
                if len(output) > 0:
                    logger.info(output)

        # Convert from our internal ESPA/ENVI format to NetCDF
        elif input_format == 'envi' and output_format == 'netcdf':
            # convert_espa_to_netcdf
            netcdf_name = metadata_filename.replace('.xml', '.nc')
            # Call with deletion of source files
            cmd = ' '.join(['convert_espa_to_netcdf',
                            '--del_src_files',
                            '--xml', metadata_filename,
                            '--netcdf', netcdf_name])

            output = ''
            try:
                output = utilities.execute_cmd(cmd)

                # Rename the XML file back to *.xml from *_nc.xml
                meta_name = metadata_filename.replace('.xml', '_nc.xml')

                os.rename(meta_name, metadata_filename)
            finally:
                if len(output) > 0:
                    logger.info(output)

        # Requested conversion not implemented
        else:
            raise ValueError("Unsupported reformat combination (%s, %s)"
                             % (input_format, output_format))

    finally:
        # Change back to the previous directory
        os.chdir(current_directory)
