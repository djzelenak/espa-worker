import requests
import logging
import config

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
        self.base = base_url
        
        # raise exception if cannot reach api
        self.test_connection()

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
            self._unexpected_status(resp.status_code, url)

        return resp.json(), resp.status_code

    def get_configuration(self, key):
        """
        Retrieve a configuration value

        Args:
            key: configuration key

        Returns: value if it exists, otherwise None

        """
        config_url = '/configuration/{}'.format(key)

        resp, status = self.request('get', config_url, status=200)

        if key in resp.keys():
            return resp[key]

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

    @staticmethod
    def _unexpected_status(code, url):
        """
        Throw exception for an unhandled http status

        Args:
            code: http status that was received
            url: URL that was used
        """
        raise Exception('Received unexpected status code: {}\n'
                        'for URL: {}'.format(code, url))

    def test_connection(self):
        """
        Tests the base URL for the class
        Returns: True if 200 status received, else False
        """
        resp, status = self.request('get')

        if status == 200:
            return True
        else:
            raise APIException("Could not connect to ESPA API: {}".format(cfg['espa_api']))


def api_connect(url):
    """
    Simple lead in method for using the API connection class

    Args:
        url: base URL to connect to

    Returns: initialized APIServer object if successful connection
             else None
    """
    api = APIServer(url)

    if not api.test_connection():
        return None

    return api
