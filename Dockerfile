FROM centos:centos6
LABEL maintainer="USGS LSRD http://eros.usgs.gov"

ENV UNAME='espa'
ENV UGROUP='ie'

RUN yum -y update && yum clean all

RUN yum -y install epel-release

RUN yum -y install ansible

# Ansible: the 'espa-worker.yml' playbook installs our ESPA science applications
COPY playbook /tmp/ansible/
RUN ansible-playbook /tmp/ansible/espa-worker.yml && \
	rm -rf /tmp/ansible

# We need to clear out this older version of numpy
RUN rm -rf /usr/local/lib/python2.7/site-packages/numpy*
RUN /usr/local/bin/pip install numpy==1.16.2 lxml==3.6.0 netcdf4==1.4.2

RUN yum -y install modtran-espa --nogpgcheck

# Copy over the espa-worker processing scripts
RUN mkdir /home/$UNAME/espa-processing
COPY processing /home/$UNAME/espa-processing/processing
COPY test /home/$UNAME/espa-processing/test
RUN chown -R $UNAME:$UGROUP /home/$UNAME/ \
    && ln -s /home/$UNAME/espa-processing/ /src

# Update PYTHONPATH to find espa-product-formatter modules
ENV PYTHONPATH=/usr/local/espa-product-formatter/python

# Set the username and working directory
USER $UNAME
WORKDIR /home/$UNAME
