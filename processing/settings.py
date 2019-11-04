
# Filename extension for Landsat based input products
LANDSAT_INPUT_FILENAME_EXTENSION = '.tar.gz'

# Filename extension for Modis based input products
MODIS_INPUT_FILENAME_EXTENSION = '.hdf'

# Filename extension for VIIRS based input products
VIIRS_INPUT_FILENAME_EXTENSION = '.h5'

# Filename extension for Sentinel-2 based input products
S2_INPUT_FILENAME_EXTENSION = '.zip'

# Path to the completed orders
ESPA_REMOTE_CACHE_DIRECTORY = '/data2/science_lsrd/LSRD/orders'
ESPA_LOCAL_CACHE_DIRECTORY = ''

# Number of seconds to sleep when errors are encountered before attempting the
# task again
DEFAULT_SLEEP_SECONDS = 2

# Maximum number of times to attempt packaging, delivery, and distribution
MAX_PACKAGING_ATTEMPTS = 3
MAX_DELIVERY_ATTEMPTS = 3
MAX_DISTRIBUTION_ATTEMPTS = 5

# Maximum number of times to attempt setting the scene error
MAX_SET_SCENE_ERROR_ATTEMPTS = 5

# Specify the checksum tool and filename extension
ESPA_CHECKSUM_TOOL = 'md5sum'
ESPA_CHECKSUM_EXTENSION = 'md5'

# Plotting defaults
PLOT_BG_COLOR = '#f3f3f3'  # A light gray
PLOT_MARKER = (1, 3, 0)    # Better circle than 'o'
PLOT_MARKER_SIZE = 4.0     # A good size for the circle or diamond
PLOT_MARKER_EDGE_WIDTH = 0.9  # The width of the black marker border

# Default pigz multithreading level
PIGZ_MULTITHREADING = 1

# We are only supporting one radius when warping to sinusoidal
SINUSOIDAL_SPHERE_RADIUS = 6371007.181

# Some defines for common pixels sizes in decimal degrees
DEG_FOR_30_METERS = 0.0002695
DEG_FOR_15_METERS = (DEG_FOR_30_METERS / 2.0)
DEG_FOR_10_METERS = (DEG_FOR_30_METERS / 3.0)
DEG_FOR_1_METER = (DEG_FOR_30_METERS / 30.0)

# Supported datums - the strings for them
WGS84 = 'WGS84'
NAD27 = 'NAD27'
NAD83 = 'NAD83'
# WGS84 should always be first in the list
VALID_DATUMS = [WGS84, NAD27, NAD83]

TRANSFER_BLOCK_SIZE = 10485760

# We do not allow any user selectable choices for this projection
GEOGRAPHIC_PROJ4_STRING = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"

# Band type data ranges.  They are intended to be used for removing outliers
# from the data before statistics generation
# Must match DATA_MAX_Y and DATA_MIN_Y values in espa_plotting.py
# The types must match the types in cdr_ecv.py and modis.py
# Note: These are also defined in such away that the fill values are also
#       excluded.
BAND_TYPE_STAT_RANGES = {
    'SR': {
        'UPPER_BOUND': 10000,
        'LOWER_BOUND': 0
    },
    'TOA': {
        'UPPER_BOUND': 10000,
        'LOWER_BOUND': 0
    },
    # BT values based on the value range in the files
    # No need to scale them to K, because the plots will come out the same
    'BT': {
        'UPPER_BOUND': 3500,
        'LOWER_BOUND': 1500
    },
    'INDEX': {
        'UPPER_BOUND': 10000,
        'LOWER_BOUND': -1000
    },
    # Over-water reflectance from LaORCA
    'RRS': {
        'UPPER_BOUND': 20000,
        'LOWER_BOUND': 0
    },
    'CHLOR_A': {
        'UPPER_BOUND': 10000,
        'LOWER_BOUND': 0
    },
    # This is for MODIS LST.  The data range is 7500 to 65535, but with scaling
    # factor 0.02 that translates to 150K to 1310.7K.  Most of that temperature
    # range will not be used much.  For comparison to the Landsat LST, and to
    # allow the standard deviations and point trends to show up better in the
    # plots, we will limit the upper bound to 18,650 (373.0K).  This matches
    # the Landsat LST range in K, so we only need separate band types so we
    # can handle the different MODIS and Landsat LST data types correctly.
    'LST': {
        'UPPER_BOUND': 373,
        'LOWER_BOUND': 150
    },
    # This is for Landsat LST.  The data range is 1500 to 3730.  With scaling
    # to K it becomes 150 to 373.
    'LANDSAT_ST': {
        'UPPER_BOUND': 373,
        'LOWER_BOUND': 150
    },
    'EMIS': {
        'UPPER_BOUND': 255,
        'LOWER_BOUND': 1
    },
    # Sentinel-2 A,B
    'S2_SR': {
        'UPPER_BOUND': 16000,
        'LOWER_BOUND': -2000
    },
    'S2_INDEX': {
        'UPPER_BOUND': 10000,
        'LOWER_BOUND': -10000
    }
}


MODIS_LST_SCALE = 0.02
LANDSAT_ST_SCALE = 0.1
SENTINEL_SR_SCALE = 0.0001


'''
LOGGING DEFINITIONS
'''
PROCESSING_LOGGER = 'espa.processing'

LOGGER_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'espa.standard': {
            # Used by the processing system
            'format': ('%(asctime)s.%(msecs)03d %(process)d'
                       ' %(levelname)-8s'
                       ' %(filename)s:%(lineno)d:%(funcName)s'
                       ' -- %(message)s'),
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'espa.thread': {
            # An example for threading, not currently used
            'format': ('%(asctime)s.%(msecs)03d %(process)d'
                       ' %(levelname)-8s'
                       ' %(filename)s:%(lineno)d:%(funcName)s'
                       ' %(thread)d'
                       ' -- %(message)s'),
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        # All espa.* handler names need to match the espa.* logger names
        'espa.processing': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'formatter': 'espa.standard',
            'filename': '/tmp/espa-processing.log',
            'mode': 'a'
        }
    },
    'loggers': {
        # All espa.* logger names need to match the espa.* handler names
        'espa.processing': {
            # To be used by the processing system
            'level': 'INFO',
            'propagate': False,
            'handlers': ['espa.processing']
        }
    }
}
