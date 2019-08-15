
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


def build_cmd(data, image='usgseros/espa-worker', tag='latest'):
    print(type(data))
    print(data)
    new_data = convert_json(data)
    print(type(new_data))
    print(new_data)

    cmd = [
        'docker run',
        '-it',
        '--rm',
        '--mount type=bind,source=${AUX_DIR},destination=/usr/local/auxiliaries,readonly',
        '--mount type=bind,source=${ESPA_STORAGE},destination=/espa-storage/orders',
        '{0}:{1}'.format(image, tag),
        new_data # This converts the json back into a string
    ]

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

    parser.add_argument('--tag', dest='tag', type=str, metavar='STR', default='latest',
                        help='Specify the docker image tagname to use')

    parser.add_argument('--data', dest='data', type=convert_json, metavar='JSON',
                        help='The API JSON response')

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
