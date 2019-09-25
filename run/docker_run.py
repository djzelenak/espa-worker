
import os
import sys
import commands
import argparse
import json

def check_env():

    if not os.environ.get('AUX_DIR'):
        print('ENV must have AUX_DIR set')
        sys.exit(1)

    if not os.environ.get('ESPA_STORAGE'):
        print('ENV must have ESPA_STORAGE set')
        sys.exit(1)


def convert_json(in_data):
    if type(in_data) is str:
        return json.loads(in_data)
    if type(in_data) in (list, dict):
        return json.dumps(in_data)
    return None


def build_cmd(data=None, image='usgseros/espa-worker', tag='devtest', interactive=False, user='espa'):
    """
    Build the command line argument that calls docker run with the requested parameters

    Args:
        data (str):
        image (str):
        tag (str):
        interactive (bool):

    Returns:
        str

    """
    mounts = [
        '--mount type=bind,source=${AUX_DIR},destination=/usr/local/auxiliaries,readonly',
        '--mount type=bind,source=${ESPA_STORAGE},destination=/espa-storage/orders',
    ]

    envs = [
        '--env ESPA_API=${ESPA_API}',
        '--env ASTER_GED_SERVER_NAME=${ASTER_GED_SERVER_NAME}',
        '--env URS_MACHINE=${URS_MACHINE}',
        '--env URS_LOGIN=${URS_LOGIN}',
        '--env URS_PASSWORD=${URS_PASSWORD}'
    ]

    image_tag = [
        '{0}:{1}'.format(image, tag),
    ]

    if interactive:
        cmd = ['docker run',
               '-it',
               '--rm']
               
    else:
        data = [
            "'{0}'".format(convert_json(data))  # This converts the json back into a string
        ]

        cmd = ['docker run',
               '--rm',
               '--entrypoint',
               'python']

        run = ['/src/processing/main.py']

#    if user:
#        user = ['--user',
#                user]
#
#        cmd.extend(user)

    cmd.extend(mounts)
    cmd.extend(envs)
    cmd.extend(image_tag)
#    cmd.extend(run)

    if not interactive and data is not None:
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

    args = parser.parse_args()

    return args


def main():
    args = cli()

    check_env()

    cmd = build_cmd(**vars(args))

    output = execute_cmd(cmd)

    print(output)


if __name__ == '__main__':
    main()
