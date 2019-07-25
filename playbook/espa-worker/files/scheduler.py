
import os
import commands
import schedule


HOME = os.environ.get('HOME')


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
        message = 'Application terminated by signal [{0}]'.format(cmd)

    if status != 0:
        message = 'Application failed to execute [{0}]'.format(cmd)

    if os.WEXITSTATUS(status) != 0:
        message = ('Application [{0}] returned error code [{1}]'
                   .format(cmd, os.WEXITSTATUS(status)))

    if len(message) > 0:
        if len(output) > 0:
            # Add the output to the exception message
            message = ' Stdout/Stderr is: '.join([message, output])
        raise Exception(message)

    return output


def ondemand_job(priority='all', limit=10, product_types='landsat'):
    """
    A wrapper function for calling the ondemand_mapper function
    from espa-processing

    Args:
        priority (str): The processing priority, default is 'all'
        limit (int): Processing limit, default is 10
        product_types (str): The product type to process

    Returns:
        None

    """
    script_name = 'ondemand_mapper.py'
    data_path = os.path.join(HOME, 'espa-site', 'processing')
    script_path = os.path.join(data_path, script_name)

    cmd = [
        '/usr/bin/python',
        script_path,
        '--priority', priority,
        '--limit', limit,
        '--product-types', product_types
    ]
    cmd = ' '.join(cmd)
    execute_cmd(cmd)


def order_disposition_job():
    """
    A wrapper function to call the orderdisposition_cron script

    """
    script_name = 'order_disposition_cron.py'
    data_path = os.path.join(HOME, 'espa-site', 'scheduling')
    script_path = os.path.join(data_path, script_name)

    cmd = [
        '/usr/bin/python',
        script_path
    ]
    cmd = ' '.join(cmd)
    execute_cmd(cmd)


def main():

    schedule.every(2).minutes.do(ondemand_job, 'all', 10, 'landsat')
    schedule.every(2).minutes.do(ondemand_job, 'all', 10, 'modis')
    schedule.every(2).minutes.do(ondemand_job, 'all', 10, 'viirs')
    schedule.every(2).minutes.do(ondemand_job, 'all', 10, 'plot')
    schedule.every(7).minutes.do(order_disposition_job)

    while True:
        schedule.run_pending()


if __name__ == '__main__':
    main()
