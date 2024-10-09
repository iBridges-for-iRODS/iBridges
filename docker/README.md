# iBridges-Integration-tests
Dockerised integration tests of iBridges with iRODS

## Docker images
- iCAT database
- iRODS server, version 4.3.0
- Client: icommands, python-irodsclient and intgration tests

## Usage
1. Clone iBridges
   
   ```sh
   git clone --branch develop https://github.com/iBridges-for-iRODS/iBridges.git
   ```

Execute the following commands in the root ibridges directory:

2. `docker-compose build`
3. `docker-compose up`

To recreate the images:

1. `docker-compose rm -f`
2. `docker-compose up --force-recreate --build --no-deps`

Clean up

1. `docker image prune`
2. `docker container prune`

Enter the irods-client
1. Bring the images up
2. `docker ps`
3. `docker exec -it <IMAGE> /bin/bash`

## Example output:

```
irods-client-1            | ============================= test session starts ==============================
irods-client-1            | platform linux -- Python 3.10.12, pytest-8.0.0, pluggy-1.4.0
irods-client-1            | rootdir: /ibridges/integration_test
irods-client-1            | collected 14 items
irods-client-1            | 
irods-client-1            | test_meta.py ..                                                          [ 28%]
irods-client-1            | test_permissions.py ..                                                   [ 42%]
irods-client-1            | test_resources.py .                                                      [ 50%]
irods-client-1            | test_rules.py .                                                          [ 57%]
irods-client-1            | test_session.py .x                                                       [ 71%]
irods-client-1            | test_ticket.py ....                                                      [100%]
irods-client-1            | 
irods-client-1            | ======================== 13 passed, 1 xfailed in 3.22s =========================
```
