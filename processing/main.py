import argparse
import datetime
import os
import socket
import sys

from functools import partial
from time import sleep

### espa-processing imports
import config
import parameters
import processor
import settings
import sensor
import utilities

from api_interface import APIServer, APIException
from environment import Environment
from logging_tools import EspaLogging, get_base_logger, get_stdout_handler, get_stderr_handler, archive_log_files

base_logger = get_base_logger()

def work(cfg, params, developer_sleep_mode=False):
    """
    Take the environment configuration, order parameters and initiate order processing.
    Note: Much of this code was taken from the ondemand_mapper.py script in espa-processing.

    Args:
        cfg (dict): Configuration params given by config.config() and by the worker environment
        params (dict): JSON response from the API for a single granule or scene

    Returns:
        None, Products are generated, packaged, and distributed if processing was successful

    """
    # This will be the Mesos node hostname
    processing_location = socket.gethostname()

    # Use the base_logger initially, if an exception occurs before the processing logger is configured
    # the base_logger will handle log it
    logger = base_logger

    if not parameters.test_for_parameter(params, 'options'):
        raise ValueError('Error missing JSON [options] record')

    start_time = datetime.datetime.now()

    # Initialize so that we don't sleep
    dont_sleep = True

    # Note that the API response "scene" value is what we use for product_id
    try:
        (order_id, product_id, product_type, options) = \
            (params['orderid'], params['scene'], params['product_type'],
             params['options'])

        if product_id != 'plot':
            # Developer mode is always false unless you are a developer
            # so sleeping will always occur for non-plotting requests
            # Override with the developer mode
            dont_sleep = developer_sleep_mode

        # Fix the orderid in-case it contains any single quotes
        # The processors can not handle single quotes in the email
        # portion due to usage in command lines.
        params['orderid'] = order_id.replace("'", '')

        # product_id is not part of the API response - we add it here
        if not parameters.test_for_parameter(params, 'product_id'):
            params['product_id'] = product_id

        # Figure out if debug level logging was requested
        debug = False
        if parameters.test_for_parameter(options, 'debug'):
            debug = options['debug']

        # Configure and get the logger for this order request
        EspaLogging.configure(settings.PROCESSING_LOGGER, order=order_id,
                              product=product_id, debug=debug)

        # Replace the base_logger with the processing_logger
        logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

        # add our stdout/stderr log streams
        logger.addHandler(get_stdout_handler())
        logger.addHandler(get_stderr_handler())

        logger.info('Processing {}:{}'.format(order_id, product_id))
        logger.info('Attempting connection to {0}'.format(cfg['espa_api']))

        # will throw an exception on init if unable to get a 200 response
        server = APIServer(cfg['espa_api'])

        # will throw an exception if does not receive a 200 response
        status = server.update_status(product_id, order_id, processing_location, 'processing')

        if product_id != 'plot':
            # Make sure we can process the sensor
            tmp_info = sensor.info(product_id)
            del tmp_info

            # Make sure we have a valid output format
            if not parameters.test_for_parameter(options, 'output_format'):
                logger.warning('[output_format] parameter missing defaulting to envi')

                options['output_format'] = 'envi'

            if (options['output_format'] not in parameters.VALID_OUTPUT_FORMATS):
                raise ValueError('Invalid Output format {}'.format(options['output_format']))

                # ----------------------------------------------------------------
                # NOTE: The first thing the product processor does during
                #       initialization is validate the input parameters.
                # ----------------------------------------------------------------

        destination_product_file = 'ERROR'
        destination_cksum_file = 'ERROR'

        pp = None

        try:
            # All processors are implemented in the processor module
            pp = processor.get_instance(cfg, params)

            (destination_product_file, destination_cksum_file) = pp.process()

        finally:
            # Free disk space to be nice to the whole system.
            if pp is not None:
                pp.remove_product_directory()

        # Sleep the number of seconds for minimum request duration
        sleep(utilities.get_sleep_duration(cfg, start_time, dont_sleep))

        archive_log_files(order_id, product_id)

        # Everything was successful so mark the scene complete
        server.mark_scene_complete(product_id, order_id,
                                   processing_location,
                                   destination_product_file,
                                   destination_cksum_file,
                                   '') # sets log_file_contents to empty string ''
        return True

    except Exception as e:
        # First log the exception
        logger.exception('Exception encountered in processing.main.work:\nexception: {}'.format(e))

        try:
            # Sleep the number of seconds for minimum request duration
            logger.debug('Attempting to archive log files for order_id: {}\nproduct_id: {}'.format(order_id, product_id))
            sleep(utilities.get_sleep_duration(cfg, start_time, dont_sleep))
            archive_log_files(order_id, product_id)
        except Exception as e2:
            logger.exception('Problem archiving log files. error: {}'.format(e2))

        try:
            logger.debug('Attempting to set product error, order_id: {}\nproduct_id: {}'.format(order_id, product_id))
            logged_contents = EspaLogging.read_logger_file(settings.PROCESSING_LOGGER)
            error_log = "Processing Log: {}\n\nException: {}".format(logged_contents, e)
            server.set_scene_error(product_id, order_id, processing_location, str(e))
        except Exception as e3:
            logger.exception('Unable to reach ESPA API and set product error for order_id: {}\nproduct_id: {}\nerror: {}'.format(order_id, product_id, e3))
            raise e3

        return False


def main(data=None):
    try:
        # retrieve a dict containing processing environment configuration values
        cfg = config.config()
        sleep_for = cfg.get('init_sleep_seconds')
        base_logger.info('Holding for {} seconds'.format(sleep_for))
        sleep(sleep_for)

        # export values for the container environment
        config.export_environment_variables(cfg)

        # create the .netrc file
        utilities.build_netrc()

        base_logger.debug('OS ENV - {0}'.format(['{0}: {1}'.format(var, val) for var, val in os.environ.items()]))
        base_logger.info('configured parameters - {0}'.format(['{0}: {1}'.format(var, val) for var, val in cfg.items()]))

        if not data:
            parser = argparse.ArgumentParser()
            parser.add_argument(dest="data", action="store", metavar="JSON", type=utilities.convert_json,
                                help="response from the API containing order information")
            args = parser.parse_args()
            data = args.data

        base_logger.info('order data - {0}'.format(data))
        for d in data:
            result = work(cfg, d)
            base_logger.info('processing.work executed for data {} successfully? {}'.format(d, result))
    except Exception as e:
        msg = 'ESPA Worker error, problem executing main.main\nError: {}'.format(e)
        base_logger.exception(msg)
        # Exit with 1 so Container and Task know there was a problem and report to the framework appropriately
        sys.exit(msg)

if __name__ == '__main__':
    main()
