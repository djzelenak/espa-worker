FROM centos:centos6
LABEL maintainer="USGS LSRD http://eros.usgs.gov"

RUN yum -y update && yum clean all

RUN yum -y install epel-release

RUN yum -y install ansible

# Ansible: the 'espa-worker.yml' playbook installs our ESPA science applications
COPY playbook /tmp/ansible/
RUN ansible-playbook /tmp/ansible/espa-worker.yml && \
	rm -rf /tmp/ansible

# We need to clear out this older version of numpy
RUN rm -rf /usr/local/lib/python2.7/site-packages/numpy*

# Install any remaining python packages
COPY requirements.txt /
RUN /usr/local/bin/pip install -r requirements.txt && \
    rm -f requirements.txt

# Copy over the espa-worker processing scripts
RUN mkdir /espa-processing
COPY processing /espa-processing/processing
COPY test /espa-processing/test
RUN ln -s /espa-processing/ /home/espa/src
RUN ln -s /espa-processing/ /home/espatst/src
RUN ln -s /espa-processing/ /home/espadev/src
RUN ln -s /espa-storage/orders /output_product_cache

# Update PYTHONPATH to find espa-product-formatter modules
ENV PYTHONPATH=/usr/local/espa-product-formatter/python

# Set the working directory
WORKDIR /
