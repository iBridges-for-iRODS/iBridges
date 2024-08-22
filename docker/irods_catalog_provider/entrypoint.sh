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

mkdir /var/lib/irods/Vault1
chown irods:irods /var/lib/irods/Vault1

#echo "Starting server"
#su irods -c 'bash -c ./irodsctl start'
#su irods -c 'iadmin mkresc resc2 unixfilesystem `hostname`:/var/lib/irods/Vault1'
#echo "Stop server"
#su irods -c 'bash -c ./irodsctl stop'

echo "Creating resource"
cd /var/lib/irods
su irods -c 'bash -c "./irodsctl start"'
su irods -c 'iadmin mkresc resc2 unixfilesystem `hostname`:/var/lib/irods/Vault1'
su irods -c 'bash -c "./irodsctl stop"'

echo "Starting server"
cd /usr/sbin
#sed 's/"irods_default_hash_scheme": "SHA256",//g' /var/lib/irods/.irods/irods_environment.json > t.json
#mv t.json /var/lib/irods/.irods/irods_environment.json
su irods -c 'bash -c "./irodsServer -u"'
