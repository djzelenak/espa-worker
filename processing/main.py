
import os
import sys
import datetime
import argparse
import json
import socket
import shutil
import logging
from functools import partial
from time import sleep

### espa-processing imports
import processor
import config
import parameters
import settings
import sensor
import utilities
import api_interface
from logging_tools import EspaLogging

# local objects and methods
from environment import Environment

WORKER_LOG_PREFIX = 'espa-worker'
WORKER_LOG_FILENAME = '.'.join([WORKER_LOG_PREFIX, 'log'])

EspaLogging.configure_base_logger(filename=WORKER_LOG_FILENAME)
# Initially set to the base logger
base_logger = EspaLogging.get_logger('base')

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add logging to stdout and stderr
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
stdout_handler.setFormatter(formatter)
base_logger.addHandler(stdout_handler)

stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.DEBUG)
stderr_handler.setFormatter(formatter)
base_logger.addHandler(stderr_handler)

def remove_single_quotes(instring):
    return instring.replace("'", '')


def convert_json(data):
    if type(data) is str:
        return json.loads(data)
    if type(data) in (list, dict):
        return json.dumps(data)


def set_product_error(server, order_id, product_id, processing_location):
    """Call the API server routine to set a product request to error

    Provides a sleep retry implementation to hopefully by-pass any errors
    encountered, so that we do not get requests that have failed, but
    show a status of processing.
    """

    if server is not None:
        logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

        attempt = 0
        sleep_seconds = settings.DEFAULT_SLEEP_SECONDS
        while True:
            try:
                logger.info('Product ID is [{}]'.format(product_id))
                logger.info('Order ID is [{}]'.format(order_id))
                logger.info('Processing Location is [{}]'
                            .format(processing_location))

                logged_contents = \
                    EspaLogging.read_logger_file(settings.PROCESSING_LOGGER)

                status = server.set_scene_error(product_id, order_id,
                                                processing_location,
                                                logged_contents)

                if not status:
                    logger.critical('Failed processing API call to'
                                    ' set_scene_error')
                    return False

                break

            except Exception:
                logger.critical('Failed processing API call to'
                                ' set_scene_error')
                logger.exception('Exception encountered and follows')

                if attempt < settings.MAX_SET_SCENE_ERROR_ATTEMPTS:
                    sleep(sleep_seconds)  # sleep before trying again
                    attempt += 1
                    sleep_seconds = int(sleep_seconds * 1.5)
                    continue
                else:
                    return False

    return True


def archive_log_files(order_id, product_id):
    """Archive the log files for the current job
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    try:
        # Determine the destination path for the logs
        output_dir = Environment().get_distribution_directory()
        destination_path = os.path.join(output_dir, 'logs', order_id)
        # Create the path
        utilities.create_directory(destination_path)

        # Job log file
        logfile_path = EspaLogging.get_filename(settings.PROCESSING_LOGGER)
        full_logfile_path = os.path.abspath(logfile_path)
        log_name = os.path.basename(full_logfile_path)
        # Determine full destination
        destination_file = os.path.join(destination_path, log_name)
        # Copy it
        shutil.copyfile(full_logfile_path, destination_file)

        # Mapper log file
        full_logfile_path = os.path.abspath(WORKER_LOG_FILENAME)
        final_log_name = '-'.join([WORKER_LOG_PREFIX, order_id, product_id])
        final_log_name = '.'.join([final_log_name, 'log'])
        # Determine full destination
        destination_file = os.path.join(destination_path, final_log_name)
        # Copy it
        shutil.copyfile(full_logfile_path, destination_file)

    except Exception:
        # We don't care because we are at the end of processing
        # And if we are on the successful path, we don't care either
        logger.exception('Exception encountered and follows')


def get_sleep_duration(proc_cfg, start_time, dont_sleep, key='espa_min_request_duration_in_seconds'):
    """Logs details and returns number of seconds to sleep
    """
    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    # Determine if we need to sleep
    end_time = datetime.datetime.now()
    seconds_elapsed = (end_time - start_time).seconds
    logger.info('Processing Time Elapsed {0} Seconds'.format(seconds_elapsed))

    min_seconds = int((proc_cfg.get(key)))

    seconds_to_sleep = 1
    if dont_sleep:
        # We don't need to sleep
        seconds_to_sleep = 1
    elif seconds_elapsed < min_seconds:
        seconds_to_sleep = (min_seconds - seconds_elapsed)

    logger.info('Sleeping An Additional {0} Seconds'.format(seconds_to_sleep))

    return seconds_to_sleep


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
    # Initially set to the base logger
    # logger = EspaLogging.get_logger('base')

    processing_location = socket.gethostname()

    base_logger.debug('processing location given as: {0}'.format(processing_location))

    if not parameters.test_for_parameter(params, 'options'):
        raise ValueError('Error missing JSON [options] record')

    base_logger.info('PARAMETERS: {0}'.format(params))
    base_logger.info('CONFIG: {0}'.format(cfg))

    # Reset these for each line
    # TODO: this might be unnecessary - carryover from espa-processing
    (server, order_id, product_id) = (None, None, None)

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
        logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)
        logger.info('Processing {}:{}'.format(order_id, product_id))

        # Update the status in the database
        if parameters.test_for_parameter(cfg, 'espa_api'):
            if cfg['espa_api'] != 'skip_api':
                server = api_interface.api_connect(cfg['espa_api'])

                base_logger.info('Attemped connection to {0}'.format(cfg['espa_api']))
                base_logger.info('API connect response: {0}'.format(server))

                if server is not None:
                    status = server.update_status(product_id, order_id,
                                                  processing_location,
                                                  'processing')
                    if not status:
                        msg = ('Failed processing API call to update_status to processing')
                        raise api_interface.APIException(msg)

                else:
                    msg = ('Failed connecting to API {0}'.format(cfg['espa_api']))
                    base_logger.critical(msg)
                    raise api_interface.APIException(msg)

        else:
            msg = ('ESPA_API is not defined!')
            base_logger.critical(msg)
            raise api_interface.APIException(msg)

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
            sleep(get_sleep_duration(cfg, start_time, dont_sleep))

            archive_log_files(order_id, product_id)

            # Everything was successful so mark the scene complete
            if server is not None:
                status = server.mark_scene_complete(product_id, order_id,
                                                    processing_location,
                                                    destination_product_file,
                                                    destination_cksum_file,
                                                    '') # sets log_file_contents to empty string ''
                if not status:
                    msg = ('Failed processing API call to mark_scene_complete')

                    raise api_interface.APIException(msg)

    except api_interface.APIException as excep:
        # This is expected when scenes have been cancelled after queueing
        base_logger.warning('Halt. API raised error: {}'.format(excep.message))

    except Exception as excep:
        # First log the exception
        base_logger.exception('Exception encountered stacktrace follows')

        # Sleep the number of seconds for minimum request duration
        sleep(get_sleep_duration(cfg, start_time, dont_sleep))

        archive_log_files(order_id, product_id)

        if server is not None:
            try:
                status = set_product_error(server,
                                           order_id,
                                           product_id,
                                           processing_location)
            except Exception:
                base_logger.exception('Exception encountered stacktrace follows')

    finally:
        # Reset back to the base logger
        # logger = EspaLogging.get_logger('base')
        pass


def cli():
    parser = argparse.ArgumentParser()

    parser.add_argument(dest="data", action="store", metavar="JSON", type=convert_json,
                        help="response from the API containing order information")

    args = parser.parse_args()

    main(**vars(args))


def main(data):


    # retrieve a dict containing processing environment configuration values
    cfg = config.config()

    # export values for the container environment
    config.export_environment_variables(cfg)

    base_logger.debug('OS ENV: {0}'.format(['{0}: {1}'.format(var, val) for var, val in os.environ.items()]))

    try:

        order_processor = partial(work, cfg)
        map(order_processor, data)

    except Exception:
        base_logger.exception('Processing failed stacktrace follows')

if __name__ == '__main__':
    cli()
