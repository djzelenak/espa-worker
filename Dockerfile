FROM centos:centos6.10
LABEL maintainer="USGS LSRD http://eros.usgs.gov"

RUN yum -y update && yum clean all

# Install python2.7 requirements, python2.7, and pip
RUN yum -y install epel-release \
    && yum groupinstall -y 'development tools' \
    && yum -y install zlib-devel openssl-devel sqlite-devel bzip2-devel xz-libs wget \
    && wget https://www.python.org/ftp/python/2.7.8/Python-2.7.8.tar.xz \
    && tar xvfJ Python-2.7.8.tar.xz \
    && cd Python-2.7.8 \
    && ./configure --prefix=/usr/local \
    && make \
    && make install \
    && curl https://bootstrap.pypa.io/get-pip.py | python2.7 \
    && cd / \
    && rm -rf Python-2.7.8*

# Install ESPA dependencies
RUN yum -y install wgrib \
    hdf5 \
    hdf5-devel \
    libxml2-devel \
    libxslt \
    libxslt-devel \
    pigz \
    java-1.7.0-openjdk \
    java-1.7.0-openjdk-devel \
    ansible \
    yum-utils \
    && pip install lxml==3.6.0 netcdf4==1.4.2 docker \
    && yum -y update && yum clean all

# Ansible: the 'espa-worker.yml' playbook installs our ESPA science applications
COPY playbook /tmp/ansible/
RUN ansible-playbook /tmp/ansible/espa-worker.yml \
    && rm -rf /tmp/ansible
