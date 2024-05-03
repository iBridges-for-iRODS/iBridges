FROM ubuntu:22.04
ARG os_name=jammy

ENV DEBIAN_FRONTEND=noninteractive
ARG ubuntu_name=focal

RUN apt-get update
RUN apt-get install -y lsb-release gnupg wget sudo
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

# IRODS SERVER PACKAGES
RUN wget -qO - https://packages.irods.org/irods-signing-key.asc | sudo apt-key add -
RUN sudo rm -rf /etc/apt/sources.list.d/renci-irods.list
RUN sudo echo "deb [arch=amd64] https://packages.irods.org/apt/ $(lsb_release -sc) main" |sudo tee /etc/apt/sources.list.d/renci-irods.list

RUN apt-get update
RUN apt-get install -y python3 unixodbc
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

ARG irods_version=4.3.2
ARG irods_package_version_suffix=-0~${os_name}
ARG irods_package_version=${irods_version}${irods_package_version_suffix}
#ARG irods_resource_plugin_version=${irods_version}.0${irods_package_version_suffix}

RUN apt-get update && \
    apt-get install -y irods-database-plugin-postgres=$irods_package_version
RUN apt-get install irods-server=$irods_package_version
RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

COPY setup-${irods_version}.input /
RUN mv /setup-${irods_version}.input /irods_setup.input

WORKDIR /
COPY entrypoint.sh .
RUN chmod u+x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
