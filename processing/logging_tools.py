
'''
Description: Provides the logging tools.

License: NASA Open Source Agreement 1.3
'''


import os
import errno
import logging
import logging.config
import settings
import shutil
import sys

from environment import Environment

WORKER_LOG_PREFIX = 'espa-worker'
WORKER_LOG_FILENAME = '.'.join([WORKER_LOG_PREFIX, 'log'])
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class EspaLoggerException(Exception):
    """An exception just for the EspaLogging class
    """
    pass


class EspaLogging(object):
    my_config = None
    basic_logger_configured = False

    @classmethod
    def check_logger_configured(cls, logger_name):
        """Checks to see if a logger has been configured

        Args:
            logger_name (str): The name of the logger to use.

        Raises:
            EspaLoggerException
        """

        logger_name = logger_name.lower()

        if logger_name not in cls.my_config['loggers']:
            raise EspaLoggerException('Reporter [{0}] is not configured'
                                      .format(logger_name))

    @classmethod
    def configure_base_logger(cls,
                              filename='/tmp/espa-base-logger.log',
                              format=('%(asctime)s.%(msecs)03d %(process)d'
                                      ' %(levelname)-8s'
                                      ' %(filename)s:%(lineno)d:%(funcName)s'
                                      ' -- %(message)s'),
                              datefmt='%Y-%m-%d %H:%M:%S',
                              level=logging.DEBUG):
        """Configures the base logger

        Args:
            filename (str): The name of the file to contain the log.
            format (str): The formatting to use withiin the logfile.
            date (str): The format for the date strings.
            level (flag): The base level of errors to log to the file.
        """

        if not cls.basic_logger_configured:
            # Setup a base logger so that we can use it for errors
            logging.basicConfig(filename=filename, format=format,
                                datefmt=datefmt, level=level)

            cls.basic_logger_configured = True

    @classmethod
    def configure(cls, logger_name, order=None, product=None, debug=False):
        """Adds a configured logger python execution instance

        Adds a configured logger from settings to the logging configured for
        this python execution instance.

        Args:
            logger_name (str): The name of the logger to define/configure.
            order (str): The Order ID to use for log name formatting.
            product (str): The Product ID to use for log name formatting.
            debug (bool): Should debug level log messages be reported in
                          the log file.

        Raises:
            EspaLoggerException
        """

        logger_name = logger_name.lower()

        if logger_name not in settings.LOGGER_CONFIG['loggers']:
            raise EspaLoggerException('Reporter [{0}] is not a configured'
                                      ' logger in settings.py'
                                      .format(logger_name))

        if (logger_name == 'espa.processing' and
                (order is None or product is None)):
            msg = ("Reporter [espa.processing] is required to have an order"
                   " and product for proper configuration of the loggers"
                   " filename")
            raise EspaLoggerException(msg)

        # Basic initialization for the configuration
        if cls.my_config is None:
            cls.my_config = dict()
            cls.my_config['version'] = settings.LOGGER_CONFIG['version']
            cls.my_config['disable_existing_loggers'] = \
                settings.LOGGER_CONFIG['disable_existing_loggers']
            cls.my_config['loggers'] = dict()
            cls.my_config['handlers'] = dict()
            cls.my_config['formatters'] = dict()

            # Setup a basic logger so that we can use it for errors
            cls.configure_base_logger()

        # Configure the logger
        if logger_name not in cls.my_config['loggers']:

            # For shorter access to them
            loggers = settings.LOGGER_CONFIG['loggers']
            handlers = settings.LOGGER_CONFIG['handlers']
            formatters = settings.LOGGER_CONFIG['formatters']

            # Copy the loggers dict for the logger we want
            cls.my_config['loggers'][logger_name] = \
                loggers[logger_name].copy()

            # Turn on debug level logging if requested
            if debug:
                cls.my_config['loggers'][logger_name]['level'] = 'DEBUG'

            # Copy the handlers dict for the handlers we want
            for handler in loggers[logger_name]['handlers']:
                cls.my_config['handlers'][handler] = handlers[handler].copy()

                # Copy the formatter dict for the formatters we want
                formatter_name = handlers[handler]['formatter']
                cls.my_config['formatters'][formatter_name] = \
                    formatters[formatter_name].copy()

            if (logger_name == 'espa.processing' and
                    order is not None and product is not None):
                # Get the name of the handler to be modified
                handler_name = logger_name

                # Get the handler
                config_handler = cls.my_config['handlers'][handler_name]

                # Override the logger path and name
                prefix = '-'.join(['espa', order, product])
                config_handler['filename'] = '.'.join([prefix, 'log'])

            # Now configure the python logging module
            logging.config.dictConfig(cls.my_config)

    @classmethod
    def get_filename(cls, logger_name):
        """Returns the full path and name of the logfile

        Args:
            logger_name (str): The name of the logger to get the filename for.

        Raises:
            EspaLoggerException
        """

        logger_name = logger_name.lower()
        cls.check_logger_configured(logger_name)

        handler = cls.my_config['handlers'][logger_name]

        if handler['class'] != 'logging.FileHandler':
            raise EspaLoggerException('Reporter [{0}] is not a file logger'
                                      .format(logger_name))

        return handler['filename']

    @classmethod
    def delete_logger_file(cls, logger_name):
        """Deletes the log file associated with the specified logger

        Args:
            logger_name (str): The name of the logger to delete the logfile
                               for.

        Raises:
            EspaLoggerException
        """

        logger_name = logger_name.lower()
        cls.check_logger_configured(logger_name)

        handler = cls.my_config['handlers'][logger_name]

        if handler['class'] != 'logging.FileHandler':
            raise EspaLoggerException('Reporter [{0}] is not a file logger'
                                      .format(logger_name))

        filename = handler['filename']

        if os.path.exists(filename):
            try:
                os.unlink(filename)
            except Exception as e:
                raise EspaLoggerException(str(e))

    @classmethod
    def read_logger_file(cls, logger_name):
        """Returns the contents of the logfile for the specified logger

        Reads and returns the contents of the file associated with the
        specified logger.

        Args:
            logger_name (str): The name of the logger to read the logfile for.

        Raises:
            EspaLoggerException
        """

        logger_name = logger_name.lower()
        cls.check_logger_configured(logger_name)

        handler = cls.my_config['handlers'][logger_name]

        if handler['class'] != 'logging.FileHandler':
            raise EspaLoggerException('Reporter [{0}] is not a file logger'
                                      .format(logger_name))

        filename = handler['filename']

        file_data = ''
        if os.path.exists(filename):
            with open(filename, "r") as file_fd:
                file_data = file_fd.read()

        return file_data

    @classmethod
    def get_logger(cls, logger_name):
        """Returns a configured logger

        Checks to see if the logger has been configured and returns the logger
        or generates an exception.

        Args:
            logger_name (str): The name of the logger to get.

        Raises:
            EspaLoggerException
        """

        logger_name = logger_name.lower()
        if logger_name != 'base':
            cls.check_logger_configured(logger_name)

        return logging.getLogger(logger_name)


class LevelFilter(logging.Filter):
    def __init__(self, low, high):
        self._low = low
        self._high = high
        logging.Filter.__init__(self)

    def filter(self, record):
        if self._low <= record.levelno <= self._high:
            return True
        return False

def get_stdout_handler():
    # Return StreamHandler that logs to sys.stdout
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)
    stdout_handler.addFilter(LevelFilter(10, 20))
    return stdout_handler

def get_stderr_handler():
    # Return StreamHandler that logs to sys.stderr
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    stderr_handler.addFilter(LevelFilter(30, 50))
    return stderr_handler

def get_base_logger():
    EspaLogging.configure_base_logger(filename=WORKER_LOG_FILENAME)
    # Initially set to the base logger
    base_logger = EspaLogging.get_logger('base')
    base_logger.addHandler(get_stdout_handler())
    base_logger.addHandler(get_stderr_handler())
    return base_logger

def archive_log_files(order_id, product_id):
    """Archive the log files for the current job
    """
    try:
        logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    except Exception:
        logger = get_base_logger()

    try:
        # Determine the destination path for the logs
        output_dir = Environment().get_distribution_directory()
        destination_path = os.path.join(output_dir, 'logs', order_id)
        # Create the path
        try:
            os.makedirs(destination_path)  # use the default mode 0777
            os.chmod(destination_path, 0755)  # use chmod to explicitly set the desired mode
        except OSError as ose:
            if ose.errno == errno.EEXIST and os.path.isdir(destination_path):
                # With how we operate, as long as it is a directory, we do not
                # care about the 'already exists' error.
                pass
            else:
                raise




        # Job log file
        logfile_path = EspaLogging.get_filename(settings.PROCESSING_LOGGER)
        full_logfile_path = os.path.abspath(logfile_path)
        log_name = os.path.basename(full_logfile_path)
        # Determine full destination
        destination_job_file = os.path.join(destination_path, log_name)
        # Copy it
        shutil.copyfile(full_logfile_path, destination_job_file)

        # Mapper log file
        full_logfile_path = os.path.abspath(WORKER_LOG_FILENAME)
        final_log_name = '-'.join([WORKER_LOG_PREFIX, order_id, product_id])
        final_log_name = '.'.join([final_log_name, 'log'])
        # Determine full destination
        destination_mapper_file = os.path.join(destination_path, final_log_name)
        # Copy it
        shutil.copyfile(full_logfile_path, destination_mapper_file)

        return destination_path, destination_job_file, destination_mapper_file

    except Exception:
        # We don't care because we are at the end of processing
        # And if we are on the successful path, we don't care either
        logger.exception('Exception encountered and follows')
