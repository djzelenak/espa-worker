
'''
Description: Provides the implementation for creating the core directories
             required for the processing of a product request.

License: NASA Open Source Agreement 1.3
'''


import os


import utilities
from environment import Environment, DISTRIBUTION_METHOD_LOCAL


def __create_local_directory(base_path, directory_name):
    '''
    Description:
        Creates a local directory under the base path.

    Note: "local" in this case means a standard directory.

    Returns:
        string: The fullpath to the directory created.

    Parameters:
        string: base_path - The location where to create the directory.
        string: directory_name - The name of the directory to be created.
    '''

    full_path = os.path.join(base_path, directory_name)

    utilities.create_directory(full_path)

    return full_path


def __create_linked_directory(base_path, linked_path, link_name):
    '''
    Description:
        Creates a link to the linked path

    Note: "linked" in this case means a symbolic link to the linked path.

    Returns:
        string: The fullpath to the link.

    Parameters:
        string: base_path - The location where to create the directory.
        string: linked_path - The location where the link will point.
        string: link_name - The name of the link to be created.
    '''

    full_path = os.path.join(base_path, link_name)

    utilities.create_link(linked_path, full_path)

    return full_path


# ============================================================================
# API Implementation
# ============================================================================

def create_stage_directory(base_path):
    '''
    Description:
        Creates a local stage directory.

    Note: "local" in this case means a standard directory.

    Returns:
        string: The fullpath to the "stage" directory.

    Parameters:
        string: base_path - The location where to create the directory.
    '''

    return __create_local_directory(base_path, 'stage')


def create_work_directory(base_path):
    '''
    Description:
        Creates a local work directory.

    Note: "local" in this case means a standard directory.

    Returns:
        string: The fullpath to the "work" directory.

    Parameters:
        string: base_path - The location where to create the directory.
    '''

    return __create_local_directory(base_path, 'work')


def create_output_directory(base_path):
    '''
    Description:
        Creates either a symbolic link to the online cache or a local
        directory.

    Note: With the local distribution method, a symbolic link is created so
          that we can just tar.gz the product and place the checksum directly
          on the product (online) cache.
          With the remote distribution method, we just create a directory to
          hold the tar.gz and checksum before using ftp/scp to transfer the
          product over the network.

    Returns:
        string: The fullpath to the "output" link or directory.

    Parameters:
        base_path - The location where to create the "output" link or
                    directory under.
    '''

    env = Environment()

    distribution_method = env.get_distribution_method()
    name = 'output'

    if distribution_method == DISTRIBUTION_METHOD_LOCAL:
        linked_path = env.get_distribution_directory()
        # return __create_linked_directory(base_path, linked_path, name)
        # Due to a concern with accidental removal of all of the online-cache
        # during a disk failure.  Assumed to be performed by hadoop.  The
        # link is being removed from the hadoop controlled directories.  So
        # we are not creating the link and using the linked_path as the value
        # of the internal output_dir  variable used by the rest of the code.
        # Until a later release where distribution of products has gone
        # through a severely needed re-implementation.
        return linked_path
    else:
        return __create_local_directory(base_path, name)
