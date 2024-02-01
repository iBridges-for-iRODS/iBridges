FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        apt-transport-https \
        gnupg \
        wget \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

# RUN wget -qO - https://packages.irods.org/irods-signing-key.asc | apt-key add - && \
    # echo "deb [arch=amd64] https://packages.irods.org/apt/ focal main" | tee /etc/apt/sources.list.d/renci-irods.list

# ARG icommands_version=4.3.0
# ARG icommands_package_version_suffix=-1~focal
# ARG icommands_package_version=${icommands_version}${icommands_package_version_suffix}

RUN apt-get update && \
    apt-get install -y \
        netcat \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

RUN mkdir -p /root/.irods
COPY docker/irods_client/irods_environment.json /root/.irods
RUN mkdir -p /root/.ibridges
COPY docker/irods_client/ibridges_config.json /root/.ibridges
RUN mkdir -p /tmp
ADD docker/irods_client/testdata /tmp/testdata/

# install python 3
RUN apt-get update && \
    apt-get upgrade -y
RUN apt-get install -y python3 git 
	# python3-pip \
	# git

RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py
RUN mkdir -p /ibridges
ADD ibridges /ibridges/ibridges
ADD .git /ibridges/.git
COPY pyproject.toml /ibridges
RUN /usr/local/bin/pip3 install /ibridges
# COPY requirements.txt /iBridges-Gui/requirements_docker.txt
# RUN pip3 install -r /iBridges-Gui/requirements_docker.txt
COPY docker/irods_client/integration_test.py /ibridges/integration_test.py

WORKDIR /
COPY docker/irods_client/entrypoint.sh .
RUN chmod u+x ./entrypoint.sh
ENTRYPOINT bash -c "./entrypoint.sh"
