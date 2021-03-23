FROM ubuntu:18.04
RUN apt-get update
RUN apt-get install -y wget gnupg
#iRODS icommands
RUN wget -qO - https://packages.irods.org/irods-signing-key.asc | apt-key add - && \
    echo "# /etc/apt/sources.list.d/renci-irods.list" | tee -a /etc/apt/sources.list.d/renci-irods.list && \
    echo "deb [arch=amd64] https://packages.irods.org/apt/ xenial main" | tee -a /etc/apt/sources.list.d/renci-irods.list && \
    apt-get update && apt-get install -y irods-icommands

#pip3 and ipython3
RUN apt-get install -y python3-pip
RUN pip3 install ipython
#python iRODS client
RUN pip3 install python-irodsclient

CMD ["bash"]
