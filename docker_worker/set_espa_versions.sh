#!/usr/bin/bash

cat ${2} | sed \
    -e "s/ESPA_PRODUCT_FORMATTER/product_formatter_v1.13.1/" \
    -e "s/ESPA_L2QA_TOOLS/l2qa_tools_v1.6.0/" \
    -e "s/ESPA_SURFACE_REFLECTANCE/surface_reflectance_sept2017/" \
    -e "s/ESPA_LAND_SURFACE_TEMPERATURE/lst-rit-v0.3.1/" \
    -e "s/ESPA_SPECTRAL_INDICES/spectral_indices_v2.6.0/" \
    -e "s/ESPA_SURFACE_WATER_EXTENT/espa-v2.22.0/" \
    -e "s/ESPA_ELEVATION/v2.3.0/" \
    -e "s/ESPA_REPROJECTION/v1.0.1/" \
    -e "s/ESPA_PYTHON_LIBRARY/v1.1.0/" > ${3}


espa_release: 2.35.0
dans_gdal_scripts_espa: 0.16
espa_product_formatter: 1.19.0
espa_l2qa_tools: 1.7.2
espa_aq_refl: 1.1.0
espa_surface_reflectance: 1.0.14
espa_surface_reflectance_ledaps: 3.4.0
espa_surface_reflectance_lasrc: 2.0.1
espa_surface_temperature: 2.5.0
espa_surface_temperature_rit: 2.5.0
espa_spectral_indices: 2.9.0
espa_surface_water_extent: 1.0.7
espa_surface_water_extent_cfbwd: 1.1.0
espa_surface_water_extent_dswe: 2.3.0
espa_elevation: 2.3.1
espa_reprojection: 1.1.1
espa_plotting: 0.5.1
gdal_espa: 1.11.1
proj_espa: 4.8.0
modtran_espa: 5.3.2
python_lsrd: 2.7.8