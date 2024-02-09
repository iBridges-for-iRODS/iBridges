#! /bin/bash -e

echo "waiting for iRODS to be ready"

irods_catalog_provider_hostname=irods-catalog-provider
until nc -z ${irods_catalog_provider_hostname} 1247
do
    sleep 1
done

# After setting up iRODS, the server will respond on port 1247. However, the server process is
# stopped after some preliminary tests are completed. The irods-catalog-provider service will
# start the server manually again, but this will take a few seconds. Sleep here to ensure that
# next time the server responds is not the temporary uptime provided during setup.
sleep 3

until nc -z ${irods_catalog_provider_hostname} 1247
do
    sleep 1
done

echo "iRODS is ready"

# pre-authenticate the user so the iCommands are ready to use
# echo 'rods' | iinit
# echo 'Authenticated as rods'

cd /ibridges/integration_test
pytest .
/bin/bash
