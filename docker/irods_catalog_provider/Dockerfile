FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ARG ubuntu_name=focal

RUN apt-get update && \
    apt-get install -y \
        apt-transport-https \
	lsb-release \
        gnupg \
        wget \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

RUN wget -qO - https://packages.irods.org/irods-signing-key.asc | apt-key add - && \
    echo "deb [arch=amd64] https://packages.irods.org/apt/ $(lsb_release -sc) main" | tee /etc/apt/sources.list.d/renci-irods.list

RUN apt-get update && \
    apt-get install -y \
        libcurl4-gnutls-dev \
        python3 \
        python3-distro \
        python3-jsonschema \
        python3-pip \
        python3-psutil \
        python3-requests \
        rsyslog \
        unixodbc \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

ARG irods_version=4.3.0
ARG irods_package_version_suffix=-1~${ubuntu_name}
ARG irods_package_version=${irods_version}${irods_package_version_suffix}
ARG irods_resource_plugin_version=${irods_version}.0${irods_package_version_suffix}

RUN apt-get update && \
    apt-get install -y \
        irods-database-plugin-postgres=${irods_package_version} \
        irods-runtime=${irods_package_version} \
        irods-server=${irods_package_version} \
        irods-resource-plugin-s3=${irods_resource_plugin_version} \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

COPY setup-${irods_version}.input /
RUN mv /setup-${irods_version}.input /irods_setup.input

WORKDIR /
COPY entrypoint.sh .
RUN chmod u+x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
