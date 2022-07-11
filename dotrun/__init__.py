#! /usr/bin/env python3

import os
import sys
from importlib import metadata

# Packages
import docker
import dockerpty
from dotenv import dotenv_values

__version__ = metadata.version("dotrun")
absolute_path = os.getcwd()
project_name = os.path.basename(absolute_path)
container_path = f"/home/ubuntu/{project_name}"

try:
    docker_client = docker.from_env()
    docker_client.ping()
except (docker.errors.APIError, docker.errors.DockerException) as e:
    print(e)
    print(
        "Dotrun needs Docker to work, please check"
        " if Docker is installed and running"
    )
    sys.exit(1)

# Get project port
project_port = dotenv_values(".env").get("PORT", 8080)

# Pull the image in case it was updated
print("Getting the latest dotrun-image...")
docker_client.images.pull(
    repository="canonicalwebteam/dotrun-image", tag="latest"
)


def cli():
    command = ["dotrun"]
    command.extend(sys.argv[1:])

    try:
        container = docker_client.containers.create(
            image="canonicalwebteam/dotrun-image",
            name=f"dotrun-{project_name}",
            volumes={
                absolute_path: {
                    "bind": container_path,
                    "mode": "rw",
                }
            },
            working_dir=container_path,
            environment=[f"DOTRUN_VERSION={__version__}"],
            stdin_open=True,
            tty=True,
            command=command,
            ports={project_port: project_port},
        )

        dockerpty.start(docker_client.api, container.id)
    except KeyboardInterrupt:
        container.stop()
        container.remove()

    container.stop()
    container.remove()
