
'''
Description: Provides routines for interfacing with parameters in a
             dictionary.

License: NASA Open Source Agreement 1.3
'''

import os

import settings
from logging_tools import EspaLogging
import sensor


# Settings for what is supported
VALID_OUTPUT_FORMATS = ['envi', 'gtiff', 'hdf-eos2', 'netcdf']
VALID_RESAMPLE_METHODS = ['near', 'bilinear', 'cubic', 'cubicspline',
                          'lanczos']
VALID_PIXEL_SIZE_UNITS = ['meters', 'dd']
VALID_IMAGE_EXTENTS_UNITS = ['meters', 'dd']
VALID_PROJECTIONS = ['sinu', 'aea', 'utm', 'ps', 'lonlat']
VALID_NS = ['north', 'south']


def test_for_parameter(parms, key):
    '''
    Description:
      Tests to see if a specific parameter is present.

    Returns:
       True - If the parameter is present in the dictionary
      False - If the parameter is *NOT* present in the dictionary or does not
              have a value
    '''

    if (key not in parms) or (parms[key] == '') or (parms[key] is None):
        return False

    return True


def validate_reprojection_parameters(parms, product_id):
    '''
    Description:
      Perform a check on the possible reprojection parameters

    Note:
      We blindly convert values to float or int without checking them.  It is
      assumed that the web tier has validated them.
    '''

    logger = EspaLogging.get_logger(settings.PROCESSING_LOGGER)

    # Create this and set to None if not present
    if not test_for_parameter(parms, 'projection'):
        logger.warning('projection: missing defaulting to None')
        parms['projection'] = None

    # Create this and set to 'near' if not present
    if not test_for_parameter(parms, 'resample_method'):
        logger.warning('resample_method: missing defaulting to near')
        parms['resample_method'] = 'near'

    # Make sure these have at least a False value
    required_parameters = ['reproject', 'image_extents', 'resize']

    for parameter in required_parameters:
        if not test_for_parameter(parms, parameter):
            logger.warning('{0}: missing defaulting to False'
                           .format(parameter))
            parms[parameter] = False

    if parms['reproject']:
        if not test_for_parameter(parms, 'target_projection'):
            raise RuntimeError('Missing target_projection parameter')
        else:
            # Convert to lower case
            target_projection = parms['target_projection'].lower()
            parms['target_projection'] = target_projection

            # Verify a valid projection
            if target_projection not in VALID_PROJECTIONS:
                msg = ('Invalid target_projection [{0}]:'
                       ' Argument must be one of ({1})'
                       .format(target_projection,
                               ', '.join(VALID_PROJECTIONS)))
                raise ValueError(msg)

            if target_projection == 'sinu':
                if not test_for_parameter(parms, 'central_meridian'):
                    raise RuntimeError('Missing central_meridian parameter')
                else:
                    parms['central_meridian'] = \
                        float(parms['central_meridian'])
                if not test_for_parameter(parms, 'false_easting'):
                    raise RuntimeError('Missing false_easting parameter')
                else:
                    parms['false_easting'] = float(parms['false_easting'])
                if not test_for_parameter(parms, 'false_northing'):
                    raise RuntimeError('Missing false_northing parameter')
                else:
                    parms['false_northing'] = float(parms['false_northing'])

                if not test_for_parameter(parms, 'datum'):
                    parms['datum'] = None

            if target_projection == 'aea':
                if not test_for_parameter(parms, 'std_parallel_1'):
                    raise RuntimeError('Missing std_parallel_1 parameter')
                else:
                    parms['std_parallel_1'] = float(parms['std_parallel_1'])
                if not test_for_parameter(parms, 'std_parallel_2'):
                    raise RuntimeError('Missing std_parallel_2 parameter')
                else:
                    parms['std_parallel_2'] = float(parms['std_parallel_2'])
                if not test_for_parameter(parms, 'origin_lat'):
                    raise RuntimeError('Missing origin_lat parameter')
                else:
                    parms['origin_lat'] = float(parms['origin_lat'])
                if not test_for_parameter(parms, 'central_meridian'):
                    raise RuntimeError('Missing central_meridian parameter')
                else:
                    parms['central_meridian'] = \
                        float(parms['central_meridian'])
                if not test_for_parameter(parms, 'false_easting'):
                    raise RuntimeError('Missing false_easting parameter')
                else:
                    parms['false_easting'] = float(parms['false_easting'])
                if not test_for_parameter(parms, 'false_northing'):
                    raise RuntimeError('Missing false_northing parameter')
                else:
                    parms['false_northing'] = float(parms['false_northing'])

                # The datum must be in uppercase for the processing code to
                # work so if it is present here, we force it
                if not test_for_parameter(parms, 'datum'):
                    raise RuntimeError('Missing datum parameter')
                else:
                    parms['datum'] = parms['datum'].upper()
                if parms['datum'] not in settings.VALID_DATUMS:
                    valid_items = ', '.join(settings.VALID_DATUMS)
                    raise ValueError('Invalid datum [{0}]:'
                                     ' Argument must be one of [{1}]'
                                     .format(parms['datum'], valid_items))

            if target_projection == 'utm':
                if not test_for_parameter(parms, 'utm_zone'):
                    raise RuntimeError('Missing utm_zone parameter')
                else:
                    zone = int(parms['utm_zone'])
                    if zone < 0 or zone > 60:
                        raise ValueError('Invalid utm_zone [{0}]:'
                                         ' Value must be 0-60'.format(zone))
                    parms['utm_zone'] = zone
                if not test_for_parameter(parms, 'utm_north_south'):
                    raise RuntimeError('Missing utm_north_south parameter')
                elif parms['utm_north_south'] not in VALID_NS:
                    raise ValueError('Invalid utm_north_south [{0}]:'
                                     ' Argument must be one of [{1}]'
                                     .format(parms['utm_north_south'],
                                             ', '.join(VALID_NS)))

                if not test_for_parameter(parms, 'datum'):
                    parms['datum'] = None

            if target_projection == 'ps':
                if not test_for_parameter(parms, 'latitude_true_scale'):
                    # Must be tested before origin_lat
                    raise RuntimeError('Missing latitude_true_scale parameter')
                else:
                    value = float(parms['latitude_true_scale'])
                    if ((value < 60.0 and value > -60.0) or
                            value > 90.0 or value < -90.0):
                        raise ValueError('Invalid latitude_true_scale [{0}]:'
                                         ' Value must be between'
                                         ' (-60.0 and -90.0) or'
                                         ' (60.0 and 90.0)'.format(value))
                    parms['latitude_true_scale'] = value
                if not test_for_parameter(parms, 'longitude_pole'):
                    raise RuntimeError('Missing longitude_pole parameter')
                else:
                    parms['longitude_pole'] = float(parms['longitude_pole'])
                if not test_for_parameter(parms, 'origin_lat'):
                    # If the user did not specify the origin_lat value, then
                    # set it based on the latitude true scale
                    lat_ts = float(parms['latitude_true_scale'])
                    if lat_ts < 0:
                        parms['origin_lat'] = -90.0
                    else:
                        parms['origin_lat'] = 90.0
                else:
                    value = float(parms['origin_lat'])
                    if value != -90.0 and value != 90.0:
                        raise ValueError('Invalid origin_lat [{0}]:'
                                         ' Value must be -90.0 or 90.0'
                                         .format(value))
                    parms['origin_lat'] = value

                if not test_for_parameter(parms, 'false_easting'):
                    raise RuntimeError('Missing false_easting parameter')
                else:
                    parms['false_easting'] = float(parms['false_easting'])
                if not test_for_parameter(parms, 'false_northing'):
                    raise RuntimeError('Missing false_northing parameter')
                else:
                    parms['false_northing'] = float(parms['false_northing'])

                if not test_for_parameter(parms, 'datum'):
                    parms['datum'] = None

            if target_projection == 'lonlat':

                if not test_for_parameter(parms, 'datum'):
                    parms['datum'] = None

    if parms['resample_method'] not in VALID_RESAMPLE_METHODS:
        raise ValueError('Invalid resample_method [{0}]:'
                         ' Argument must be one of [{1}]'
                         .format(parms['resample_method'],
                                 ', '.join(VALID_RESAMPLE_METHODS)))

    if parms['image_extents']:
        if not test_for_parameter(parms, 'image_extents_units'):
            raise RuntimeError('Missing image_extents_units parameter')
        else:
            if parms['image_extents_units'] not in VALID_IMAGE_EXTENTS_UNITS:
                raise ValueError('Invalid image_extents_units [{0}]:'
                                 ' Argument must be one of [{1}]'
                                 .format(parms['image_extents_units'],
                                         ', '.join(VALID_IMAGE_EXTENTS_UNITS)))
        if not test_for_parameter(parms, 'minx'):
            raise RuntimeError('Missing minx parameter')
        else:
            parms['minx'] = float(parms['minx'])
        if not test_for_parameter(parms, 'miny'):
            raise RuntimeError('Missing miny parameter')
        else:
            parms['miny'] = float(parms['miny'])
        if not test_for_parameter(parms, 'maxx'):
            raise RuntimeError('Missing maxx parameter')
        else:
            parms['maxx'] = float(parms['maxx'])
        if not test_for_parameter(parms, 'maxy'):
            raise RuntimeError('Missing maxy parameter')
        else:
            parms['maxy'] = float(parms['maxy'])
    else:
        # Default these
        parms['minx'] = None
        parms['miny'] = None
        parms['maxx'] = None
        parms['maxy'] = None
        parms['image_extents_units'] = None

    if parms['resize']:
        if not test_for_parameter(parms, 'pixel_size'):
            raise RuntimeError('Missing pixel_size parameter')
        else:
            parms['pixel_size'] = float(parms['pixel_size'])
        if not test_for_parameter(parms, 'pixel_size_units'):
            raise RuntimeError('Missing pixel_size_units parameter')
        else:
            if parms['pixel_size_units'] not in VALID_PIXEL_SIZE_UNITS:
                valid_items = ', '.join(VALID_PIXEL_SIZE_UNITS)
                raise ValueError('Invalid pixel_size_units [{0}]:'
                                 ' Argument must be one of [{1}]'
                                 .format(parms['pixel_size_units'],
                                         valid_items))
    else:
        # Default this
        parms['pixel_size'] = None
        parms['pixel_size_units'] = None

    if ((parms['reproject'] or parms['image_extents']) and
            not parms['resize']):
        # Sombody asked for reproject or extents, but didn't specify a pixel
        # size

        units = 'meters'
        if parms['reproject'] and parms['target_projection'] == 'lonlat':
            units = 'dd'

        # Default to the sensor specific meters or dd equivalent
        parms['pixel_size'] = sensor.info(product_id).default_pixel_size[units]
        parms['pixel_size_units'] = units

        logger.warning('resize: parameter not provided'
                       ' but required for reprojection or image extents'
                       ' (Defaulting pixel_size({0}) and pixel_size_units({1})'
                       .format(parms['pixel_size'], parms['pixel_size_units']))
