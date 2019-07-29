# replaces processing.conf
import os

def default_env(variable, value, operator=None):
    default = [variable, value]
    upcase_variable = variable.upper()
    if os.environ.get(upcase_variable):
        new_var = os.environ.get(upcase_variable)
        if operator:
            new_var = operator(new_var)
        default = [variable, new_var]
    return default

default_gdal_skip_drivers = 'aaigrid ace2 adrg aig airsar arg blx bmp bsb bt ceos coasp cosar cpg ctable2 ctg dimap dipex doq1 doq2 dted e00grid ecrgtoc eir elas ers esat fast fit fujibas gff gif grib gsag gsbg gs7bg gsc gtx gxf hf2 hfa ida ilwis ingr iris isis2 isis3 jaxapalsar jdem jpeg kro l1b lan lcp leveller loslas map mem mff mff2 msgn ndf ngsgeoid nitf ntv2 nwt_grc nwt_grd paux pcidsk pcraster pdf pds rik rmf rpftoc rs2 rst saga sar_ceos sdts sgi snodas srp srtmhgt terragen til usgsdem vrt xpm xyz zmap'

def config():

    aux_dir = "/usr/local/auxiliaries/"
    if os.environ.get("AUX_DIR"):
        aux_dir = os.environ.get("AUX_DIR")

    de = default_env
    return dict([
        de('espa_user', None),
        de('espa_priority', None),
        de('espa_jobscale', 1, int),
        de('espa_datatype', 'landsat'),
        de('espa_min_request_duration_in_seconds', 0, int),
        de('espa_work_dir', '/'),
        de('espa_distribution_method', 'local'),
        de('espa_distribution_dir', '/output_product_cache'),
        de('espa_schema', '/usr/local/schema/espa_internal_metadata_v2_1.xsd'),
        de('espa_land_mass_polygon', aux_dir+'land_water_polygon/land_no_buf.ply'),
        de('espa_xmlrpc', 'http://localhost:9876/ordering/rpc'),   # SET IN ENV
        de('espa_api', 'http://localhost:9876/production-api/v0'), # SET IN ENV
        de('espa_cache_host_list', None),                          # SET IN ENV
        de('espa_elevation_dir', aux_dir+'elevation'),
        de('ias_data_dir', aux_dir+'gls-dem'),
        de('pythonpath', '/usr/local/python'),
        de('immutable_distribution', 'off'),
        de('ledaps_aux_dir', aux_dir+'L17'),
        de('l8_aux_dir', aux_dir+'L8'),
        de('esun', '/usr/local/espa-cloud-masking/cfmask/static_data'),
        de('st_aux_dir', aux_dir+'LST/NARR'),
        de('st_aux_path', aux_dir+'LST/NARR'),
        de('st_fp_aux_path', aux_dir+'LST/fp'),
        de('st_fpit_aux_path', aux_dir+'LST/fpit'),
        de('st_merra_aux_path', aux_dir+'LST/merra2'),
        de('st_data_dir', '/usr/local/espa-surface-temperature/st/static_data'),
        de('st_data_path', '/usr/local/espa-surface-temperature/st/static_data'),
        de('modtran_path', '/usr/local/bin'),
        de('modtran_data_dir', aux_dir+'MODTRAN_DATA'),
        de('modtran_data_path', aux_dir+'MODTRAN_DATA'),
        de('OCDATAROOT', aux_dir+'ocdata'),
        de('aster_ged_server_name', 'localhost:5000'),  # SET IN ENV
        de('aster_ged_server_dir', '/ASTT/AG100.003/2000.01.01/'),
        de('aster_ged_server_path', '/ASTT/AG100.003/2000.01.01/'),
        de('omp_num_threads', 1, int),
        de('pigz_num_threads', 1, int),
        de('include_resource_report', False, eval),  # TO-DO: do better
        de('gdal_skip', default_gdal_skip_drivers)])
