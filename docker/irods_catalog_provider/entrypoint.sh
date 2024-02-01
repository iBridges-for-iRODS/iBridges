#! /bin/bash -e

catalog_db_hostname=irods-catalog

echo "Waiting for iRODS catalog database to be ready"

until pg_isready -h ${catalog_db_hostname} -d ICAT -U irods -q
do
    sleep 1
done

echo "iRODS catalog database is ready"

setup_input_file=/irods_setup.input

if [ -e "${setup_input_file}" ]; then
    echo "Running iRODS setup"
    python3 /var/lib/irods/scripts/setup_irods.py < "${setup_input_file}"
    rm /irods_setup.input
fi

echo "Starting server"

cd /usr/sbin
su irods -c 'bash -c "./irodsServer -u"'
