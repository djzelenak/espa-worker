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

# Install any remaining python packages
COPY requirements.txt /
RUN /usr/local/bin/pip install -r requirements.txt && \
    rm -f requirements.txt

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
