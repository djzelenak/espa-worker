[![pipeline status](https://eroslab.cr.usgs.gov/lsrd/espa-worker/badges/topic/centos7/pipeline.svg)](https://eroslab.cr.usgs.gov/lsrd/espa-worker/commits/topic/centos7)

[![coverage report](https://eroslab.cr.usgs.gov/lsrd/espa-worker/badges/topic/centos7/coverage.svg)](https://eroslab.cr.usgs.gov/lsrd/espa-worker/commits/topic/centos7)

# ESPA worker
##### A containerized processing environment for generating ESPA science products

## Base
A CentOS 7 base image using the native python 2 interpreter.  Provides
additional python dev headers and pip.

#### Built From:
 * __centos:7.3.1611__
 
#### Registry Names:
 * __***REMOVED***/lsrd/espa-worker:base-latest__
 * __***REMOVED***/lsrd/espa-worker:base-{version}-{short commit SHA}__

## Build Environment
Built from the base image.  Provides all of the libraries required to
build the various espa science applications.

 
| Packages |
| --------|
| e2fsprogs
| expat-devel |
| freetype-devel |
| glibc-static |
| libcurl-devel |
| libidn-devel |
| libgfortran-static |
| libquadmath-static |
| perl-ExtUtils-MakeMaker |
| texinfo |
| bzip2-devel |
| zlib-devel |
| zlib-static |
| libpng-devel |
| libpng-static |
| rpm-build |
| cmake |
| libxml2 |
| libxml2-devel |
| libxslt |
| libxslt-devel |
| openjpeg2 |
| openjpeg2-devel |
| openjpeg |
| openjpeg-devel |
| java-1.7.0-openjdk |
| java-1.7.0-openjdk-devel |

#### Libraries:
  
| Library       | Version       | Source                                          |
| ------------- |:-------------:|:------------------------------------------------|
| libidn        | 1.32          | ftp://ftp.gnu.org/gnu/libidn/libidn-1.32.tar.gz |
| curl          | 7.48.0        | https://curl.haxx.se/download/curl-7.48.0.tar.gz |
| sxz           | 5.2.2         |https://tukaani.org/xz/xz-5.2.2.tar.gz   |
| szip          | 2.1.1         |https://support.hdfgroup.org/ftp/lib-external/szip/2.1.1/src/szip-2.1.1.tar.gz|
| libxml2       | 2.9.3         |ftp://xmlsoft.org/libxml2/libxml2-2.9.3.tar.gz|
| libxslt       | 1.1.28        |ftp://xmlsoft.org/libxslt/libxslt-1.1.28.tar.gz|
| jpeg          | v9b           |http://www.ijg.org/files/jpegsrc.v9b.tar.gz |
| jbigkit       | 2.1           |https://www.cl.cam.ac.uk/~mgk25/jbigkit/download/jbigkit-2.1.tar.gz|
| proj          | 4.9.1         |https://download.osgeo.org/proj/proj-4.9.1.tar.gz|
| tiff          | 4.0.6         | http://download.osgeo.org/libtiff/tiff-4.0.6.tar.gz|
| libgeotiff    | 1.4.1         | http://download.osgeo.org/geotiff/libgeotiff/libgeotiff-1.4.1.tar.gz|
| hdf4          | 4.2.11        | https://support.hdfgroup.org/ftp/HDF/releases/HDF4.2.11/src/hdf-4.2.11.tar.gz|
| hdf5          | 1.8.16        | https://support.hdfgroup.org/ftp/HDF5/releases/hdf5-1.8/hdf5-1.8.16/src/hdf5-1.8.16.tar.gz|
| netcdf        | 4.4.1.1       | https://github.com/Unidata/netcdf-c/archive/v4.4.1.1.tar.gz|
| hdf-eos2      | 19v1.00       | http://hdfeos.org/software/hdfeos/HDF-EOS2.19v1.00.tar.Z|
| hdf-eos5      | 1.16          | https://observer.gsfc.nasa.gov/ftp/edhs/hdfeos5/latest_release/HDF-EOS5.1.16.tar.Z|
| gdal          | 1.11.4        | http://download.osgeo.org/gdal/1.11.4/gdal-1.11.4.tar.gz

#### Registry Names: 
 * __***REMOVED***/lsrd/espa-worker:builder-latest___
 * __***REMOVED***/lsrd/espa-worker:builder-{version}-{short commit SHA}__

## Worker Environment
Based off the of the builder image, the worker image downloads, builds, and installs all
of the ESPA science applications from source.  It provides the final processing 
environment that is run on MESOS to deliver ESPA science products.

#### Registry Names
 * __***REMOVED***/lsrd/espa-worker:worker-latest__
 * __***REMOVED***/lsrd/espa-worker:worker-{version}-{short commit SHA}__
 

