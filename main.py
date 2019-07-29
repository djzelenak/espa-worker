import os
import requests
import schedule
from copy import deepcopy
from processing import processor, config
from functools import partial

def request(method, url, status=None):
   """
    Make an http request
    Args:
        method: HTTP method to use
        resource: API resource to touch

    Returns: response and status code
    """
   valid_methods = ('get', 'put', 'delete', 'head', 'options', 'post')

   if method not in valid_methods:
       raise Exception('Invalid request method {}'.format(method))

   try:
       resp = requests.request(method, url)
   except requests.RequestException as e:
       raise Exception(e)

   if status and resp.status_code != status:
       raise Exception("unexpected status: {} for {}".format(resp.status_code, url))

   return resp.json(), resp.status_code

def update_status(api, products, status):
    return True

def get_products_to_process(resource, limit, user, priority, product_type):
    """
    Retrieve scenes/orders to begin processing in the system
    Args:
        limit: number of products to grab
        user: specify a user
        priority: depricated, legacy support
        product_type: landsat and/or modis
    Returns: list of dicts
    """
    params = ['record_limit={}'.format(limit) if limit else None,
              'for_user={}'.format(user) if user else None,
              'priority={}'.format(priority) if priority else None,
              'product_types={}'.format(product_type) if product_type else None]

    query = '&'.join([q for q in params if q])
    url = '{}/products?{}'.format(resource, query)
    resp, status = request('get', url, status=200)
    return resp

def remove_single_quotes(instring):
    return instring.replace("'", '')

def work(indata):
    datatype = indata['espa_datatype']
    priority = indata['espa_priority']
    scale    = indata['espa_jobscale']
    user     = indata['espa_user']
    api      = indata['espa_api']

    cfg = config.config()

    # make request to api for work
    products = get_products_to_process(api, scale, user, priority, datatype)

    # update their status in the api to 'processing'
    status_to_processing = partial(update_status, api=api, status='processing')
    map(status_to_processing, products)

    for product in products:
        # todo: use some a spec validation to ensure data characteristics
        # todo: add logging
        params = deepcopy(product)

        params['orderid'] = remove_single_quotes(product['orderid']) 
        params['product_id'] = product['scene'] 
        product_type = product['product_type']
        options      = product['options']

        if 'output_format' not in options.keys():
            options['output_format'] = 'envi'

        params['options'] = options

        # pass the dicts to processor.py
        # ----------------------------------------------------------------
        # NOTE: The first thing the product processor does during
        #       initialization is validate the input parameters.
        # ----------------------------------------------------------------

        destination_product_file = 'ERROR'
        destination_cksum_file = 'ERROR'
        pp = None
        try:
            # All processors are implemented in the processor module
            pp = processor.get_instance(cfg, params)
            (destination_product_file, destination_cksum_file) = pp.process()

        finally:
             # Free disk space to be nice to the whole system.
             if pp is not None:
                 pp.remove_product_directory()

def main():
    cfg = config.config()
    schedule.every(1).minutes.do(work, cfg)

    # this should be scheduled in the api using either Schedule, or cron
    # schedule.every(7).minutes.do(order_disposition_job)
    while True:
        schedule.run_pending()

if __name__ == '__main__':
    main()

