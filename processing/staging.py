
'''
Description: Provides routines for creating order directories and staging data
             to them.

License: NASA Open Source Agreement 1.3
'''

import os
import sys
import glob

import settings
import utilities
from logging_tools import EspaLogging
from environment import Environment, DISTRIBUTION_METHOD_LOCAL
import transfer
from config_utils import retrieve_pigz_cfg

PROC_CFG_FILENAME = 'processing.conf'


def untar_data(source_file, destination_directory):
    '''
    Description:
        Using tar extract the file contents into a destination directory.

    Notes:
        Works with '*.tar.gz' and '*.tar' files.
    '''

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    # Look up the configured level of multithreading
    num_threads_str = retrieve_pigz_cfg(PROC_CFG_FILENAME)

    # If both source and destination are localhost we can just copy the data
    cmd = ' '.join(['unpigz -p ', num_threads_str, ' < ', source_file,
                        ' | tar', '--directory', destination_directory,
                        ' -xv'])
    logger.info("Unpacking [%s] to [%s]"
                % (source_file, destination_directory))

    # Unpack the data and raise any errors
    output = ''
    try:
        output = utilities.execute_cmd(cmd)
    except Exception:
        logger.exception("Failed to unpack data")
        raise
    finally:
        if len(output) > 0:
            logger.info(output)


def stage_local_statistics_data(output_dir, work_dir, order_id):
    '''
    Description:
        Stages the statistics using a local directory path.
    '''

    cache_dir = os.path.join(output_dir, settings.ESPA_LOCAL_CACHE_DIRECTORY)
    cache_dir = os.path.join(cache_dir, order_id)
    cache_dir = os.path.join(cache_dir, 'stats')
    cache_files = os.path.join(cache_dir, '*')

    stats_files = glob.glob(cache_files)

    transfer.copy_files_to_directory(stats_files, work_dir)


def stage_remote_statistics_data(stage_dir, work_dir, order_id):
    '''
    Description:
        Stages the statistics using scp from a remote location.
    '''

    env = Environment()

    cache_host = utilities.get_cache_hostname(env.get_cache_host_list())
    cache_dir = os.path.join(settings.ESPA_REMOTE_CACHE_DIRECTORY, order_id)
    cache_dir = os.path.join(cache_dir, 'stats')

    # Transfer the directory using scp
    transfer.scp_transfer_directory(cache_host, cache_dir,
                                    'localhost', stage_dir)

    # Move the staged data to the work directory
    stats_files = glob.glob(os.path.join(stage_dir, 'stats/*'))

    transfer.move_files_to_directory(stats_files, work_dir)


def stage_statistics_data(output_dir, stage_dir, work_dir, parms):
    '''
    Description:
        Stages the statistics data, either by using scp from a remote location,
        or by just copying them from a local disk path.
    '''

    env = Environment()

    distribution_method = env.get_distribution_method()

    order_id = parms['orderid']

    if distribution_method == DISTRIBUTION_METHOD_LOCAL:
        stage_local_statistics_data(output_dir, work_dir, order_id)

    else:
        stage_remote_statistics_data(stage_dir, work_dir, order_id)
