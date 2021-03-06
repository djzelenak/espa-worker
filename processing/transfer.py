"""
Description: Provides routines for transferring files.

License: NASA Open Source Agreement 1.3
"""

import os
import shutil
import ftplib
import urllib2
import requests
from requests.adapters import HTTPAdapter
import random
from time import sleep

import settings
import utilities
from logging_tools import EspaLogging


def copy_files_to_directory(source_files, destination_directory):
    """
    Description:
      Use unix 'cp' to copy files from one place to another on the localhost.
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    if isinstance(source_files, list):
        for source_file in source_files:
            cmd = ' '.join(['cp', source_file, destination_directory])

            # Transfer the data and raise any errors
            output = ''
            try:
                output = utilities.execute_cmd(cmd)
            except Exception:
                logger.error("Failed to copy file")
                raise
            finally:
                if len(output) > 0:
                    logger.info(output)

    logger.info("Transfer complete - CP")


def move_files_to_directory(source_files, destination_directory):
    """
    Description:
      Move files from one place to another on the localhost.
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    if isinstance(source_files, str):
        filename = os.path.basename(source_files)

        new_name = os.path.join(destination_directory, filename)

        os.rename(source_files, new_name)

    elif isinstance(source_files, list):
        for source_file in source_files:
            filename = os.path.basename(source_file)

            new_name = os.path.join(destination_directory, filename)

            os.rename(source_file, new_name)

    logger.info("Transfer complete - MOVE")


def remote_copy_file_to_file(source_host, source_file, destination_file):
    """
    Description:
      Use unix 'cp' to copy a file from one place to another on a remote
      machine using ssh.
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    cmd = ' '.join(['ssh', '-q', '-o', 'StrictHostKeyChecking=no',
                    source_host, 'cp', source_file, destination_file])

    # Transfer the data and raise any errors
    output = ''
    try:
        output = utilities.execute_cmd(cmd)
    except Exception:
        logger.error("Failed to copy file")
        raise
    finally:
        if len(output) > 0:
            logger.info(output)

    logger.info("Transfer complete - SSH-CP")


def ftp_from_remote_location(username, pword, host, remotefile, localfile):
    """
    Description:
      Transfers files from a remote location to the local machine using ftplib.

    Parameters:
      username = Username for ftp account
      pword = Password for ftp account
      host = The ftp server host
      remotefile = The file to transfer
      localfile = Full path to where the local file should be created.
                  (Parent directories must exist)

    Returns: None

    Errors: Raises Exception() in the event of error
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    # Make sure the src_file is absolute, otherwise ftp will choke
    if not remotefile.startswith('/'):
        remotefile = ''.join(['/', remotefile])

    password = urllib2.unquote(pword)

    url = 'ftp://%s/%s' % (host, remotefile)

    logger.info("Transferring file from %s to %s" % (url, localfile))
    ftp = None
    try:
        with open(localfile, 'wb') as loc_file:
            def callback(data):
                loc_file.write(data)

            ftp = ftplib.FTP(host, timeout=60)
            ftp.login(user=username, passwd=password)
            ftp.set_debuglevel(0)
            ftp.retrbinary(' '.join(['RETR', remotefile]), callback)

    finally:
        if ftp:
            ftp.quit()

    logger.info("Transfer complete - FTP")


def ftp_to_remote_location(username, pword, localfile, host, remotefile):
    """
    Description:
      Transfers files from the local machine to a remote location using ftplib.

    Parameters:
      username = Username for ftp account
      pword = Password for ftp account
      host = The ftp server host
      remotefile = Full path of where to store the file
                   (Directories must exist)
      localfile = Full path of file to transfer out

    Returns: None

    Errors: Raises Exception() in the event of error
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    # Make sure the src_file is absolute, otherwise ftp will choke
    if not remotefile.startswith('/'):
        remotefile = ''.join(['/', remotefile])

    password = urllib2.unquote(pword)

    logger.info("Transferring file from %s to %s"
                % (localfile, 'ftp://%s/%s' % (host, remotefile)))

    ftp = None

    try:
        ftp = ftplib.FTP(host, user=username, passwd=password, timeout=60)
        with open(localfile, 'rb') as tmp_fd:
            ftp.storbinary(' '.join(['STOR', remotefile]), tmp_fd, 1024)
    finally:
        if ftp:
            ftp.quit()

    logger.info("Transfer complete - FTP")


def scp_transfer_file(source_host, source_file,
                      destination_host, destination_file):
    """
    Description:
      Using SCP transfer a file from a source location to a destination
      location.

    Note:
      - It is assumed ssh has been setup for access between the localhost
        and destination system
      - If wild cards are to be used with the source, then the destination
        file must be a directory.  ***No checking is performed in this code***
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    if source_host == destination_host:
        msg = "source and destination host match unable to scp"
        logger.error(msg)
        raise Exception(msg)

    cmd = ['scp', '-q', '-o', 'StrictHostKeyChecking=no', '-C']

    # Build the source portion of the command
    # Single quote the source to allow for wild cards
    if source_host == 'localhost':
        cmd.append(source_file)
    else:
        cmd.append("'%s:%s'" % (source_host, source_file))

    # Build the destination portion of the command
    if destination_host == 'localhost':
        cmd.append(destination_file)
    else:
        cmd.append('%s:%s' % (destination_host, destination_file))

    cmd = ' '.join(cmd)

    # Transfer the data and raise any errors
    output = ''
    try:
        output = utilities.execute_cmd(cmd)
    except Exception:
        if len(output) > 0:
            logger.info(output)
        logger.error("Failed to transfer data")
        raise

    logger.info("Transfer complete - SCP")


def scp_transfer_directory(source_host, source_directory,
                           destination_host, destination_directory):
    """
    Description:
      Using SCP transfer a directory from a source location to a destination
      location.

    Note:
      - It is assumed ssh has been setup for access between the localhost
        and destination system
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    if source_host == destination_host:
        msg = "source and destination host match unable to scp"
        logger.error(msg)
        raise Exception(msg)

    cmd = ['scp', '-r', '-q', '-o', 'StrictHostKeyChecking=no', '-C']

    # Build the source portion of the command
    # Single quote the source to allow for wild cards
    if source_host == 'localhost':
        cmd.append(source_directory)
    else:
        cmd.append("'%s:%s'" % (source_host, source_directory))

    # Build the destination portion of the command
    if destination_host == 'localhost':
        cmd.append(destination_directory)
    else:
        cmd.append('%s:%s' % (destination_host, destination_directory))

    cmd = ' '.join(cmd)

    # Transfer the data and raise any errors
    output = ''
    try:
        output = utilities.execute_cmd(cmd)
    except Exception:
        if len(output) > 0:
            logger.info(output)
        logger.error("Failed to transfer data")
        raise

    logger.info("Transfer complete - SCP")


def http_transfer_file(download_url, destination_file):
    """
    Description:
      Using http transfer a file from a source location to a destination
      file on the localhost.
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)
    logger.info(download_url)

    session = requests.Session()
    session.mount('http://', HTTPAdapter(max_retries=1))
    session.mount('https://', HTTPAdapter(max_retries=1))

    req = None
    try:
        # Use .netrc credentials by default since no auth= specified
        # we'll use this method for now to get through to the lp daac
        req = session.get(url=download_url, timeout=300.0)

        if not req.ok:
            logger.error("Transfer Failed - HTTP")
            req.raise_for_status()

        with open(destination_file, 'wb') as local_fd:
            local_fd.write(req.content)

    except Exception:
        logger.exception("Transfer Issue - HTTP - {0}".format(download_url))
        msg = "Connection timed out"

        # Sleep randomly from 1 to 10 minutes before raising the exception
        sleep_seconds = int(random.random() * 540) + 60

        logger.debug('Transfer Issue - Sleeping for {} seconds'.format(sleep_seconds))

        sleep(sleep_seconds)

        raise Exception(msg)

    finally:
        if req is not None:
            req.close()

    logger.info("Transfer Complete - HTTP")


def download_file_url(download_url, destination_file):
    """
    Description:
        Using a URL download the specified file to the destination.
    """

    download_url = urllib2.unquote(download_url)

    if download_url.startswith('http'):
        http_transfer_file(download_url, destination_file)
    elif download_url.startswith('file://'):
        source_file = download_url.replace('file://', '')
        transfer_file('localhost', source_file, 'localhost', destination_file)
    else:
        raise Exception("Transfer Failed -"
                        " Unknown URL transport protocol [%s]"
                        % download_url)


def transfer_file(source_host, source_file,
                  destination_host, destination_file,
                  source_username=None, source_pw=None,
                  destination_username=None, destination_pw=None):
    """
    Description:
      Using cp/FTP/SCP transfer a file from a source location to a destination
      location.

    Notes:
      We are not doing anything significant here other then some logic and
      fallback to SCP if FTP fails.
    """

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    logger.info("Transfering [%s:%s] to [%s:%s]"
                % (source_host, source_file,
                   destination_host, destination_file))

    # If both source and destination are localhost we can just copy the data
    if source_host == 'localhost' and destination_host == 'localhost':
        shutil.copyfile(source_file, destination_file)
        return

    # If both source and destination hosts are the same, we can use ssh to copy
    # the files locally on the remote host
    if source_host == destination_host:
        remote_copy_file_to_file(source_host, source_file, destination_file)
        return

    # Try FTP first before SCP if usernames and passwords are provided
    if source_username is not None and source_pw is not None:
        try:
            ftp_from_remote_location(source_username, source_pw, source_host,
                                     source_file, destination_file)
            return
        except Exception as excep:
            logger.warning("FTP failures will attempt transfer using SCP")
            logger.warning("FTP Errors: %s" % str(excep))

    elif destination_username is not None and destination_pw is not None:
        try:
            ftp_to_remote_location(destination_username, destination_pw,
                                   source_file, destination_host,
                                   destination_file)
            return
        except Exception as excep:
            logger.warning("FTP failures will attempt transfer using SCP")
            logger.warning("FTP Errors: %s" % str(excep))

    # As a last resort try SCP
    scp_transfer_file(source_host, source_file,
                      destination_host, destination_file)
