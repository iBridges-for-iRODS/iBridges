#! /bin/bash -e

echo "waiting for iRODS to be ready"

irods_catalog_provider_hostname=irods-catalog-provider
until nc -z ${irods_catalog_provider_hostname} 1247
do
    sleep 10
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
echo 'rods' | iinit
echo 'Authenticated as rods'

# wait until second resource is created
ilsresc | grep 'resc2' &> /dev/null
while [ $? != 0 ];
do
    echo "Sleep"
    sleep 1
done

# create second user
iadmin mkuser testuser rodsuser
iadmin moduser testuser password testuser
echo 'testuser created'
echo $(iadmin lu testuser)

cd /ibridges/integration_test
pytest .

result=$?
if [[ -z "$CI" ]]; then
    /bin/bash
else
    exit $result
fi
