
'''
Description: Utility module for espa-processing.

License: NASA Open Source Agreement 1.3
'''

import os
import errno
import datetime
import commands
import random
import resource
from collections import defaultdict
from subprocess import check_output, CalledProcessError, check_call
from config_utils import retrieve_pigz_cfg

PIGZ_WRAPPER_FILENAME = 'pigz_wrapper.sh'


def date_from_year_doy(year, doy):
    """Returns a python date object given a year and day of year

    Args:
        year (int/str): The 4-digit year for the date.
        doy (int/str): The day of year for the date.

    Returns:
        date (date): A date repesenting the given year and day of year.
    """

    d = datetime.date(int(year), 1, 1) + datetime.timedelta(int(doy) - 1)

    if int(d.year) != int(year):
        raise Exception('doy [{}] must fall within the specified year [{}]'
                        .format(doy, year))
    else:
        return d


def peak_memory_usage(this=False):
    """ Get the peak memory usage of all children processes (Linux-specific KB->Byte implementation)

    Args:
        this (bool): Flag to instead get usage of this calling process (not including children)

    Returns:
        usage (float): Usage in bytes
    """
    who = resource.RUSAGE_CHILDREN
    if this is True:
        # NOTE: RUSAGE_BOTH also exists, but not available everywhere
        who = resource.RUSAGE_SELF
    info = resource.getrusage(who)
    usage = info.ru_maxrss * 1024
    return usage


def current_disk_usage(pathname):
    """ Get the total disk usage of a filesystem path

    Args:
        pathname (str): Relative/Absolute path to a filesystem resource

    Returns:
        usage: (int): Usage in bytes
    """
    dirs_dict = defaultdict(int)
    for root, dirs, files in os.walk(pathname, topdown=False):
        size = sum(os.path.getsize(os.path.join(root, name))
                   if os.path.exists(os.path.join(root, name)) else 0 for name in files)
        subdir_size = sum(dirs_dict[os.path.join(root, d)] for d in dirs)
        my_size = dirs_dict[root] = size + subdir_size
    return dirs_dict[pathname]


def execute_cmd(cmd):
    """Execute a system command line

    Args:
        cmd (str): The command line to execute.

    Returns:
        output (str): The stdout and/or stderr from the executed command.

    Raises:
        Exception(message)
    """

    output = ''
    (status, output) = commands.getstatusoutput(cmd)

    message = ''
    if status < 0:
        message = 'Application terminated by signal [{}]'.format(cmd)

    if status != 0:
        message = 'Application failed to execute [{}]'.format(cmd)

    if os.WEXITSTATUS(status) != 0:
        message = ('Application [{}] returned error code [{}]'
                   .format(cmd, os.WEXITSTATUS(status)))

    if len(message) > 0:
        if len(output) > 0:
            # Add the output to the exception message
            message = ' Stdout/Stderr is: '.join([message, output])
        raise Exception(message)

    return output


def get_cache_hostname(host_names):
    """Poor mans load balancer for accessing the online cache over the private
       network

    Returns:
        hostname (str): The name of the host to use.

    Raises:
        Exception(message)
    """

    host_list = list(host_names)

    def check_host_status(hostname):
        """Check to see if the host is reachable

        Args:
            hostname (str): The hostname to check.

        Returns:
            result (bool): True if the host was reachable and False if not.
        """

        cmd = 'ping -q -c 1 {}'.format(hostname)

        try:
            execute_cmd(cmd)
        except Exception:
            return False
        return True

    def get_hostname():
        """Recursivly select a host and check to see if it is available

        Returns:
            hostname (str): The name of the host to use.

        Raises:
            Exception(message)
        """

        hostname = random.choice(host_list)
        if check_host_status(hostname):
            return hostname
        else:
            for x in host_list:
                if x == hostname:
                    host_list.remove(x)
            if len(host_list) > 0:
                return get_hostname()
            else:
                raise Exception('No online cache hosts available...')

    return get_hostname()


def create_directory(directory):
    """Create the specified directory with some error checking

    Args:
        directory (str): The full path to create.

    Raises:
        Exception()
    """

    # Create/Make sure the directory exists
    try:
        os.makedirs(directory, mode=0755)
    except OSError as ose:
        if ose.errno == errno.EEXIST and os.path.isdir(directory):
            # With how we operate, as long as it is a directory, we do not
            # care about the 'already exists' error.
            pass
        else:
            raise


def create_link(src_path, link_path):
    """Create the specified link with some error checking

    Args:
        src_path (str): The location where the link will point.
        link_path (str): The location where the link will reside.

    Raises:
        Exception()
    """

    # Create/Make sure the directory exists
    try:
        os.symlink(src_path, link_path)
    except OSError as ose:
        if (ose.errno == errno.EEXIST and os.path.islink(link_path) and
                src_path == os.path.realpath(link_path)):
            pass
        else:
            raise


def tar_files(tarred_full_path, file_list, gzip=False):
    """Create a tar ball (*.tar or *.tar.gz) of the specified file(s)

    Args:
        cfg (dict): Config settings
        tarred_full_path (str): The full path to the tarred filename.
        file_list (list): The files to tar as a list.
        gzip (bool): Whether or not to gzip the tar on the fly.

    Returns:
        target (str): The full path to the tarred/gzipped filename.

    Raises:
        Exception(message)
    """

    flags = ['-cf']
    target = '%s.tar' % tarred_full_path

    # If zipping was chosen, change the flags and the target name
    if gzip:
        # Look up the configured level of multithreading
        num_threads = retrieve_pigz_cfg()

        # Create and use a pigz wrapper script.  tar --use-compress-program
        # doesn't allow parameters
        with open(PIGZ_WRAPPER_FILENAME, 'w') as pigz_wrapper_file:
            pigz_wrapper_file.write("#!/bin/bash\n")
            pigz_wrapper_file.write("pigz -p " + num_threads + '\n')
        pigz_wrapper_file.close()
        os.chmod(PIGZ_WRAPPER_FILENAME, 0755)

        flags = ['--use-compress-program=./' + PIGZ_WRAPPER_FILENAME] + ['-cf']
        target = '%s.tar.gz' % tarred_full_path

    cmd = ['tar'] + flags + [target]
    cmd.extend(file_list)

    output = ''
    try:
        output = check_output(cmd)
    except Exception:
        msg = "Error encountered tar'ing file(s): Stdout/Stderr:"
        if len(output) > 0:
            msg = ' '.join([msg, output])
        else:
            msg = ' '.join([msg, 'NO STDOUT/STDERR'])
        # Raise and retain the callstack
        raise Exception(msg)

    # If zipping was chosen, clean up the pigz wrapper script 
    if gzip:
        os.unlink(PIGZ_WRAPPER_FILENAME)

    return target


def gzip_files(file_list):
    """Create a gzip for each of the specified file(s).

    Args:
        cfg (dict): Config settings
        file_list (list): The files to tar as a list.

    Raises:
        Exception(message)
    """
    # Look up the configured level of multithreading
    num_threads = retrieve_pigz_cfg()

    # Force the gzip file to overwrite any previously existing attempt
    cmd = ['pigz', '-p ' + num_threads, '--force']
    cmd.extend(file_list)
    cmd = ' '.join(cmd)

    output = ''
    try:
        output = execute_cmd(cmd)
    except Exception:
        msg = 'Error encountered compressing file(s): Stdout/Stderr:'
        if len(output) > 0:
            msg = ' '.join([msg, output])
        else:
            msg = ' '.join([msg, 'NO STDOUT/STDERR'])
        # Raise and retain the callstack
        raise Exception(msg)


def str2bool(val):
    """Convert string to boolean value
    """
    try:
        if val.lower() in ['false', 'off', '0']:
            return False
        else:
            return True

    except AttributeError:
        raise TypeError('value {0} was not a string'.format(type(val)))
