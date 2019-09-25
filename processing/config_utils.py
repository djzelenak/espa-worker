

import os
from ConfigParser import ConfigParser
import config
import settings


cfg = config.config()

def get_cfg_file_path(filename):
    """Build the full path to the config file

    Args:
        filename (str): The name of the file to append to the full path.

    Raises:
        Exception(message)
    """

    # Use the users home directory as the base source directory for
    # configuration
    if 'HOME' not in os.environ:
        raise Exception('[HOME] not found in environment')
    home_dir = os.environ.get('HOME')

    # Build the full path to the configuration file
    config_path = os.path.join(home_dir, '.usgs', 'espa', filename)

    return config_path


def retrieve_cfg(cfg_filename, default=None):
    """Retrieve the ESPA configuration values

    Returns:
        cfg (ConfigParser): Configuration for ESPA.

    Raises:
        Exception(message)
    """

    # Build the full path to the configuration file
    config_path = get_cfg_file_path(cfg_filename)

    if not os.path.isfile(config_path):
        raise Exception('Missing configuration file [{}]'.format(config_path))

    # Create the object and load the configuration
    cfg = ConfigParser(default)
    cfg.read(config_path)

    return cfg

def retrieve_pigz_cfg(key='pigz_num_threads'):
    """Retrieve and verify the pigz configuration

    Returns:
        num_threads_str <str>: pigz string for number of threads 
    """

    default = {'pigz_num_threads' : str(settings.PIGZ_MULTITHREADING)}

    num_threads_str = cfg.get(key)

    try:
        num_threads = int(num_threads_str)
        if num_threads <= 0:
            num_threads_str = str(settings.PIGZ_MULTITHREADING)
    except ValueError:
            num_threads_str = str(settings.PIGZ_MULTITHREADING)

    return num_threads_str

