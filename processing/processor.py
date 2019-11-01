'''
Description: Implements the processors which generate the products the system
             is capable of producing.

License: NASA Open Source Agreement 1.3
'''

import os
import shutil
import glob
import json
import datetime
import copy
import subprocess
from collections import namedtuple
import re

from espa import Metadata

import settings
import utilities
from logging_tools import EspaLogging
import sensor
import initialization
import parameters
import landsat_metadata
import staging
import transfer
import distribution
import product_formatting
from espa_exception import ESPAException


class ProductProcessor(object):
    """Provides the super class for all product request processing

    It performs the tasks needed by all processors.

    It initializes the logger object and keeps it around for all the
    child-classes to use.

    It implements initialization of the order and product directory
    structures.

    It also implements the cleanup of the product directory.
    """

    def __init__(self, cfg, parms):
        """Initialization for the object.
        """

        self._logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

        # Some minor enforcement for what parms should be
        if isinstance(parms, dict):
            self._parms = parms
            self._logger.debug('PARMS: {0}'.format(self._parms))
        else:
            raise ESPAException('Input parameters was of type [{}],'
                            ' where dict is required'.format(type(parms)))

        self._cfg = cfg

        # Log the distribution method that will be used
        self._logger.info('Using distribution method [{}]'.
                          format(self._cfg.get('espa_distribution_method')))

        # Establish the product owner
        self._user = self._cfg.get('espa_user')
        self._group = self._cfg.get('espa_group')

        # Validate the parameters
        self.validate_parameters()

        # Initialize these, which are set by other methods
        self._product_name = None
        self._product_dir = None
        self._stage_dir = None
        self._work_dir = None
        self._output_dir = None

        # Ship resource report
        self._include_resource_report = self._cfg.get('include_resource_report')

    def validate_parameters(self):
        """Validates the parameters required for the processor
        """

        # Test for presence of required top-level parameters
        keys = ['orderid', 'scene', 'product_type', 'options']
        for key in keys:
            if not parameters.test_for_parameter(self._parms, key):
                raise RuntimeError('Missing required input parameter [{}]'
                                   .format(key))

        # Set the download URL to None if not provided
        if not parameters.test_for_parameter(self._parms, 'download_url'):
            self._parms['download_url'] = None

        # TODO - Remove this once we have converted
        if not parameters.test_for_parameter(self._parms, 'product_id'):
            self._logger.warning('[product_id] parameter missing defaulting'
                                 ' to [scene]')
            self._parms['product_id'] = self._parms['scene']

        # Make sure the bridge mode parameter is defined
        if not parameters.test_for_parameter(self._parms, 'bridge_mode'):
            self._parms['bridge_mode'] = False

        # Validate the options
        options = self._parms['options']

        # Default these so they are not kept, they should only be present and
        # turned on for developers
        if not parameters.test_for_parameter(options, 'keep_directory'):
            options['keep_directory'] = False
        if not parameters.test_for_parameter(options,
                                             'keep_intermediate_data'):
            options['keep_intermediate_data'] = False

        # Verify or set the destination information
        if not parameters.test_for_parameter(options, 'destination_username'):
            options['destination_username'] = 'localhost'

        if not parameters.test_for_parameter(options, 'destination_pw'):
            options['destination_pw'] = 'localhost'

    def log_order_parameters(self):
        """Log the order parameters in json format
        """

        # Override the usernames and passwords for logging
        parms = copy.deepcopy(self._parms)
        parms['options']['source_username'] = 'XXXXXXX'
        parms['options']['destination_username'] = 'XXXXXXX'
        parms['options']['source_pw'] = 'XXXXXXX'
        parms['options']['destination_pw'] = 'XXXXXXX'

        self._logger.info('MAPPER OPTION LINE {}'
                          .format(json.dumps(parms, sort_keys=True)))

        del parms

    def snapshot_resources(self):
        """ Delivers (to logger) a current resource snapshot in JSON format
        """

        # Likely to be turned off duing operations
        if not self._include_resource_report:
            return

        resources = dict(current_workdir_size=utilities.current_disk_usage(self._work_dir),
                         peak_memory_usage=utilities.peak_memory_usage(),
                         entity={k: self._parms.get(k) for k in ('scene', 'orderid')})
        self._logger.info('*** RESOURCE SNAPSHOT {} ***'
                          .format(json.dumps(resources, sort_keys=True)))

    def initialize_processing_directory(self):
        """Initializes the processing directory

        Creates the following directories.

           .../output
           .../stage
           .../work

        Note:
            order_id and product_id along with the espa_work_dir processing
            configuration provide the path to the processing locations.
        """

        product_id = self._parms['product_id']
        order_id = self._parms['orderid']

        # Get the absolute path to the directory, and default to the current one
        base_work_dir = self.check_work_dir(self._cfg.get('espa_work_dir'))

        # Create the product directory name
        product_dirname = '-'.join([str(order_id), str(product_id)])

        # Add the product directory name to the path
        self._product_dir = os.path.join(base_work_dir, product_dirname)

        # Just incase remove it, and we don't care about errors if it
        # doesn't exist (probably only needed for developer runs)
        shutil.rmtree(self._product_dir, ignore_errors=True)

        # Create each of the sub-directories
        self._stage_dir = initialization.create_stage_directory(self._product_dir)
        self._logger.info('Created directory [{}]'.format(self._stage_dir))

        self._work_dir = initialization.create_work_directory(self._product_dir)
        self._logger.info('Created directory [{}]'.format(self._work_dir))

        # Will return the espa_distribution_dir if distribution_method is local
        self._output_dir = initialization.create_output_directory(self._product_dir)

    def remove_product_directory(self):
        """Remove the product directory
        """

        options = self._parms['options']

        # We don't care about this failing, we just want to attempt to free
        # disk space to be nice to the whole system.  If this processing
        # request failed due to a processing issue.  Otherwise, with
        # successfull processing, hadoop cleans up after itself.
        if self._product_dir is not None and not options['keep_directory']:
            shutil.rmtree(self._product_dir, ignore_errors=True)

    def get_product_name(self):
        """Build the product name from the product information and current
           time

        Note:
            Not implemented here.
        """

        raise NotImplementedError('[{}] Requires implementation in the child'
                                  ' class'.format(self.get_product_name
                                                  .__name__))

    def distribute_product(self):
        """Does both the packaging and distribution of the product using
           the distribution module
        """

        product_name = self.get_product_name()

        # Deliver the product files
        product_file = 'ERROR'
        cksum_file = 'ERROR'
        try:
            immutability = utilities.str2bool(self._cfg.get('immutable_distribution'))

            (product_file, cksum_file) = \
                distribution.distribute_product(immutability=immutability,
                                                product_name=product_name,
                                                source_path=self._work_dir,
                                                packaging_path=self._output_dir,
                                                parms=self._parms,
                                                user=self._user,
                                                group=self._group)
        except (Exception, ESPAException):
            msg = 'An Exception occurred delivering the product'
            self._logger.exception(msg)
            raise ESPAException(msg)

        self._logger.info('*** Product Delivery Complete ***')

        # Let the caller know where we put these on the destination system
        return (product_file, cksum_file)

    def process_product(self):
        """Perform the processor specific processing to generate the
           requested product

        Note:
            Not implemented here.

        Note:
            Must return the destination product and cksum file names.
        """

        raise NotImplementedError('[{}] Requires implementation in the child'
                                  ' class'.format(self.process_product
                                                  .__name__))

    def process(self):
        """Generates a product through a defined process

        This method must cleanup everything it creates by calling the
        remove_product_directory() method.

        Note:
            Must return the destination product and cksum file names.
        """

        # Logs the order parameters that can be passed to the mapper for this
        # processor
        self.log_order_parameters()

        # Initialize the processing directory.
        self.initialize_processing_directory()

        try:
            (destination_product_file, destination_cksum_file) = \
                self.process_product()

        finally:
            # Remove the product directory
            # Free disk space to be nice to the whole system.
            self.remove_product_directory()

        return (destination_product_file, destination_cksum_file)

    def check_work_dir(self, path):
        """
        Make sure that the base work dir exists, if not, set it to something safe
        Args:
            path (str): The full path to a base working directory
        Returns:
            str
        """
        fallback = '/home/espa'

        if not os.path.exists(path) or path == '':
            path = os.path.abspath(fallback)
            self._logger.warning('Processing work directory not found, trying {}'.format(path))

        if not os.path.exists(path):
            path = os.getcwd()
            self._logger.warning('Fallback working directory option is not valid, setting to {}'.format(path))
            return path
        else:
            # Path as it was given is OK..get the absolute path
            path = os.path.abspath(path)
            self._logger.info('Working directory is set to {}'.format(path))
            return path


class CustomizationProcessor(ProductProcessor):
    """Provides the super class implementation for customization processing

    Allows for warping the products to the user requested projection.
    """

    def __init__(self, cfg, parms):

        self._build_products = False

        super(CustomizationProcessor, self).__init__(cfg, parms)

    def validate_parameters(self):
        """Validates the parameters required for the processor
        """

        # Call the base class parameter validation
        super(CustomizationProcessor, self).validate_parameters()

        product_id = self._parms['product_id']
        options = self._parms['options']

        self._logger.info('Validating [CustomizationProcessor] parameters')

        parameters.validate_reprojection_parameters(options, product_id)

        # Update the xml filename to be correct
        self._xml_filename = '.'.join([product_id, 'xml'])

    def build_reprojection_cmd_line(self, options):
        """Converts the options to command line arguments for reprojection
        """

        cmd = ['espa_reprojection.py', '--xml', self._xml_filename]

        # The target_projection is used as the sub-command to the executable
        if not options['reproject']:
            # none is used if no reprojection will be performed
            cmd.append('none')
        else:
            cmd.append(options['target_projection'])

        if options['target_projection'] == 'utm':
            cmd.extend(['--zone', options['utm_zone']])
            cmd.extend(['--north-south', options['utm_north_south']])
        elif options['target_projection'] == 'aea':
            cmd.extend(['--datum', options['datum']])
            cmd.extend(['--central-meridian', options['central_meridian']])
            cmd.extend(['--origin-latitude', options['origin_lat']])
            cmd.extend(['--std-parallel-1', options['std_parallel_1']])
            cmd.extend(['--std-parallel-2', options['std_parallel_2']])
            cmd.extend(['--false-easting', options['false_easting']])
            cmd.extend(['--false-northing', options['false_northing']])
        elif options['target_projection'] == 'ps':
            cmd.extend(['--latitude-true-scale', options['latitude_true_scale']])
            cmd.extend(['--longitude-pole', options['longitude_pole']])
            cmd.extend(['--origin-latitude', options['origin_lat']])
            cmd.extend(['--false-easting', options['false_easting']])
            cmd.extend(['--false-northing', options['false_northing']])
        elif options['target_projection'] == 'sinu':
            cmd.extend(['--central-meridian', options['central_meridian']])
            cmd.extend(['--false-easting', options['false_easting']])
            cmd.extend(['--false-northing', options['false_northing']])
        # Nothing needed for lonlat or none

        if options['resample_method']:
            cmd.extend(['--resample-method', options['resample_method']])
        else:
            cmd.extend(['--resample-method', 'near'])

        if options['resize'] or options['reproject'] or options['image_extents']:
            cmd.extend(['--pixel-size', options['pixel_size']])
            cmd.extend(['--pixel-size-units', options['pixel_size_units']])

        if options['image_extents']:
            cmd.extend(['--extent-minx', options['minx']])
            cmd.extend(['--extent-maxx', options['maxx']])
            cmd.extend(['--extent-miny', options['miny']])
            cmd.extend(['--extent-maxy', options['maxy']])
            cmd.extend(['--extent-units', options['image_extents_units']])

        # Always envi for ESPA reprojection processing
        # The provided output format is used later
        cmd.extend(['--output-format', 'envi'])

        return map(str, cmd)

    def customize_products(self):
        """Performs the customization of the products
        """

        # Nothing to do if the user did not specify anything to build
        if not self._build_products:
            return

        product_id = self._parms['product_id']
        options = self._parms['options']

        # Reproject the data for each product, but only if necessary
        if (options['reproject'] or
                options['resize'] or
                options['image_extents'] or
                options['projection'] is not None):

            # Change to the working directory
            current_directory = os.getcwd()
            os.chdir(self._work_dir)

            try:
                cmd = self.build_reprojection_cmd_line(options)
                output = ''
                try:
                    output = subprocess.check_output(cmd)
                except subprocess.CalledProcessError as error:
                    self._logger.info(error.output)
                    msg = 'An exception occurred during product customization'
                    self._logger.exception(msg)
                    raise ESPAException(msg)
                if len(output) > 0:
                    self._logger.info(output)

            finally:
                # Change back to the previous directory
                os.chdir(current_directory)


class CDRProcessor(CustomizationProcessor):
    """Provides the super class implementation for generating CDR products
    """

    def __init__(self, cfg, parms):
        super(CDRProcessor, self).__init__(cfg, parms)

    def validate_parameters(self):
        """Validates the parameters required for all processors
        """

        # Call the base class parameter validation
        super(CDRProcessor, self).validate_parameters()

    def stage_input_data(self):
        """Stages the input data required for the processor

        Not implemented here.
        """

        msg = ('[%s] Requires implementation in the child class'
               % self.stage_input_data.__name__)
        raise NotImplementedError(msg)

    def build_science_products(self):
        """Build the science products requested by the user

        Not implemented here.
        """

        raise NotImplementedError('[{}] Requires implementation in the child'
                                  ' class'.format(self.build_science_products
                                                  .__name__))

    def cleanup_work_dir(self):
        """Cleanup all the intermediate non-products and the science
           products not requested

        Not implemented here.
        """

        raise NotImplementedError('[{}] Requires implementation in the child'
                                  ' class'.format(self.cleanup_work_dir
                                                  .__name__))

    def remove_band_from_xml(self, band):
        """Remove the band from disk and from the XML
        Hint: This is just for files in the ESPA native envi format
        """

        img_filename = str(band.file_name)
        hdr_filename = img_filename.replace('.img', '.hdr')

        # Remove the files
        if os.path.exists(img_filename):
            os.unlink(img_filename)
        if os.path.exists(hdr_filename):
            os.unlink(hdr_filename)

        # Remove the element
        parent = band.getparent()
        parent.remove(band)

    def remove_products_from_xml(self):
        """Remove the specified products from the XML file

        The file is read into memory, processed, and written back out with out
        the specified products.
        """
        raise NotImplementedError('[{}] Requires implementation in the child'
                                  ' class'.format(self.remove_products_from_xml
                                                  .__name__))

    def generate_statistics(self):
        """Generates statistics if required for the processor

        Not implemented here.
        """

        raise NotImplementedError('[{}] Requires implementation in the child'
                                  ' class'.format(self.generate_statistics
                                                  .__name__))

    def distribute_statistics(self):
        """Distributes statistics if required for the processor
        """

        options = self._parms['options']

        if options['include_statistics']:
            try:
                immutability = utilities.str2bool(self._cfg.get('immutable_distribution'))

                distribution.distribute_statistics(immutability,
                                                   self._work_dir,
                                                   self._output_dir,
                                                   self._parms,
                                                   self._user,
                                                   self._group)
            except (Exception, ESPAException):
                msg = 'An exception occurred delivering the stats'
                self._logger.exception(msg)
                raise ESPAException(msg)

            self._logger.info('*** Statistics Distribution Complete ***')

    def reformat_products(self):
        """Reformat the customized products if required for the processor
        """

        # Nothing to do if the user did not specify anything to build
        if not self._build_products:
            return

        options = self._parms['options']

        # Convert to the user requested output format or leave it in ESPA ENVI
        # We do all of our processing using ESPA ENVI format so it can be
        # hard-coded here
        product_formatting.reformat(self._xml_filename, self._work_dir,
                                    'envi', options['output_format'])

    def process_product(self):
        """Perform the processor specific processing to generate the
           requested product
        """

        # Stage the required input data
        self.stage_input_data()

        # Build science products
        self.build_science_products()

        # [[ Science-Resource Snapshot ]]
        self.snapshot_resources()

        # Remove science products and intermediate data not requested
        self.cleanup_work_dir()

        # Customize products
        self.customize_products()

        # Generate statistics products
        self.generate_statistics()

        # Distribute statistics
        self.distribute_statistics()

        # Reformat product
        self.reformat_products()

        # Package and deliver product
        (destination_product_file, destination_cksum_file) = \
            self.distribute_product()

        # [[ Formatting-Resource Snapshot ]]
        self.snapshot_resources()

        return (destination_product_file, destination_cksum_file)


class LandsatProcessor(CDRProcessor):
    """Implements the common processing between all of the Landsat
       processors
    """

    def __init__(self, cfg, parms):
        super(LandsatProcessor, self).__init__(cfg, parms)

        product_id = self._parms['product_id']

        self._metadata_filename = None

    def validate_parameters(self):
        """Validates the parameters required for the processor
        """

        # Call the base class parameter validation
        super(LandsatProcessor, self).validate_parameters()

        self._logger.info('Validating [LandsatProcessor] parameters')

        options = self._parms['options']

        # Force these parameters to false if not provided
        # They are the required includes for product generation
        required_includes = ['include_pixel_qa',
                             'include_customized_source_data',
                             'include_dswe',
                             'include_st',
                             'include_orca',
                             'include_source_data',
                             'include_sr',
                             'include_sr_evi',
                             'include_sr_msavi',
                             'include_sr_nbr',
                             'include_sr_nbr2',
                             'include_sr_ndmi',
                             'include_sr_ndvi',
                             'include_sr_savi',
                             'include_sr_thermal',
                             'include_sr_toa',
                             'include_statistics']

        for parameter in required_includes:
            if not parameters.test_for_parameter(options, parameter):
                self._logger.warning('[{}] parameter missing defaulting to'
                                     ' False'.format(parameter))
                options[parameter] = False

        # Determine if we need to build products
        if (not options['include_customized_source_data'] and
                not options['include_sr'] and
                not options['include_sr_toa'] and
                not options['include_sr_thermal'] and
                not options['include_pixel_qa'] and
                not options['include_sr_nbr'] and
                not options['include_sr_nbr2'] and
                not options['include_sr_ndvi'] and
                not options['include_sr_ndmi'] and
                not options['include_sr_savi'] and
                not options['include_sr_msavi'] and
                not options['include_sr_evi'] and
                not options['include_dswe'] and
                not options['include_st'] and
                not options['include_orca']):

            self._logger.info('***NO SCIENCE PRODUCTS CHOSEN***')
            self._build_products = False
        else:
            self._build_products = True

        # Always generate TOA and BT (for cfmask_based_water_detection)
        # Also, generate SR input if needed, but do not deliver it in output
        self.requires_sr_input = any(
            options[x] for x in [
                'include_sr',
                'include_sr_nbr',
                'include_sr_nbr2',
                'include_sr_ndvi',
                'include_sr_ndmi',
                'include_sr_savi',
                'include_sr_msavi',
                'include_sr_evi',
                'include_dswe'
            ])

    def stage_input_data(self):
        """Stages the input data required for the processor
        """

        product_id = self._parms['product_id']
        download_url = self._parms['download_url']

        file_name = ''.join([product_id,
                             settings.LANDSAT_INPUT_FILENAME_EXTENSION])
        staged_file = os.path.join(self._stage_dir, file_name)

        # Download the source data
        transfer.download_file_url(download_url, staged_file)

        # Un-tar the input data to the work directory
        staging.untar_data(staged_file, self._work_dir)
        os.unlink(staged_file)

    def convert_to_raw_binary(self):
        """Converts the Landsat(LPGS) input data to our internal raw binary
           format
        """

        product_id = self._parms['product_id']
        options = self._parms['options']

        # Figure out the metadata filename
        metadata_filename = landsat_metadata.get_filename(self._work_dir,
                                                          product_id)

        # Build a command line arguments list
        cmd = ['convert_lpgs_to_espa',
               '--mtl', metadata_filename]
        if not options['include_source_data']:
            cmd.append('--del_src_files')

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['CONVERT LPGS TO ESPA COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def clip_band_misalignment(self):
        """Clips the bands to matching fill extents
        """

        # Build a command line arguments list
        cmd = ['clip_band_misalignment',
               '--xml', self._xml_filename]

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['CLIP BAND MISALIGNMENT ESPA COMMAND:',
                                    cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def elevation_command_line(self):
        """Returns the command line required to generate the elevation
           product

        Evaluates the options requested by the user to define the command
        line string to use, or returns None indicating nothing todo.

        Note:
            Provides the L4, L5, L7, and L8 command line.
        """

        options = self._parms['options']

        cmd = None
        if options['include_dswe'] or options['include_st']:
            cmd = ['build_elevation_band.py',
                   '--xml', self._xml_filename]

            # Turn the list into a string
            cmd = ' '.join(cmd)

        return cmd

    def generate_elevation_product(self):
        """Generates an elevation product using the metadata from the source
           data
        """

        cmd = self.elevation_command_line()

        # Only if required
        if cmd is not None:

            self._logger.info(' '.join(['ELEVATION COMMAND:', cmd]))

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def generate_pixel_qa(self):
        """Generates the initial pixel QA band from the Level-1 QA band
        """

        cmd = ['generate_pixel_qa',
               '--xml', self._xml_filename]

        # Turn the list into a string
        cmd = ' '.join(cmd)

        self._logger.info(' '.join(['CLASS BASED QA COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def generate_dilated_cloud(self):
        """Adds cloud dilation to the pixel QA band based on original
           cfmask cloud dilation
        """

        cmd = ['dilate_pixel_qa',
               '--xml', self._xml_filename,
               '--bit', '5',
               '--distance', '3']

        # Turn the list into a string
        cmd = ' '.join(cmd)

        self._logger.info(' '.join(['CLOUD DILATION COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def generate_cfmask_water_detection(self):
        """Adds CFmask based water detection to the class based QA band
        """

        cmd = ['cfmask_water_detection',
               '--xml', self._xml_filename]

        # Turn the list into a string
        cmd = ' '.join(cmd)

        self._logger.info(' '.join(['CFMASK WATER DETECTION COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def sr_command_line(self):
        """Returns the command line required to generate surface reflectance

        Evaluates the options requested by the user to define the command
        line string to use, or returns None indicating nothing todo.

        Note:
            Provides the L4, L5, and L7 command line.  L8 processing overrides
            this method.
        """

        options = self._parms['options']

        cmd = ['surface_reflectance.py', '--xml', self._xml_filename]

        if not self.requires_sr_input:
            cmd.extend(['--process_sr', 'False'])

        return ' '.join(cmd)

    def generate_sr_products(self):
        """Generates surface reflectance products
        """

        cmd = self.sr_command_line()

        # Only if required
        if cmd is not None:

            self._logger.info(' '.join(['SURFACE REFLECTANCE COMMAND:', cmd]))

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def orca_command_line(self):
        """Returns command line required to generate over-water reflectance"""
        cmd = ['water_leaving_reflectance.py',
               '--xml',
               self._xml_filename]

        return ' '.join(cmd)

    def generate_over_water_reflectance(self):
        """Generates over-water reflectance products"""
        options = self._parms['options']
        if options['include_orca']:
            cmd = self.orca_command_line()

            self._logger.info(' '.join(['WATER LEAVING REFLECTANCE COMMAND:', cmd]))
            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def generate_spectral_indices(self):
        """Generates the requested spectral indices
        """

        options = self._parms['options']

        cmd = None
        if (options['include_sr_nbr'] or
                options['include_sr_nbr2'] or
                options['include_sr_ndvi'] or
                options['include_sr_ndmi'] or
                options['include_sr_savi'] or
                options['include_sr_msavi'] or
                options['include_sr_evi']):

            cmd = ['spectral_indices.py', '--xml', self._xml_filename]

            # Add the specified index options
            if options['include_sr_nbr']:
                cmd.append('--nbr')
            if options['include_sr_nbr2']:
                cmd.append('--nbr2')
            if options['include_sr_ndvi']:
                cmd.append('--ndvi')
            if options['include_sr_ndmi']:
                cmd.append('--ndmi')
            if options['include_sr_savi']:
                cmd.append('--savi')
            if options['include_sr_msavi']:
                cmd.append('--msavi')
            if options['include_sr_evi']:
                cmd.append('--evi')

            cmd = ' '.join(cmd)

        # Only if required
        if cmd is not None:

            self._logger.info(' '.join(['SPECTRAL INDICES COMMAND:', cmd]))

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def generate_surface_water_extent(self):
        """Generates the Dynamic Surface Water Extent product
        """

        options = self._parms['options']

        if not options['include_dswe']:
            return

        cmd = ['surface_water_extent.py',
               '--xml', self._xml_filename,
               '--verbose']

        cmd = ' '.join(cmd)

        self._logger.info(' '.join(['SURFACE WATER EXTENT COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def generate_surface_temperature(self):
        """Generates the Surface Temperature product
        """

        options = self._parms['options']

        cmd = None
        if options['include_st']:

            if options['st_algorithm'] == "single_channel":
                cmd = ['surface_temperature.py',
                       '--xml', self._xml_filename,
                       '--keep-intermediate-data',
                       '--st_algorithm', options['st_algorithm'],
                       '--reanalysis', options['reanalysis_source']]
            else:  # Split Window
                cmd = ['surface_temperature.py',
                       '--xml', self._xml_filename,
                       '--keep-intermediate-data',
                       '--st_algorithm', options['st_algorithm']]

            cmd = ' '.join(cmd)

        # Only if required
        if cmd is not None:

            self._logger.info(' '.join(['ST COMMAND:', cmd]))

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def build_science_products(self):
        """Build the science products requested by the user
        """

        # Nothing to do if the user did not specify anything to build
        if not self._build_products:
            return

        self._logger.info('[LandsatProcessor] Building Science Products')

        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            self.convert_to_raw_binary()

            self.clip_band_misalignment()

            self.generate_elevation_product()

            self.generate_pixel_qa()

            self.generate_sr_products()

            self.generate_dilated_cloud()

            self.generate_cfmask_water_detection()

            self.generate_spectral_indices()

            self.generate_surface_water_extent()

            self.generate_surface_temperature()

            self.generate_over_water_reflectance()

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)

    def remove_products_from_xml(self):
        """Remove the specified products from the XML file

        The file is read into memory, processed, and written back out without
        the specified products.

        Specific for Landsat products
        """

        # Nothing to do if the user did not specify anything to build
        if not self._build_products:
            return

        options = self._parms['options']

        # Map order options to the products in the XML files
        order2product = {
            'source_data': ['L1T', 'L1G', 'L1TP', 'L1GT', 'L1GS'],
            'include_sr': 'sr_refl',
            'include_sr_toa': 'toa_refl',
            'include_sr_thermal': 'toa_bt',
            'angle_bands': 'angle_bands',
            'keep_intermediate_data': 'intermediate_data'
        }

        # If nothing to do just return
        if self._xml_filename is None:
            return

        # Remove generated products that were not requested
        products_to_remove = []
        if not options['include_customized_source_data']:
            products_to_remove.extend(
                order2product['source_data'])
        if not options['include_sr']:
            products_to_remove.append(
                order2product['include_sr'])
        if not options['include_sr_toa']:
            products_to_remove.append(
                order2product['include_sr_toa'])
            products_to_remove.append(
                order2product['angle_bands'])
        if not options['include_sr_thermal']:
            products_to_remove.append(
                order2product['include_sr_thermal'])
        if not options['keep_intermediate_data']:
            products_to_remove.append(
                order2product['keep_intermediate_data'])

        # Always remove the elevation data
        products_to_remove.append('elevation')

        if products_to_remove is not None:
            # Create and load the metadata object
            espa_metadata = Metadata(xml_filename=self._xml_filename)

            # Search for and remove the items
            for band in espa_metadata.xml_object.bands.band:
                if band.attrib['product'] in products_to_remove:
                    # Business logic to always keep the radsat_qa band if bt,
                    # or toa, or sr output was chosen
                    if (band.attrib['name'] == 'radsat_qa' and
                            (options['include_sr'] or options['include_sr_toa'] or
                             options['include_sr_thermal'])):
                        continue
                    else:
                        self.remove_band_from_xml(band)

            # Validate the XML
            espa_metadata.validate()

            # Write it to the XML file
            espa_metadata.write(xml_filename=self._xml_filename)

            del espa_metadata

    def cleanup_work_dir(self):
        """Cleanup all the intermediate non-products and the science
           products not requested
        """

        product_id = self._parms['product_id']
        options = self._parms['options']

        # Define intermediate files that need to be removed before product
        # tarball generation
        intermediate_files = [
            'lndsr.*.txt',
            'lndcal.*.txt',
            'LogReport*',
            '*_elevation.*'
        ]

        # Define L1 source files that may need to be removed before product
        # tarball generation
        l1_source_files = [
            'L*.TIF',
            'README.GTF',
            '*gap_mask*',
            'L*_GCP.txt',
            'L*_VER.jpg',
            'L*_VER.txt',
        ]

        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            non_products = []
            # Remove the intermediate non-product files
            if not options['keep_intermediate_data']:
                for item in intermediate_files:
                    non_products.extend(glob.glob(item))

            # Add level 1 source files if not requested
            if not options['include_source_data']:
                for item in l1_source_files:
                    non_products.extend(glob.glob(item))

            if len(non_products) > 0:
                cmd = ' '.join(['rm', '-rf'] + non_products)
                self._logger.info(' '.join(['REMOVING INTERMEDIATE DATA'
                                            ' COMMAND:', cmd]))

                output = ''
                try:
                    output = utilities.execute_cmd(cmd)
                finally:
                    if len(output) > 0:
                        self._logger.info(output)

            self.remove_products_from_xml()

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)

    def generate_statistics(self):
        """Generates statistics if required for the processor
        """

        options = self._parms['options']

        # Nothing to do if the user did not specify anything to build
        if not self._build_products or not options['include_statistics']:
            return

        # Generate the stats for each stat'able' science product

        # Hold the wild card strings in a type based dictionary
        files_to_search_for = dict()

        # Landsat files (Includes L4-L8)
        # The types must match the types in settings.py
        files_to_search_for['SR'] = ['*_sr_band[0-9].img']
        files_to_search_for['TOA'] = ['*_toa_band[0-9].img']
        files_to_search_for['BT'] = ['*_bt_band6.img',
                                     '*_bt_band1[0-1].img']
        files_to_search_for['INDEX'] = ['*_nbr.img', '*_nbr2.img',
                                        '*_ndmi.img', '*_ndvi.img',
                                        '*_evi.img', '*_savi.img',
                                        '*_msavi.img']
        files_to_search_for['LANDSAT_ST'] = ['*_st.img']
        files_to_search_for['RRS'] = ['*_rrs_band[0-7].img']
        files_to_search_for['CHLOR_A'] = ['*_chlor_a.img']

        # Build a command line arguments list
        cmd = ['espa_statistics.py',
               '--work_directory', self._work_dir,
               "--files_to_search_for '{}'".format(json.dumps(files_to_search_for))]

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['SUMMARY LANDSAT STATISTICS COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def get_product_name(self):
        """Build the product name from the product information and current
           time
        """

        if self._product_name is None:
            product_id = self._parms['product_id']

            # Get the current time information
            ts = datetime.datetime.today()

            # Extract stuff from the product information
            product_prefix = sensor.info(product_id).product_prefix

            product_name = ('{0}-SC{1}{2}{3}{4}{5}{6}'
                            .format(product_prefix,
                                    str(ts.year).zfill(4),
                                    str(ts.month).zfill(2),
                                    str(ts.day).zfill(2),
                                    str(ts.hour).zfill(2),
                                    str(ts.minute).zfill(2),
                                    str(ts.second).zfill(2)))

            self._product_name = product_name

        return self._product_name


class LandsatTMProcessor(LandsatProcessor):
    """Implements TM specific processing

    Note:
        Today all processing is inherited from the LandsatProcessors because
        the TM and ETM processors are identical.
    """

    def __init__(self, cfg, parms):
        super(LandsatTMProcessor, self).__init__(cfg, parms)


class LandsatETMProcessor(LandsatProcessor):
    """Implements ETM specific processing

    Note:
        Today all processing is inherited from the LandsatProcessors because
        the TM and ETM processors are identical.
    """

    def __init__(self, cfg, parms):
        super(LandsatETMProcessor, self).__init__(cfg, parms)


class LandsatOLITIRSProcessor(LandsatProcessor):
    """Implements OLITIRS (LC8) specific processing
    """

    def __init__(self, cfg, parms):
        super(LandsatOLITIRSProcessor, self).__init__(cfg, parms)

    def validate_parameters(self):
        """Validates the parameters required for the processor
        """

        # Call the base class parameter validation
        super(LandsatOLITIRSProcessor, self).validate_parameters()

        self._logger.info('Validating [LandsatOLITIRSProcessor] parameters')

        options = self._parms['options']

    def sr_command_line(self):
        """Returns the command line required to generate surface reflectance

        Evaluates the options requested by the user to define the command
        line string to use, or returns None indicating nothing todo.
        """

        options = self._parms['options']

        cmd = ['surface_reflectance.py', '--xml', self._xml_filename,
               '--write_toa']

        if not self.requires_sr_input:
            cmd.extend(['--process_sr', 'False'])

        return ' '.join(cmd)


class LandsatOLIProcessor(LandsatOLITIRSProcessor):
    """Implements OLI only (LO8) specific processing
    """

    def __init__(self, cfg, parms):
        super(LandsatOLIProcessor, self).__init__(cfg, parms)

    def validate_parameters(self):
        """Validates the parameters required for the processor
        """

        # Call the base class parameter validation
        super(LandsatOLIProcessor, self).validate_parameters()

        self._logger.info('Validating [LandsatOLIProcessor] parameters')

        options = self._parms['options']

        if options['include_sr'] is True:
            raise ESPAException('include_sr is an unavailable product option'
                            ' for OLI-Only data')

        if options['include_sr_thermal'] is True:
            raise ESPAException('include_sr_thermal is an unavailable product'
                            ' option for OLI-Only data')

        if options['include_dswe'] is True:
            raise ESPAException('include_dswe is an unavailable product option'
                            ' for OLI-Only data')

    def generate_spectral_indices(self):
        """Spectral Indices processing requires surface reflectance products
           as input

        So since, SR products can not be produced with OLI only data, OLI only
        processing can not produce spectral indices.
        """
        pass


class ModisProcessor(CDRProcessor):
    """Implements the common processing between all of the MODIS
       processors
    """

    def __init__(self, cfg, parms):
        super(ModisProcessor, self).__init__(cfg, parms)

        self._hdf_filename = None

    def validate_parameters(self):
        """Validates the parameters required for the processor
        """

        # Call the base class parameter validation
        super(ModisProcessor, self).validate_parameters()

        self._logger.info('Validating [ModisProcessor] parameters')

        options = self._parms['options']

        # Force these parameters to false if not provided
        # They are the required includes for product generation
        required_includes = ['include_customized_source_data',
                             'include_source_data',
                             'include_statistics']

        for parameter in required_includes:
            if not parameters.test_for_parameter(options, parameter):
                self._logger.warning('[{}] parameter missing defaulting to'
                                     ' False'.format(parameter))
                options[parameter] = False

        # Determine if we need to build products
        if not options['include_customized_source_data'] and not options['include_modis_ndvi']:

            self._logger.info('***NO CUSTOMIZED PRODUCTS CHOSEN***')
            self._build_products = False
        else:
            self._build_products = True

    def stage_input_data(self):
        """Stages the input data required for the processor
        """

        product_id = self._parms['product_id']
        download_url = self._parms['download_url']

        file_name = ''.join([product_id,
                             settings.MODIS_INPUT_FILENAME_EXTENSION])
        staged_file = os.path.join(self._stage_dir, file_name)

        # Download the source data
        transfer.download_file_url(download_url, staged_file)

        self._hdf_filename = os.path.basename(staged_file)
        work_file = os.path.join(self._work_dir, self._hdf_filename)

        # Copy the staged data to the work directory
        shutil.copyfile(staged_file, work_file)
        os.unlink(staged_file)

    def convert_to_raw_binary(self):
        """Converts the MODIS input data to our internal raw binary
           format
        """

        options = self._parms['options']

        # Build a command line arguments list
        cmd = ['convert_modis_to_espa',
               '--hdf', self._hdf_filename]
        if not options['include_source_data']:
            cmd.append('--del_src_files')

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['CONVERT MODIS TO ESPA COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def generate_spectral_indices(self):
        """Generates the requested spectral indices
        """

        options = self._parms['options']

        if options['include_modis_ndvi']:

            cmd = ['spectral_indices.py', '--xml', self._xml_filename, '--ndvi']
            cmd = ' '.join(cmd)

            self._logger.info(' '.join(['SPECTRAL INDICES COMMAND:', cmd]))

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def build_science_products(self):
        """Build the science products requested by the user

        Note:
            We get science products as the input, so the only thing really
            happening here is generating a customized product for the
            statistics generation.
            - Added option to request spectral indices but this should
            only be available for the M[O,Y]D09GA products
        """
        self._logger.info('[ModisProcessor] Building Science Products')

        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            self.convert_to_raw_binary()

            self.generate_spectral_indices()

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)

    def remove_products_from_xml(self):
        """Remove the specified products from the XML file

        The file is read into memory, processed, and written back out with out
        the specified products.

        Specific for Modis XML
        """
        options = self._parms['options']

        # Map order options to the products in the XML files
        # For Modis, the source data is surface reflectance...
        order2product = {
            'source_data': ['sr_refl']
        }

        # If nothing to do just return
        if self._xml_filename is None:
            return

        # Remove source products that were not requested
        products_to_remove = []
        if not options['include_customized_source_data']:
            products_to_remove.extend(
                order2product['source_data'])

        if products_to_remove is not None:
            # Create and load the metadata object
            espa_metadata = Metadata(xml_filename=self._xml_filename)

            # Search for and remove the items
            for band in espa_metadata.xml_object.bands.band:
                if band.attrib['product'] in products_to_remove:
                    self.remove_band_from_xml(band)

            # Validate the XML
            espa_metadata.validate()

            # Write it to the XML file
            espa_metadata.write(xml_filename=self._xml_filename)

            del espa_metadata

    def cleanup_work_dir(self):
        """Cleanup source data if it was not requested
        """

        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            self.remove_products_from_xml()

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)

        return

    def generate_statistics(self):
        """Generates statistics if required for the processor
        """

        options = self._parms['options']

        # Nothing to do if the user did not specify anything to build
        if not self._build_products or not options['include_statistics']:
            return

        # Generate the stats for each stat'able' science product

        # Hold the wild card strings in a type based dictionary
        files_to_search_for = dict()

        # MODIS files
        # The types must match the types in settings.py
        files_to_search_for['SR'] = ['*sur_refl_b*.img']
        files_to_search_for['INDEX'] = ['*NDVI.img', '*EVI.img', '*_sr_ndvi.img']
        files_to_search_for['LST'] = ['*LST_Day_1km.img',
                                      '*LST_Night_1km.img',
                                      '*LST_Day_6km.img',
                                      '*LST_Night_6km.img']
        files_to_search_for['EMIS'] = ['*Emis_*.img']

        # Build a command line arguments list
        cmd = ['espa_statistics.py',
               '--work_directory', self._work_dir,
               "--files_to_search_for '{}'".format(json.dumps(files_to_search_for))]

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['SUMMARY MODIS STATISTICS COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def get_product_name(self):
        """Build the product name from the product information and current
           time
        """

        if self._product_name is None:
            product_id = self._parms['product_id']

            # Get the current time information
            ts = datetime.datetime.today()

            # Extract stuff from the product information
            product_prefix = sensor.info(product_id).product_prefix

            product_name = ('{0}-SC{1}{2}{3}{4}{5}{6}'
                            .format(product_prefix,
                                    str(ts.year).zfill(4),
                                    str(ts.month).zfill(2),
                                    str(ts.day).zfill(2),
                                    str(ts.hour).zfill(2),
                                    str(ts.minute).zfill(2),
                                    str(ts.second).zfill(2)))

            self._product_name = product_name

        return self._product_name


class ModisAQUAProcessor(ModisProcessor):
    """Implements AQUA specific processing
    """

    def __init__(self, cfg, parms):
        super(ModisAQUAProcessor, self).__init__(cfg, parms)


class ModisTERRAProcessor(ModisProcessor):
    """Implements TERRA specific processing
    """

    def __init__(self, cfg, parms):
        super(ModisTERRAProcessor, self).__init__(cfg, parms)


class SentinelProcessor(CDRProcessor):
    """
    Implements the common processing between all of the Sentinel
    processors
    """

    def __init__(self, cfg, parms):
        super(SentinelProcessor, self).__init__(cfg, parms)

        self._zip_filename = None
        self._unpackage_dir = None

    def validate_parameters(self):
        """Validates the parameters required for the processor"""

        # Call the base class parameter validation
        super(SentinelProcessor, self).validate_parameters()

        self._logger.info('Validating [SentinelProcessor] parameters')

        options = self._parms['options']

        # Force these parameters to false if not provided
        # They are the required includes for product generation
        required_includes = ['include_s2_sr',
                             'include_s2_evi',
                             'include_s2_msavi',
                             'include_s2_nbr',
                             'include_s2_nbr2',
                             'include_s2_ndmi',
                             'include_s2_ndvi',
                             'include_s2_savi',
                             'include_statistics']

        for parameter in required_includes:
            if not parameters.test_for_parameter(options, parameter):
                self._logger.warning('[{}] parameter missing defaulting to'
                                     ' False'.format(parameter))
                options[parameter] = False

        # Determine if we need to build products
        if (not options['include_s2_sr'] and
                not options['include_s2_nbr'] and
                not options['include_s2_nbr2'] and
                not options['include_s2_ndvi'] and
                not options['include_s2_ndmi'] and
                not options['include_s2_savi'] and
                not options['include_s2_msavi'] and
                not options['include_s2_evi']):

            self._logger.info('***NO SCIENCE PRODUCTS CHOSEN***')
            self._build_products = False
        else:
            self._build_products = True

        # Generate SR input if needed, but do not deliver it in output
        self.requires_sr_input = any(
            options[x] for x in [
                'include_s2_sr',
                'include_s2_nbr',
                'include_s2_nbr2',
                'include_s2_ndvi',
                'include_s2_ndmi',
                'include_s2_savi',
                'include_s2_msavi',
                'include_s2_evi'
            ])

    def stage_input_data(self):
        """Stages the input data required for the processor
        """
        product_id = self._parms['product_id']
        download_url = self._parms['download_url']

        file_name = ''.join([product_id,
                             settings.S2_INPUT_FILENAME_EXTENSION])
        staged_file = os.path.join(self._stage_dir, file_name)

        # Download the source data
        transfer.download_file_url(download_url, staged_file)

        self._zip_filename = os.path.basename(staged_file)
        work_file = os.path.join(self._work_dir, self._zip_filename)

        # Copy the staged data to the work directory
        shutil.copyfile(staged_file, work_file)
        os.unlink(staged_file)

        cmd = ['unpackage_s2.py',
               '-i {0}'.format(work_file),
               '-o {0}'.format(self._work_dir)]

        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['UNPACKAGE SENTINEL COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)
            os.unlink(work_file)
            self._logger.info('Cleaned original Sentinel-2 .zip package {0}'.format(work_file))

        # Move the extracted sentinel-2 files into the top level of the working directory
        # and clean up empty .SAFE folder
        cmd = ['mv {f}/*.SAFE/* {f}'.format(f=self._work_dir),
               '&&',
               'rm -rf {0}/*.SAFE'.format(self._work_dir)]
        cmd = ' '.join(cmd)
        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)
                self._logger.info('Completed staging Sentinel-2 files in working directory')

    def convert_to_raw_binary(self):
        """Converts the Sentinel input data to our internal raw binary
           format
        """
        options = self._parms['options']

        # Build a command line arguments list
        cmd = ['convert_sentinel_to_espa']

        if not options['include_source_data']:
            cmd.append('--del_src_files')

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['CONVERT SENTINEL TO ESPA COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

            # Change back to the working directory
            os.chdir(self._work_dir)

    def sr_command_line(self):
        """Returns the command line required to generate surface reflectance

        Evaluates the options requested by the user to define the command
        line string to use, or returns None indicating nothing todo.

        Note:
            Provides the L4, L5, and L7 command line.  L8 processing overrides
            this method.
        """

        options = self._parms['options']

        cmd = ['surface_reflectance.py', '--xml', self._xml_filename]

        if not self.requires_sr_input:
            cmd.extend(['--process_sr', 'False'])

        return ' '.join(cmd)

    def generate_sr_products(self):
        """Generates surface reflectance products
        """

        cmd = self.sr_command_line()

        # Only if required
        if cmd is not None:

            self._logger.info(' '.join(['SENTINEL-2 SURFACE REFLECTANCE COMMAND:', cmd]))

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def generate_spectral_indices(self):
        """Generates the requested spectral indices
        """

        options = self._parms['options']

        cmd = None
        if (options['include_s2_nbr'] or
                options['include_s2_nbr2'] or
                options['include_s2_ndvi'] or
                options['include_s2_ndmi'] or
                options['include_s2_savi'] or
                options['include_s2_msavi'] or
                options['include_s2_evi']):

            cmd = ['spectral_indices.py', '--xml', self._xml_filename]

            # Add the specified index options
            if options['include_s2_nbr']:
                cmd.append('--nbr')
            if options['include_s2_nbr2']:
                cmd.append('--nbr2')
            if options['include_s2_ndvi']:
                cmd.append('--ndvi')
            if options['include_s2_ndmi']:
                cmd.append('--ndmi')
            if options['include_s2_savi']:
                cmd.append('--savi')
            if options['include_s2_msavi']:
                cmd.append('--msavi')
            if options['include_s2_evi']:
                cmd.append('--evi')

            cmd = ' '.join(cmd)

        # Only if required
        if cmd is not None:

            self._logger.info(' '.join(['SENTINEL-2 SPECTRAL INDICES COMMAND:', cmd]))

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def build_science_products(self):
        """Build the science products requested by the user
        """

        # Nothing to do if the user did not specify anything to build
        if not self._build_products:
            return

        self._logger.info('[SentinelProcessor] Building Science Products')

        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            self.convert_to_raw_binary()

            self.generate_sr_products()

            self.generate_spectral_indices()

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)

    def remove_products_from_xml(self):
        """Remove the specified products from the XML file

        The file is read into memory, processed, and written back out without
        the specified products.

        Specific for Sentinel-2 products
        """

        # Nothing to do if the user did not specify anything to build
        if not self._build_products:
            return

        options = self._parms['options']

        # Map order options to the products in the XML files
        # TODO: Figure out Sentinel-2 values
        order2product = {
            'source_data': ['MSIL1C'],
            'include_s2_sr': 'sr_refl',
            'keep_intermediate_data': 'intermediate_data'
        }

        # If nothing to do just return
        if self._xml_filename is None:
            return

        # Remove generated products that were not requested
        products_to_remove = []
        if not options['include_customized_source_data']:
            products_to_remove.extend(
                order2product['source_data'])
        if not options['include_s2_sr']:
            products_to_remove.append(
                order2product['include_s2_sr'])
        if not options['keep_intermediate_data']:
            products_to_remove.append(
                order2product['keep_intermediate_data'])

        if products_to_remove is not None:
            # Create and load the metadata object
            espa_metadata = Metadata(xml_filename=self._xml_filename)

            # Search for and remove the items
            for band in espa_metadata.xml_object.bands.band:
                if band.attrib['product'] in products_to_remove:
                    self.remove_band_from_xml(band)

            # Validate the XML
            espa_metadata.validate()

            # Write it to the XML file
            espa_metadata.write(xml_filename=self._xml_filename)

            del espa_metadata

    def cleanup_work_dir(self):
        """Cleanup all the intermediate non-products and the science
           products not requested
        """

        product_id = self._parms['product_id']
        options = self._parms['options']

        # TODO: Determine which S2 files need to be removed
        # Define intermediate files that need to be removed before product
        # tarball generation
        intermediate_files = [
            'lndsr.*.txt',
            'lndcal.*.txt',
            'LogReport*',
            '*_elevation.*'
        ]

        # Define L1 source files that may need to be removed before product
        # tarball generation
        l1_source_files = [
            # TODO perhaps eventually we will want to add the option to deliver these
            r'MTD_MSIL1C\.xml',
            r'MTD_TL\.xml',
            r'_B[0-9,A-Z]'
        ]

        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            non_products = []
            # Remove the intermediate non-product files
            if not options['keep_intermediate_data']:
                for item in intermediate_files:
                    non_products.extend(glob.glob(item))

            # Add level 1 source files if not requested
            if not options['include_source_data']:
                for item in l1_source_files:
                    non_products.extend([f for f in os.listdir('.') if re.search(item, f)])

            if len(non_products) > 0:
                cmd = ' '.join(['rm', '-rf'] + non_products)
                self._logger.info(' '.join(['REMOVING INTERMEDIATE DATA'
                                            ' COMMAND:', cmd]))

                output = ''
                try:
                    output = utilities.execute_cmd(cmd)
                finally:
                    if len(output) > 0:
                        self._logger.info(output)

            self.remove_products_from_xml()

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)

    def generate_statistics(self):
        """Generates statistics if required for the processor
        """

        options = self._parms['options']

        # Nothing to do if the user did not specify anything to build
        if not self._build_products or not options['include_statistics']:
            return

        # Generate the stats for each stat'able' science product

        # Hold the wild card strings in a type based dictionary
        files_to_search_for = dict()

        """
        # These original L1C bands may be included at a later date
        s2_toa_bands = list()
        s2_toa_bands.extend([*_B[0-9,A-Z].img])
        """

        s2_sr_bands = list()
        s2_sr_bands.extend(['*_sr_band*.img'])
        s2_sr_bands.extend(['*_sr_aerosol.img'])

        # The types must match the types in settings.py
        files_to_search_for['SR'] = s2_sr_bands
        # files_to_search_for['TOA'] = s2_toa_bands
        files_to_search_for['INDEX'] = ['*_nbr.img', '*_nbr2.img',
                                        '*_ndmi.img', '*_ndvi.img',
                                        '*_evi.img', '*_savi.img',
                                        '*_msavi.img']

        # Build a command line arguments list
        cmd = ['espa_statistics.py',
               '--work_directory', self._work_dir,
               "--files_to_search_for '{}'".format(json.dumps(files_to_search_for))]

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['SUMMARY LANDSAT STATISTICS COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def get_product_name(self):
        """Build the product name from the product information and current
           time
        """
        # product_id = self._parms['product_id']
        product_id = None

        # For sentinel-2 we want to work with the ESPA formatting
        # as opposed to the original product_id returned by M2M
        if self._product_name is None:
            prods = os.listdir(self._work_dir)
            for prod in prods:
                # Use the scene name taken from the XML filename
                if prod.startswith('S2') and prod.endswith('.xml'):
                    product_id = os.path.splitext(prod)[0]
                    break

            if product_id is None:
                msg = "Unable to determine ESPA-formatted product id"
                self._logger.exception(msg)
                raise ESPAException(msg)

            # Get the current time information
            ts = datetime.datetime.today()

            # Extract stuff from the product information
            product_prefix = sensor.info(product_id).product_prefix

            product_name = ('{0}-SC{1}{2}{3}{4}{5}{6}'
                            .format(product_prefix,
                                    str(ts.year).zfill(4),
                                    str(ts.month).zfill(2),
                                    str(ts.day).zfill(2),
                                    str(ts.hour).zfill(2),
                                    str(ts.minute).zfill(2),
                                    str(ts.second).zfill(2)))

            self._product_name = product_name

        return self._product_name


class VIIRSProcessor(CDRProcessor):
    """Implements the common processing between all of the VIIRS
       processors
    """

    def __init__(self, cfg, parms):
        super(VIIRSProcessor, self).__init__(cfg, parms)

        self._h5_filename = None

    def validate_parameters(self):
        """Validates the parameters required for the processor
        """

        # Call the base class parameter validation
        super(VIIRSProcessor, self).validate_parameters()

        self._logger.info('Validating [VIIRSProcessor] parameters')

        options = self._parms['options']

        # Force these parameters to false if not provided
        # They are the required includes for product generation
        required_includes = ['include_customized_source_data',
                             'include_source_data',
                             'include_statistics']

        for parameter in required_includes:
            if not parameters.test_for_parameter(options, parameter):
                self._logger.warning('[{}] parameter missing defaulting to'
                                     ' False'.format(parameter))
                options[parameter] = False

        # Determine if we need to build products
        if not options['include_customized_source_data'] and not options['include_viirs_ndvi']:

            self._logger.info('***NO CUSTOMIZED PRODUCTS CHOSEN***')
            self._build_products = False
        else:
            self._build_products = True

    def stage_input_data(self):
        """Stages the input data required for the processor
        """
        product_id = self._parms['product_id']
        download_url = self._parms['download_url']

        file_name = ''.join([product_id,
                             settings.VIIRS_INPUT_FILENAME_EXTENSION])
        staged_file = os.path.join(self._stage_dir, file_name)

        # Download the source data
        transfer.download_file_url(download_url, staged_file)

        self._h5_filename = os.path.basename(staged_file)
        work_file = os.path.join(self._work_dir, self._h5_filename)

        # Copy the staged data to the work directory
        shutil.copyfile(staged_file, work_file)
        os.unlink(staged_file)

    def convert_to_raw_binary(self):
        """Converts the Viirs input data to our internal raw binary
           format
        """

        options = self._parms['options']

        # Build a command line arguments list
        cmd = ['convert_viirs_to_espa',
               '--hdf', self._h5_filename]

        if not options['include_source_data']:
            cmd.append('--del_src_files')

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['CONVERT VIIRS TO ESPA COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def generate_spectral_indices(self):
        """Generates the requested spectral indices
        """

        options = self._parms['options']

        if options['include_viirs_ndvi']:

            cmd = ['spectral_indices.py', '--xml', self._xml_filename, '--ndvi']
            cmd = ' '.join(cmd)

            self._logger.info(' '.join(['SPECTRAL INDICES COMMAND:', cmd]))

            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            finally:
                if len(output) > 0:
                    self._logger.info(output)

    def build_science_products(self):
        """Build the science products requested by the user

        Note:
            We get science products as the input, so the only thing really
            happening here is generating a customized product for the
            statistics generation.
            - Added option to request spectral indices but this should
            only be available for the VNP09GA products
        """
        self._logger.info('[ViirsProcessor] Building Science Products')

        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            self.convert_to_raw_binary()

            self.generate_spectral_indices()

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)

    def remove_products_from_xml(self):
        """Remove the specified products from the XML file

        The file is read into memory, processed, and written back out with out
        the specified products.

        Specific for Viirs XML
        """
        options = self._parms['options']

        # Map order options to the products in the XML files
        # For Viirs, the source data is surface reflectance...
        order2product = {
            'source_data': ['sr_refl']
        }

        # If nothing to do just return
        if self._xml_filename is None:
            return

        # Remove source products that were not requested
        products_to_remove = []
        if not options['include_customized_source_data']:
            products_to_remove.extend(
                order2product['source_data'])

        if products_to_remove is not None:
            # Create and load the metadata object
            espa_metadata = Metadata(xml_filename=self._xml_filename)

            # Search for and remove the items
            for band in espa_metadata.xml_object.bands.band:
                if band.attrib['product'] in products_to_remove:
                    self.remove_band_from_xml(band)

            # Validate the XML
            espa_metadata.validate()

            # Write it to the XML file
            espa_metadata.write(xml_filename=self._xml_filename)

            del espa_metadata

    def cleanup_work_dir(self):
        """Cleanup source data if it was not requested
        """
        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            self.remove_products_from_xml()

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)
        return

    def generate_statistics(self):
        """Generates statistics if required for the processor
        """

        options = self._parms['options']

        # Nothing to do if the user did not specify anything to build
        if not self._build_products or not options['include_statistics']:
            return

        # Generate the stats for each stat'able' science product

        # Hold the wild card strings in a type based dictionary
        files_to_search_for = dict()

        # VIIRS files
        # The types must match the types in settings.py
        files_to_search_for['SR'] = ['*SurfReflect_I*.img']
        files_to_search_for['INDEX'] = ['*_sr_ndvi.img']

        # Build a command line arguments list
        cmd = ['espa_statistics.py',
               '--work_directory', self._work_dir,
               "--files_to_search_for '{}'".format(json.dumps(files_to_search_for))]

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['SUMMARY VIIRS STATISTICS COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def get_product_name(self):
        """Build the product name from the product information and current
           time
        """

        if self._product_name is None:
            product_id = self._parms['product_id']

            # Get the current time information
            ts = datetime.datetime.today()

            # Extract stuff from the product information
            product_prefix = sensor.info(product_id).product_prefix

            product_name = ('{0}-SC{1}{2}{3}{4}{5}{6}'
                            .format(product_prefix,
                                    str(ts.year).zfill(4),
                                    str(ts.month).zfill(2),
                                    str(ts.day).zfill(2),
                                    str(ts.hour).zfill(2),
                                    str(ts.minute).zfill(2),
                                    str(ts.second).zfill(2)))

            self._product_name = product_name

        return self._product_name


class PlotProcessor(ProductProcessor):
    """Implements Plot processing
    """

    def __init__(self, cfg, parms):

        # --------------------------------------------------------------------
        # Define the configuration for searching for files and some of the
        # text for the plots and filenames.
        # Doing this greatly simplified the code. :)
        # Should be real easy to add others. :)
        # --------------------------------------------------------------------

        L4_NAME = 'Landsat 4'
        L5_NAME = 'Landsat 5'
        L7_NAME = 'Landsat 7'
        L8_NAME = 'Landsat 8'
        L8_TIRS1_NAME = 'Landsat 8 TIRS1'
        L8_TIRS2_NAME = 'Landsat 8 TIRS2'
        TERRA_NAME = 'Terra'
        TERRA_NAME_DAILY = 'Terra 09GA'
        AQUA_NAME = 'Aqua'
        AQUA_NAME_DAILY = 'Aqua 09GA'
        VIIRS_NAME = 'Viirs'
        VIIRS_NAME_DAILY = 'Viirs 09GA'
        S2_NAME = 'Sentinel 2 MSI'

        SearchInfo = namedtuple('SearchInfo', ('key', 'filter_list'))

        # Only MODIS SR band 5 files
        _sr_swir_modis_b5_info = [SearchInfo(TERRA_NAME,
                                             ['MOD*sur_refl*b05.stats']),
                                  SearchInfo(AQUA_NAME,
                                             ['MYD*sur_refl*b05.stats'])]

        # Only VIIRS SR band 3 files
        _sr_swir_viirs_b3_info = [SearchInfo(VIIRS_NAME,
                                             ['VNP*SurfReflect_I3_1.stats'])]

        # SR (L4-L7 B5) (L8 B6) (MODIS B6) (VIIRS B3) (S2 B11)
        _sr_swir1_info = [SearchInfo(L4_NAME, ['LT4*_sr_band5.stats',
                                               'LT04*_sr_band5.stats']),
                          SearchInfo(L5_NAME, ['LT5*_sr_band5.stats',
                                               'LT05*_sr_band5.stats']),
                          SearchInfo(L7_NAME, ['LE7*_sr_band5.stats',
                                               'LE07*_sr_band5.stats']),
                          SearchInfo(L8_NAME, ['LC8*_sr_band6.stats',
                                               'LC08*_sr_band6.stats']),
                          SearchInfo(S2_NAME, ['S2*_sr_band11.stats']),
                          SearchInfo(TERRA_NAME, ['MOD*sur_refl_b06*.stats']),
                          SearchInfo(AQUA_NAME, ['MYD*sur_refl_b06*.stats']),

                          SearchInfo(VIIRS_NAME, ['VNP*SurfReflect_I3*.stats'])]

        # LaORCA bands (Landsat 8)
        _rrs_coastal_info = [SearchInfo(L8_NAME, ['L[C,O]08*_rrs_band1.stats'])]
        _rrs_blue_info = [SearchInfo(L8_NAME, ['L[C,O]08*_rrs_band2.stats'])]
        _rrs_green_info = [SearchInfo(L8_NAME, ['L[C,O]08*_rrs_band3.stats'])]
        _rrs_red_info = [SearchInfo(L8_NAME, ['L[C,O]08*_rrs_band4.stats'])]
        _rrs_nir_info = [SearchInfo(L8_NAME, ['L[C,O]08*_rrs_band5.stats'])]
        _rrs_swir1_info = [SearchInfo(L8_NAME, ['L[C,O]08*_rrs_band6.stats'])]
        _rrs_swir2_info = [SearchInfo(L8_NAME, ['L[C,O]08*_rrs_band7.stats'])]
        _chlor_a_info = [SearchInfo(L8_NAME, ['L[C,O]08*_chlor_a.stats'])]

        # SR (L4-L8 B7) (MODIS B7) (S2 B12)
        _sr_swir2_info = [SearchInfo(L4_NAME, ['LT4*_sr_band7.stats',
                                               'LT04*_sr_band7.stats']),
                          SearchInfo(L5_NAME, ['LT5*_sr_band7.stats',
                                               'LT05*_sr_band7.stats']),
                          SearchInfo(L7_NAME, ['LE7*_sr_band7.stats',
                                               'LE07*_sr_band7.stats']),
                          SearchInfo(L8_NAME, ['LC8*_sr_band7.stats',
                                               'LC08*_sr_band7.stats']),
                          SearchInfo(S2_NAME, ['S2*_sr_band12.stats']),
                          SearchInfo(TERRA_NAME, ['MOD*sur_refl_b07*.stats']),
                          SearchInfo(AQUA_NAME, ['MYD*sur_refl_b07*.stats'])]

        # SR (L8 B1)  (SENTINEL-2 AB B1) coastal aerosol
        _sr_coastal_info = [SearchInfo(L8_NAME, ['LC8*_sr_band1.stats',
                                                 'LC08*_sr_band1.stats']),
                            SearchInfo(S2_NAME, ['S2*_sr_band1.stats'])]

        # SR (L4-L7 B1) (L8 B2) (MODIS B3) (S2 B2)
        _sr_blue_info = [SearchInfo(L4_NAME, ['LT4*_sr_band1.stats',
                                              'LT04*_sr_band1.stats']),
                         SearchInfo(L5_NAME, ['LT5*_sr_band1.stats',
                                              'LT05*_sr_band1.stats']),
                         SearchInfo(L7_NAME, ['LE7*_sr_band1.stats',
                                              'LE07*_sr_band1.stats']),
                         SearchInfo(L8_NAME, ['LC8*_sr_band2.stats',
                                              'LC08*_sr_band2.stats']),
                         SearchInfo(S2_NAME, ['S2*_sr_band2.stats']),
                         SearchInfo(TERRA_NAME, ['MOD*sur_refl_b03*.stats']),
                         SearchInfo(AQUA_NAME, ['MYD*sur_refl_b03*.stats'])]

        # SR (L4-L7 B2) (L8 B3) (MODIS B4) (S2 B3)
        _sr_green_info = [SearchInfo(L4_NAME, ['LT4*_sr_band2.stats',
                                               'LT04*_sr_band2.stats']),
                          SearchInfo(L5_NAME, ['LT5*_sr_band2.stats',
                                               'LT05*_sr_band2.stats']),
                          SearchInfo(L7_NAME, ['LE7*_sr_band2.stats',
                                               'LE07*_sr_band2.stats']),
                          SearchInfo(L8_NAME, ['LC8*_sr_band3.stats',
                                               'LC08*_sr_band3.stats']),
                          SearchInfo(S2_NAME, ['S2*_sr_band3.stats']),
                          SearchInfo(TERRA_NAME, ['MOD*sur_refl_b04*.stats']),
                          SearchInfo(AQUA_NAME, ['MYD*sur_refl_b04*.stats'])]

        # SR (L4-L7 B3) (L8 B4) (MODIS B1) (VIIRS B1) (S2 B4)
        _sr_red_info = [SearchInfo(L4_NAME, ['LT4*_sr_band3.stats',
                                             'LT04*_sr_band3.stats']),
                        SearchInfo(L5_NAME, ['LT5*_sr_band3.stats',
                                             'LT05*_sr_band3.stats']),
                        SearchInfo(L7_NAME, ['LE7*_sr_band3.stats',
                                             'LE07*_sr_band3.stats']),
                        SearchInfo(L8_NAME, ['LC8*_sr_band4.stats',
                                             'LC08*_sr_band4.stats']),
                        SearchInfo(S2_NAME, ['S2*_sr_band4.stats']),
                        SearchInfo(TERRA_NAME, ['MOD*sur_refl_b01*.stats']),
                        SearchInfo(AQUA_NAME, ['MYD*sur_refl_b01*.stats']),
                        SearchInfo(VIIRS_NAME, ['VNP*SurfReflect_I1*.stats'])]

        # SR (L4-L7 B4) (L8 B5) (MODIS B2) (VIIRS B2) (S2 B8)
        _sr_nir_info = [SearchInfo(L4_NAME, ['LT4*_sr_band4.stats',
                                             'LT04*_sr_band4.stats']),
                        SearchInfo(L5_NAME, ['LT5*_sr_band4.stats',
                                             'LT05*_sr_band4.stats']),
                        SearchInfo(L7_NAME, ['LE7*_sr_band4.stats',
                                             'LE07*_sr_band4.stats']),
                        SearchInfo(L8_NAME, ['LC8*_sr_band5.stats',
                                             'LC08*_sr_band5.stats']),
                        SearchInfo(S2_NAME, ['S2*_sr_band8.stats']),
                        SearchInfo(TERRA_NAME, ['MOD*sur_refl_b02*.stats']),
                        SearchInfo(AQUA_NAME, ['MYD*sur_refl_b02*.stats']),

                        SearchInfo(VIIRS_NAME, ['VNP*SurfReflect_I2*.stats'])]

        # Only Sentinel 2
        _sr_b5_info = [SearchInfo(S2_NAME, ['S2*_sr_band5.stats'])]
        _sr_b6_info = [SearchInfo(S2_NAME, ['S2*_sr_band6.stats'])]
        _sr_b7_info = [SearchInfo(S2_NAME, ['S2*_sr_band7.stats'])]
        _sr_b8a_info = [SearchInfo(S2_NAME, ['S2*_sr_band8a.stats'])]
        _sr_b9_info = [SearchInfo(S2_NAME, ['S2*_sr_band9.stats'])]

        # SR (L8 B9) (S2 B10)
        _sr_cirrus_info = [SearchInfo(L8_NAME, ['LC8*_sr_band9.stats',
                                                'LC08*_sr_band9.stats']),
                           SearchInfo(S2_NAME, ['S2*_sr_band10.stats'])]

        # Only Landsat TOA band 6(L4-7) band 10(L8) band 11(L8)
        _bt_thermal_info = [SearchInfo(L4_NAME, ['LT4*_bt_band6.stats',
                                                 'LT04*_bt_band6.stats']),
                            SearchInfo(L5_NAME, ['LT5*_bt_band6.stats',
                                                 'LT05*_bt_band6.stats']),
                            SearchInfo(L7_NAME, ['LE7*_bt_band6.stats',
                                                 'LE07*_bt_band6.stats']),
                            SearchInfo(L8_TIRS1_NAME,
                                       ['LC8*_bt_band10.stats',
                                        'LC08*_bt_band10.stats']),
                            SearchInfo(L8_TIRS2_NAME,
                                       ['LC8*_bt_band11.stats',
                                        'LC08*_bt_band11.stats'])]

        # Only Landsat TOA (L4-L7 B5) (L8 B6)
        _toa_swir1_info = [SearchInfo(L4_NAME, ['LT4*_toa_band5.stats',
                                                'LT04*_toa_band5.stats']),
                           SearchInfo(L5_NAME, ['LT5*_toa_band5.stats',
                                                'LT05*_toa_band5.stats']),
                           SearchInfo(L7_NAME, ['LE7*_toa_band5.stats',
                                                'LE07*_toa_band5.stats']),
                           SearchInfo(L8_NAME, ['L[C,O]8*_toa_band6.stats',
                                                'L[C,O]08*_toa_band6.stats'])]

        # Only Landsat TOA (L4-L8 B7)
        _toa_swir2_info = [SearchInfo(L4_NAME, ['LT4*_toa_band7.stats',
                                                'LT04*_toa_band7.stats']),
                           SearchInfo(L5_NAME, ['LT5*_toa_band7.stats',
                                                'LT05*_toa_band7.stats']),
                           SearchInfo(L7_NAME, ['LE7*_toa_band7.stats',
                                                'LE07*_toa_band7.stats']),
                           SearchInfo(L8_NAME, ['L[C,O]8*_toa_band7.stats',
                                                'L[C,O]08*_toa_band7.stats'])]

        # Only Landsat TOA (L8 B1)
        _toa_coastal_info = [SearchInfo(L8_NAME,
                                        ['L[C,O]8*_toa_band1.stats',
                                         'L[C,O]08*_toa_band1.stats'])]

        # Only Landsat TOA (L4-L7 B1) (L8 B2)
        _toa_blue_info = [SearchInfo(L4_NAME, ['LT4*_toa_band1.stats',
                                               'LT04*_toa_band1.stats']),
                          SearchInfo(L5_NAME, ['LT5*_toa_band1.stats',
                                               'LT05*_toa_band1.stats']),
                          SearchInfo(L7_NAME, ['LE7*_toa_band1.stats',
                                               'LE07*_toa_band1.stats']),
                          SearchInfo(L8_NAME, ['L[C,O]8*_toa_band2.stats',
                                               'L[C,O]08*_toa_band2.stats'])]

        # Only Landsat TOA (L4-L7 B2) (L8 B3)
        _toa_green_info = [SearchInfo(L4_NAME, ['LT4*_toa_band2.stats',
                                                'LT04*_toa_band2.stats']),
                           SearchInfo(L5_NAME, ['LT5*_toa_band2.stats',
                                                'LT05*_toa_band2.stats']),
                           SearchInfo(L7_NAME, ['LE7*_toa_band2.stats',
                                                'LE07*_toa_band2.stats']),
                           SearchInfo(L8_NAME, ['L[C,O]8*_toa_band3.stats',
                                                'L[C,O]08*_toa_band3.stats'])]

        # Only Landsat TOA (L4-L7 B3) (L8 B4)
        _toa_red_info = [SearchInfo(L4_NAME, ['LT4*_toa_band3.stats',
                                              'LT04*_toa_band3.stats']),
                         SearchInfo(L5_NAME, ['LT5*_toa_band3.stats',
                                              'LT05*_toa_band3.stats']),
                         SearchInfo(L7_NAME, ['LE7*_toa_band3.stats',
                                              'LE07*_toa_band3.stats']),
                         SearchInfo(L8_NAME, ['L[C,O]8*_toa_band4.stats',
                                              'L[C,O]08*_toa_band4.stats'])]

        # Only Landsat TOA (L4-L7 B4) (L8 B5)
        _toa_nir_info = [SearchInfo(L4_NAME, ['LT4*_toa_band4.stats',
                                              'LT04*_toa_band4.stats']),
                         SearchInfo(L5_NAME, ['LT5*_toa_band4.stats',
                                              'LT05*_toa_band4.stats']),
                         SearchInfo(L7_NAME, ['LE7*_toa_band4.stats',
                                              'LE07*_toa_band4.stats']),
                         SearchInfo(L8_NAME, ['L[C,O]8*_toa_band5.stats',
                                              'L[C,O]08*_toa_band5.stats'])]

        # Only Landsat TOA (L8 B9)
        _toa_cirrus_info = [SearchInfo(L8_NAME, ['L[C,O]8*_toa_band9.stats',
                                                 'L[C,O]08*_toa_band9.stats'])]

        # Only MODIS band 20 files
        _emis_20_info = [SearchInfo(TERRA_NAME, ['MOD*Emis_20.stats']),
                         SearchInfo(AQUA_NAME, ['MYD*Emis_20.stats'])]

        # Only MODIS band 22 files
        _emis_22_info = [SearchInfo(TERRA_NAME, ['MOD*Emis_22.stats']),
                         SearchInfo(AQUA_NAME, ['MYD*Emis_22.stats'])]

        # Only MODIS band 23 files
        _emis_23_info = [SearchInfo(TERRA_NAME, ['MOD*Emis_23.stats']),
                         SearchInfo(AQUA_NAME, ['MYD*Emis_23.stats'])]

        # Only MODIS band 29 files
        _emis_29_info = [SearchInfo(TERRA_NAME, ['MOD*Emis_29.stats']),
                         SearchInfo(AQUA_NAME, ['MYD*Emis_29.stats'])]

        # Only MODIS band 31 files
        _emis_31_info = [SearchInfo(TERRA_NAME, ['MOD*Emis_31.stats']),
                         SearchInfo(AQUA_NAME, ['MYD*Emis_31.stats'])]

        # Only MODIS band 32 files
        _emis_32_info = [SearchInfo(TERRA_NAME, ['MOD*Emis_32.stats']),
                         SearchInfo(AQUA_NAME, ['MYD*Emis_32.stats'])]

        # MODIS and Landsat LST Day files
        _lst_day_info = [SearchInfo(TERRA_NAME, ['MOD*LST_Day_*.stats']),
                         SearchInfo(AQUA_NAME, ['MYD*LST_Day_*.stats']),
                         SearchInfo(L4_NAME, ['LT4*_st.stats',
                                              'LT04*_st.stats']),
                         SearchInfo(L5_NAME, ['LT5*_st.stats',
                                              'LT05*_st.stats']),
                         SearchInfo(L7_NAME, ['LE7*_st.stats',
                                              'LE07*_st.stats']),
                         SearchInfo(L8_NAME, ['L[C,O]8*_st.stats',
                                              'L[C,O]08*_st.stats'])]

        # Only MODIS Night files
        _lst_night_info = [SearchInfo(TERRA_NAME, ['MOD*LST_Night_*.stats']),
                           SearchInfo(AQUA_NAME, ['MYD*LST_Night_*.stats'])]

        # MODIS, VIIRS, Sentinel, and Landsat NDVI files
        _ndvi_info = [SearchInfo(L4_NAME, ['LT4*_sr_ndvi.stats',
                                           'LT04*_sr_ndvi.stats']),
                      SearchInfo(L5_NAME, ['LT5*_sr_ndvi.stats',
                                           'LT05*_sr_ndvi.stats']),
                      SearchInfo(L7_NAME, ['LE7*_sr_ndvi.stats',
                                           'LE07*_sr_ndvi.stats']),
                      SearchInfo(L8_NAME, ['LC8*_sr_ndvi.stats',
                                           'LC08*_sr_ndvi.stats']),
                      SearchInfo(S2_NAME, ['S2*_sr_ndvi.stats']),
                      SearchInfo(TERRA_NAME, ['MOD*_NDVI.stats']),
                      SearchInfo(AQUA_NAME, ['MYD*_NDVI.stats']),
                      SearchInfo(TERRA_NAME_DAILY, ['MOD*_sr_ndvi.stats']),
                      SearchInfo(AQUA_NAME_DAILY, ['MYD*_sr_ndvi.stats']),
                      SearchInfo(VIIRS_NAME_DAILY, ['VNP*_sr_ndvi.stats'])]

        # MODIS, Sentinel, and Landsat EVI files
        _evi_info = [SearchInfo(L4_NAME, ['LT4*_sr_evi.stats',
                                          'LT04*_sr_evi.stats']),
                     SearchInfo(L5_NAME, ['LT5*_sr_evi.stats',
                                          'LT05*_sr_evi.stats']),
                     SearchInfo(L7_NAME, ['LE7*_sr_evi.stats',
                                          'LE07*_sr_evi.stats']),
                     SearchInfo(L8_NAME, ['LC8*_sr_evi.stats',
                                          'LC08*_sr_evi.stats']),
                     SearchInfo(S2_NAME, ['S2*_sr_evi.stats']),
                     SearchInfo(TERRA_NAME, ['MOD*_EVI.stats']),
                     SearchInfo(AQUA_NAME, ['MYD*_EVI.stats'])]

        # Sentinel and Landsat SAVI files
        _savi_info = [SearchInfo(L4_NAME, ['LT4*_sr_savi.stats',
                                           'LT04*_sr_savi.stats']),
                      SearchInfo(L5_NAME, ['LT5*_sr_savi.stats',
                                           'LT05*_sr_savi.stats']),
                      SearchInfo(L7_NAME, ['LE7*_sr_savi.stats',
                                           'LE07*_sr_savi.stats']),
                      SearchInfo(L8_NAME, ['LC8*_sr_savi.stats',
                                           'LC08*_sr_savi.stats']),
                      SearchInfo(S2_NAME, ['S2*_sr_savi.stats'])]

        # Sentinel and Landsat MSAVI files
        _msavi_info = [SearchInfo(L4_NAME, ['LT4*_sr_msavi.stats',
                                            'LT04*_sr_msavi.stats']),
                       SearchInfo(L5_NAME, ['LT5*_sr_msavi.stats',
                                            'LT05*_sr_msavi.stats']),
                       SearchInfo(L7_NAME, ['LE7*_sr_msavi.stats',
                                            'LE07*_sr_msavi.stats']),
                       SearchInfo(L8_NAME, ['LC8*_sr_msavi.stats',
                                            'LC08*_sr_msavi.stats']),
                       SearchInfo(S2_NAME, ['S2*_sr_msavi.stats'])]

        # Sentinel and Landsat NBR files
        _nbr_info = [SearchInfo(L4_NAME, ['LT4*_sr_nbr.stats',
                                          'LT04*_sr_nbr.stats']),
                     SearchInfo(L5_NAME, ['LT5*_sr_nbr.stats',
                                          'LT05*_sr_nbr.stats']),
                     SearchInfo(L7_NAME, ['LE7*_sr_nbr.stats',
                                          'LE07*_sr_nbr.stats']),
                     SearchInfo(L8_NAME, ['LC8*_sr_nbr.stats',
                                          'LC08*_sr_nbr.stats']),
                     SearchInfo(S2_NAME, ['S2*_sr_nbr.stats'])]

        # Sentinel and Landsat NBR2 files
        _nbr2_info = [SearchInfo(L4_NAME, ['LT4*_sr_nbr2.stats',
                                           'LT04*_sr_nbr2.stats']),
                      SearchInfo(L5_NAME, ['LT5*_sr_nbr2.stats',
                                           'LT05*_sr_nbr2.stats']),
                      SearchInfo(L7_NAME, ['LE7*_sr_nbr2.stats',
                                           'LE07*_sr_nbr2.stats']),
                      SearchInfo(L8_NAME, ['LC8*_sr_nbr2.stats',
                                           'LC08*_sr_nbr2.stats']),
                      SearchInfo(S2_NAME, ['S2*_sr_nrb2.stats'])]

        # Sentinel and Landsat NDMI files
        _ndmi_info = [SearchInfo(L4_NAME, ['LT4*_sr_ndmi.stats',
                                           'LT04*_sr_ndmi.stats']),
                      SearchInfo(L5_NAME, ['LT5*_sr_ndmi.stats',
                                           'LT05*_sr_ndmi.stats']),
                      SearchInfo(L7_NAME, ['LE7*_sr_ndmi.stats',
                                           'LE07*_sr_ndmi.stats']),
                      SearchInfo(L8_NAME, ['LC8*_sr_ndmi.stats',
                                           'LC08*_sr_ndmi.stats']),
                      SearchInfo(S2_NAME, ['S2*_sr_ndmi.stats'])]

        self.work_list = [(_sr_coastal_info, 'SR COASTAL AEROSOL'),
                          (_sr_blue_info, 'SR Blue'),
                          (_sr_green_info, 'SR Green'),
                          (_sr_red_info, 'SR Red'),
                          (_sr_nir_info, 'SR NIR'),
                          (_sr_swir1_info, 'SR SWIR1'),
                          (_sr_swir2_info, 'SR SWIR2'),
                          (_sr_cirrus_info, 'SR CIRRUS'),
                          (_sr_swir_modis_b5_info, 'SR SWIR B5'),
                          (_sr_swir_viirs_b3_info, 'SR SWIR B3'),
                          (_sr_b5_info, 'Sentinel-2 SR B5'),
                          (_sr_b6_info, 'Sentinel-2 SR B6'),
                          (_sr_b7_info, 'Sentinel-2 SR B7'),
                          (_sr_b8a_info, 'Sentinel-2 SR B8'),
                          (_sr_b9_info, 'Sentinel-2 SR B9'),
                          (_bt_thermal_info, 'BT Thermal'),
                          (_toa_coastal_info, 'TOA COASTAL AEROSOL'),
                          (_toa_blue_info, 'TOA Blue'),
                          (_toa_green_info, 'TOA Green'),
                          (_toa_red_info, 'TOA Red'),
                          (_toa_nir_info, 'TOA NIR'),
                          (_toa_swir1_info, 'TOA SWIR1'),
                          (_toa_swir2_info, 'TOA SWIR2'),
                          (_toa_cirrus_info, 'TOA CIRRUS'),
                          (_emis_20_info, 'Emis Band 20'),
                          (_emis_22_info, 'Emis Band 22'),
                          (_emis_23_info, 'Emis Band 23'),
                          (_emis_29_info, 'Emis Band 29'),
                          (_emis_31_info, 'Emis Band 31'),
                          (_emis_32_info, 'Emis Band 32'),
                          (_rrs_coastal_info, 'RRS Coastal'),
                          (_rrs_blue_info, 'RRS Blue'),
                          (_rrs_green_info, 'RRS Green'),
                          (_rrs_red_info, 'RRS Red'),
                          (_rrs_nir_info, 'RRS NIR'),
                          (_rrs_swir1_info, 'RRS SWIR1'),
                          (_rrs_swir2_info, 'RRS SWIR2'),
                          (_chlor_a_info, 'CHLOR_A'),
                          (_lst_day_info, 'LST Day'),
                          (_lst_night_info, 'LST Night'),
                          (_ndvi_info, 'NDVI'),
                          (_evi_info, 'EVI'),
                          (_savi_info, 'SAVI'),
                          (_msavi_info, 'MSAVI'),
                          (_nbr_info, 'NBR'),
                          (_nbr2_info, 'NBR2'),
                          (_ndmi_info, 'NDMI')]

        super(PlotProcessor, self).__init__(cfg, parms)

    def validate_parameters(self):
        """Validates the parameters required for the processor
        """

        # Call the base class parameter validation
        super(PlotProcessor, self).validate_parameters()

    def process_band_type(self, (search_list, band_type)):
        """A generic processing routine which finds the files to process based
           on the provided search criteria

        Utilizes the provided band type as part of the plot names and
        filenames.  If no files are found, no plots or combined statistics
        will be generated.
        """
        # Build a command line arguments list
        cmd = ['espa_plotting.py',
               "--band_type '{}'".format(band_type),
               "--search_list '{}'".format(json.dumps(search_list))]

        # Turn the list into a string
        cmd = ' '.join(cmd)
        self._logger.info(' '.join(['SUMMARY STATISTICS AND PLOTTING COMMAND:', cmd]))

        output = ''
        try:
            output = utilities.execute_cmd(cmd)
        finally:
            if len(output) > 0:
                self._logger.info(output)

    def process_stats(self):
        """Process the stat results to plots

        If any bands/files do not exist, plots will not be generated for them.
        """

        # Change to the working directory
        current_directory = os.getcwd()
        os.chdir(self._work_dir)

        try:
            map(self.process_band_type, self.work_list)

        finally:
            # Change back to the previous directory
            os.chdir(current_directory)

    def stage_input_data(self):
        """Stages the input data required for the processor
        """

        staging.stage_statistics_data(self._output_dir, self._stage_dir,
                                      self._work_dir, self._parms)

    def get_product_name(self):
        """Return the product name for that statistics and plot product from
           the product request information
        """

        if self._product_name is None:
            self._product_name = '-'.join([self._parms['orderid'],
                                           'statistics'])

        return self._product_name

    def process_product(self):
        """Perform the processor specific processing to generate the
           requested product
        """

        # Stage the required input data
        self.stage_input_data()

        # Create the combinded stats and plots
        self.process_stats()

        # Package and deliver product
        (destination_product_file, destination_cksum_file) = \
            self.distribute_product()

        return (destination_product_file, destination_cksum_file)


# ===========================================================================
def get_instance(cfg, parms):
    """Provides a method to retrieve the proper processor for the specified
       product.
    """

    product_id = parms['product_id']

    if product_id == 'plot':
        return PlotProcessor(cfg, parms)

    if sensor.is_landsat4(product_id):
        return LandsatTMProcessor(cfg, parms)
    elif sensor.is_landsat5(product_id):
        return LandsatTMProcessor(cfg, parms)
    elif sensor.is_landsat7(product_id):
        return LandsatETMProcessor(cfg, parms)
    elif sensor.is_lo08(product_id):
        return LandsatOLIProcessor(cfg, parms)
    elif sensor.is_lt08(product_id):
        raise NotImplementedError('A processor for [{}] has not been'
                                  ' implemented'.format(product_id))
    elif sensor.is_lc08(product_id):
        return LandsatOLITIRSProcessor(cfg, parms)

    elif sensor.is_terra(product_id):
        return ModisTERRAProcessor(cfg, parms)
    elif sensor.is_aqua(product_id):
        return ModisAQUAProcessor(cfg, parms)

    elif sensor.is_viirs(product_id):
        return VIIRSProcessor(cfg, parms)

    elif sensor.is_sentinel(product_id):
        return SentinelProcessor(cfg, parms)

    else:
        raise NotImplementedError('A processor for [{}] has not been'
                                  ' implemented'.format(product_id))
