FROM centos:centos6.10
MAINTAINER USGS LSRD http://eros.usgs.gov

RUN yum -y update && yum clean all

# Install python2.7 requirements, python2.7, and pip
RUN yum -y install epel-release && yum groupinstall -y 'development tools'
RUN yum -y install zlib-dev openssl-devel sqlite-devel bzip2-devel xz-libs wget
RUN wget https://www.python.org/ftp/python/2.7.8/Python-2.7.8.tar.xz
RUN tar xvfJ Python-2.7.8.tar.xz
WORKDIR Python-2.7.8
RUN ./configure --prefix=/usr/local && make && make install
RUN curl https://bootstrap.pypa.io/get-pip.py | python2.7

# Install ESPA dependencies
WORKDIR /
RUN yum -y install gcc gcc-c++ wgrib libhdf5 libhdf5-devl libxml2 libxml2-devel libxslt libxslt-devel pigz \
    java-1.7.0-openjdk java-1.7.0-openjdk-devel git ansible yum-utils && yum clean all

#RUN yum -y install python-devel && yum clean all

RUN pip install lxml==3.6.0 netcdf4==1.4.2

# Ansible playbook installs ESPA science libraries and sets up working dirs
COPY playbook/ /tmp/ansible/
RUN ansible-playbook /tmp/ansible/lsrd_hadoop_worker.yml
