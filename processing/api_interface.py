import requests
import logging
import config

from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_fixed

from logging_tools import get_base_logger

logger = get_base_logger()

logging.getLogger('requests').setLevel(logging.WARNING)
cfg = config.config()

class APIException(Exception):
    """
    Handle exceptions thrown by the APIServer class
    """
    pass


class APIServer(object):
    """
    Provide a more straightforward way of handling API calls
    """
    def __init__(self, base_url):
        logger.debug("initializing APIServer object with url: {}".format(base_url))
        self.base = base_url
        
        # raise exception if cannot reach api
        self.test_connection()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(10), reraise=True)
    def request(self, method, resource=None, status=None, **kwargs):
        """
        Make a call into the API

        Args:
            method: HTTP method to use
            resource: API resource to touch

        Returns: response and status code

        """
        valid_methods = ('get', 'put', 'delete', 'head', 'options', 'post')

        if method not in valid_methods:
            raise APIException('Invalid method {}'.format(method))

        if resource and resource[0] == '/':
            url = '{}{}'.format(self.base, resource)
        elif resource:
            url = '{}/{}'.format(self.base, resource)
        else:
            url = self.base

        try:
            resp = requests.request(method, url, **kwargs)
        except requests.RequestException as e:
            raise APIException(e)

        if status and resp.status_code != status:
            msg = 'Received unexpected status code: {}\n for URL: {}'.format(code, url)
            logger.error(msg)
            raise Exception(msg)

        return resp.json(), resp.status_code

    def update_status(self, prod_id, order_id, proc_loc, val):
        """
        Update the status of a product.

        Args:
            prod_id: scene name
            order_id: order id
            proc_loc: processing location
            val: status value

        Returns:
        """
        url = '/update_status'

        data_dict = {'name': prod_id,
                     'orderid': order_id,
                     'processing_loc': proc_loc,
                     'status': val}

        resp, status = self.request('post', url, json=data_dict, status=200)

        return resp

    def mark_scene_complete(self, prod_id, order_id, proc_loc, dest_prodfile,
                            dest_cksumfile, val):
        """
        Marks products as complete

        Args:
            prod_id: scene name
            order_id: order id
            proc_loc: processing location
            dest_prodfile: final tarball location
            dest_cksumfile: final checksum location
            val: log file information

        Returns:
        """
        url = '/mark_product_complete'

        data_dict = {'name': prod_id,
                     'orderid': order_id,
                     'processing_loc': proc_loc,
                     'completed_file_location': dest_prodfile,
                     'cksum_file_location': dest_cksumfile,
                     'log_file_contents': val}

        resp, status = self.request('post', url, json=data_dict, status=200)

        return resp

    def set_scene_error(self, prod_id, order_id, proc_loc, log):
        """
        Set a scene to error status

        Args:
            prod_id: scene name
            order_id: order id
            proc_loc: processing location
            log: log file contents

        Returns:
        """
        url = '/set_product_error'
        data_dict = {'name': prod_id,
                     'orderid': order_id,
                     'processing_loc': proc_loc,
                     'error': log}

        resp, status = self.request('post', url, json=data_dict, status=200)

        return resp

    def test_connection(self):
        """
        Tests the base URL for the class
        Returns: True if 200 status received, else False
        """
        logger.debug("testing ESPA API connection...")
        # self.request will raise an exception on a non-200 status for the request
        resp, status = self.request('get', status=200)
        logger.debug("Successfully reached ESPA API!")
        return True
