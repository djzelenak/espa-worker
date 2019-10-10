"""
This is a wrapper script to docker run for launching an espa-worker
container with the appropriate volume mounts and environment variables defined
- granted you have them in a local shell script or something along those lines.

This is mainly used for testing a new image during development and should not be used
to deploy a worker in a production capacity.
"""


import os
import sys
import commands
import argparse
import json

# environment variables required by the container
ENV = ['AUX_DIR',
       'ESPA_STORAGE',
       'ESPA_API',
       'ESPA_USER',
       'ESPA_GROUP',
       'URS_MACHINE',
       'URS_LOGIN',
       'URS_PASSWORD',
       'ASTER_GED_SERVER_NAME']


def check_env():
    """
    Make sure that the required environment variables are defined
    locally so they can be applied to the container.

    Returns:
        bool

    """
    for env in ENV:
        if not os.environ.get(env):
            print('Current environment must have {} set'.format(env))

            return False

    return True


def convert_json(in_data):
    if type(in_data) is str:
        return json.loads(in_data)
    if type(in_data) in (list, dict):
        return json.dumps(in_data)
    return None


def build_cmd(data=None, image='usgseros/espa-worker', tag='devtest', interactive=False, user=None, test=False):
    """
    Build the command line argument that calls `docker run` with the requested parameters

    Args:
        data (str): This is a formatted JSON response from the ESPA API containing all of
                    the information required to process an order.
        image (str): The name of the docker image.
        tag (str): The docker tag
        interactive (bool): You can issue this flag to run the container in the background, it
                            can then be accessed via `docker exec -it <containerID> /bin/bash`.
                            Note - you'll have to manually stop the container afterwards.
        user (str): The active user inside the container
        test (bool): If true, will run unit tests inside the container

    Returns:
        str

    """
    mounts = [
        '--mount type=bind,source=${AUX_DIR},destination=/usr/local/auxiliaries,readonly',
        '--mount type=bind,source=${ESPA_STORAGE},destination=/espa-storage/orders',
    ]

    # e.g. '--env AUX_DIR=${AUX_DIR}'
    envs = ['--env {e}=${{{e}}}'.format(e=e) for e in ENV]

    image_tag = [
        '{i}:{t}'.format(i=image, t=tag)
    ]

    # Only run the unit tests and then exit the container
    if test:
        cmd = ['docker run',
               '--rm']

        workdir = ['--workdir', '/home/espa/espa-processing']

        # cmd.extend(mounts)
        # cmd.extend(envs)
        cmd.extend(workdir)
        cmd.extend(image_tag)

        call = ['nose2 --with-coverage']
        cmd.extend(call)

        return ' '.join(cmd)

    if interactive:
        cmd = ['docker run',
               '-it',
               '--rm']

        run = ['/bin/bash']

        cmd.extend(mounts)
        cmd.extend(envs)
        if user:
            user = ['--user {}'.format(user)]
            cmd.extend(user)
        cmd.extend(image_tag)
        cmd.extend(run)

        return ' '.join(cmd)

    # only include the JSON stored in the data object if we're running non-interactively
    else:
        data = [
            # This converts the json back into a string
            "'{0}'".format(convert_json(data))
        ]

        cmd = ['docker run',
               '--rm',
               '--entrypoint',
               'python']

        run = ['/src/processing/main.py']

        cmd.extend(mounts)
        cmd.extend(envs)
        if user:
            user = ['--user {}'.format(user)]
            cmd.extend(user)
        cmd.extend(image_tag)
        cmd.extend(run)
        cmd.extend(data)

        return ' '.join(cmd)


def execute_cmd(cmd):
    """Execute a system command line

    Args:
        cmd (str): The command line to execute.

    Returns:
        output (str): The stdout and/or stderr from the executed command.

    Raises:
        Exception(message)
    """
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


def cli():
    parser = argparse.ArgumentParser()

    parser.add_argument('--image', dest='image', type=str, metavar='STR', default='usgseros/espa-worker',
                        help='Specify the name of the docker image')

    parser.add_argument('--tag', dest='tag', type=str, metavar='STR', default='devtest',
                        help='Specify the docker image tagname to use')

    parser.add_argument('--data', dest='data', type=convert_json, metavar='JSON', default=None,
                        help='The API JSON response')

    parser.add_argument('--interactive', action='store_true',
                        help='Enter container interactively')

    parser.add_argument('--user', default='espa', metavar='USER',
                        help='Enter a username for the container environment')

    parser.add_argument('--test', action='store_true',
                        help='Run unit tests inside the container and do nothing else')

    args = parser.parse_args()

    return args


def main():
    args = cli()

    if not check_env():
        sys.exit(1)

    cmd = build_cmd(**vars(args))

    output = execute_cmd(cmd)

    print(output)


if __name__ == '__main__':
    main()
