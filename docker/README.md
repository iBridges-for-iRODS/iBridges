# iBridges-Integration-tests
Dockerised integration tests of iBridges with iRODS

## Docker images
- iCAT database
- iRODS server, version 4.3.0
- Client: icommands, python-irodsclient and intgration tests

## Usage
1. Clone iBridges
   
   ```sh
   cd iBridges-Integration-tests/irods_client/
   git clone git clone --branch develop https://github.com/chStaiger/iBridges-Gui.git
   cd ..
   ```

2. `docker-compose build`
3. `docker-compose up`

To recreate the images:

1. `docker-compose rm -f`
2. `docker-compose up --force-recreate --build --no-deps`

Clean up

1. `docker image prune`
2. `docker container prune`

## Example output:

```
irods-client_1            | Integration tests start ...
irods-client_1            | Loading configs ...
irods-client_1            | iBridges config:
irods-client_1            | {'check_free_space': False, 'force_transfers': True, 'verbose': 'debug'}
irods-client_1            |
irods-client_1            | iRODS config:
irods-client_1            | {'irods_host': 'irods-catalog-provider', 'irods_port': 1247, 'irods_user_name': 'rods', 'irods_default_resc': 'demoResc', 'irods_home': '/tempZone/home/rods', 'irods_zone_name': 'tempZone'}
irods-client_1            | Passing configs to irodsConnector ...
irods-client_1            | {'check_free_space': False, 'force_transfers': True, 'verbose': 'debug'}
irods-client_1            | {'irods_host': 'irods-catalog-provider', 'irods_port': 1247, 'irods_user_name': 'rods', 'irods_default_resc': 'demoResc', 'irods_home': '/tempZone/home/rods', 'irods_zone_name': 'tempZone'}
irods-client_1            | Connect with cached password:
irods-client_1            | Valid iRODS session:  True
irods-client_1            | Get home collection
irods-client_1            | /tempZone/home/rods
irods-client_1            | Close iBridges session
irods-client_1            | Integration tests end
irods-client_1            |
irods-client_1            | Summary
irods-client_1            | Import_backend : success
irods-client_1            | authentication_cached_passwd : success
irods-client_1            | get_home_coll : success
irods-client_1            | session_cleanup : success
```
