FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y \
        apt-transport-https \
        gnupg \
        wget \
	lsb-release \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

RUN wget -qO - https://packages.irods.org/irods-signing-key.asc | apt-key add - && \
    echo "deb [arch=amd64] https://packages.irods.org/apt/ $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/renci-irods.list

# ARG icommands_version=4.3.0
# ARG icommands_package_version_suffix=-1~focal
# ARG icommands_package_version=${icommands_version}${icommands_package_version_suffix}

RUN apt-get update && \
    apt-get install -y \
        netcat \
	irods-runtime \
	irods-icommands \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

RUN mkdir -p /root/.irods
COPY docker/irods_client/environments/plain-irods/irods_environment.json /root/.irods
COPY docker/irods_client/environments/plain-irods/irods_environment_testuser.json /root/.irods

RUN mkdir -p /tmp
ADD docker/irods_client/testdata /tmp/testdata/

# install python 3
RUN apt-get update && \
    apt-get upgrade -y
RUN apt-get install -y python3 git 
	# python3-pip \
	# git

# Work around for a bug in Ubuntu 22.04: https://github.com/pypa/setuptools/issues/3269#ref-issue-1217398136
RUN wget https://bootstrap.pypa.io/get-pip.py
RUN python3 get-pip.py
RUN mkdir -p /ibridges/integration_test
ADD ibridges /ibridges/ibridges
ADD docker/irods_client/tests ibridges/integration_test
ADD docker/irods_client/environments/plain-irods ibridges/integration_test/environment
ADD .git /ibridges/.git
COPY pyproject.toml /ibridges
RUN /usr/local/bin/pip3 install /ibridges
RUN /usr/local/bin/pip3 install pytest tomli

WORKDIR /
COPY docker/irods_client/entrypoint.sh .
RUN chmod u+x ./entrypoint.sh
ENTRYPOINT bash -c "./entrypoint.sh"
