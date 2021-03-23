# Userinterfaces for iRODS in Docker
## Installation
1. Install Docker
2. `docker build --tag <your tag> .`

## Usage
Start the docker container with:

`docker run -it -v <your local path>:<docker path> <your tag>`

The command will start a Docker container and enter the bash and mounts a local folder to the container.

