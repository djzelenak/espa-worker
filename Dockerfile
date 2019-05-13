FROM centos:centos7.6.1810
MAINTAINER USGS LCMAP http://eros.usgs.gov

ENV GDAL_VERSION 2.4.1

ADD http://download.osgeo.org/gdal/${GDAL_VERSION}/gdal-${GDAL_VERSION}.tar.gz /usr/local/src/

RUN yum update -y

RUN yum install -y cmake gcc gcc-c++ make
RUN cd /usr/local/src; tar xf gdal-${GDAL_VERSION}.tar.gz
RUN cd /usr/local/src/gdal-${GDAL_VERSION}; ./configure; make; make install
