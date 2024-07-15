#! /usr/bin/env python3

import os
import platform
import re
import sys
import time
import threading
from importlib import metadata

# Packages
import docker
import dockerpty
import requests
from dotenv import dotenv_values
from slugify import slugify

__version__ = metadata.version("dotrun")


class Dotrun:
    base_image_name = "canonicalwebteam/dotrun-image:latest"

    def __init__(self):
        self.cwd = os.getcwd()
        self.project_name = slugify(os.path.basename(self.cwd))
        self.project_port = dotenv_values(".env").get("PORT", 8080)
        self.container_home = "/home/ubuntu/"
        self.container_path = f"{self.container_home}{self.project_name}"
        # --network host is only supported on Linux
        self.network_host_mode = (
            sys.platform.startswith("linux")
            and "microsoft" not in platform.platform()
        )
                
        self._get_docker_client()
        self._check_image_updates()
        self._create_cache_volume()
    
    def _get_release_image_name(self, image_tag="latest"):
        """
        Return the image name with the tag in the format
        canonicalwebteam/dotrun-image:<release_tag>
        """
        base_image = self.base_image_name.split(":")[0]
        return f"{base_image}:{image_tag}"
    
    def _get_image_name(self, image_name):
        """
        Return a fully qualified image name from a given image 
        name, defaulting to the :latest tag if none is provided.
        """
        if ":" not in image_name:
            return image_name + ":latest"
        return image_name

    def _get_docker_client(self):
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()
        except (docker.errors.APIError, docker.errors.DockerException) as e:
            print(e)
            print(
                "Dotrun needs Docker to work, please check"
                " if Docker is installed and running"
            )
            sys.exit(1)

    def _check_image_updates(self):
        try:
            self.docker_client.images.get(
                self.base_image_name
            )
            # Pull the image in the background
            print("Checking for dotrun image updates...")
            threading.Thread(target=self._pull_image)
        except docker.errors.ImageNotFound:
            print("Getting the dotrun image...")
            self._pull_image()

    def _pull_image(self, image_name=None, no_exit=False):
        """Pull the dotrun image (if updated) from Docker Hub"""
        if not image_name:
            image_name = self.base_image_name
        image_uri = self._get_image_name(image_name)      
        repository, tag = image_uri.split(":")
        try:
            self.docker_client.images.pull(
                repository=repository, tag=tag
            )
        except (docker.errors.APIError, docker.errors.ImageNotFound) as e:
            print(f"Unable to download image: {image_name}")
            # Optionally quit if image download fails
            if not no_exit:
                print(e)
                sys.exit(1)
            print(f"Attempting to use local image: {image_name}")

    def _create_cache_volume(self):
        try:
            self.docker_client.volumes.get("dotrun-cache")
        except docker.errors.NotFound:
            self.docker_client.volumes.create(name="dotrun-cache")

            # We need to fix the volume ownership
            self.docker_client.containers.run(
                self.base_image_name,
                f"chown -R ubuntu:ubuntu {self.container_home}.cache",
                user="root",
                mounts=self._prepare_mounts([]),
                remove=True,
            )

    def _prepare_mounts(self, command):
        mounts = [
            docker.types.Mount(
                target=f"{self.container_home}.cache",
                source="dotrun-cache",
                type="volume",
                read_only=False,
                consistency="delegated",
            ),
            docker.types.Mount(
                target=self.container_path,
                source=self.cwd,
                type="bind",
                read_only=False,
                # See https://tkacz.pro/docker-volumes-cached-vs-delegated/
                consistency="cached",
            ),
        ]

        additional_mounts = self._get_additional_mounts(command)
        if additional_mounts:
            for mount in additional_mounts:
                mounts.append(
                    docker.types.Mount(
                        target=f"{self.container_path}/{mount[1]}",
                        source=f"{mount[0]}",
                        type="bind",
                        read_only=False,
                        consistency="cached",
                    )
                )
        return mounts

    def _get_container_name(self, command=None):
        """
        Return a simple name to easily identify the container on Docker
        """
        name = ["dotrun"]

        if self.project_name:
            name.append(self.project_name)

        if command:
            name.append(slugify(command))

        # Timestamp so we don't get name collisions
        name.append(str(int(time.time())))

        name = "-".join(name)

        # Remove duplicated hyphens
        return re.sub(r"(-)+", r"\1", name)

    def _get_additional_mounts(self, command):
        """
        Return a list of additional mounts
        """
        if "-m" not in command:
            return

        def get_mount(command, mounts):
            mount_index = command.index("-m")
            mount_string = command[mount_index + 1]
            del command[mount_index]
            if ":" in mount_string:
                mount_parts = mount_string.split(":")
                mounts.append(mount_parts)
                del command[mount_index]

            if "-m" in command:
                mounts = get_mount(command, mounts)

            return mounts

        return get_mount(command, [])

    def create_container(self, command, image_name=None):
        if not image_name:
            image_name = self.base_image_name
        ports = {self.project_port: self.project_port}
        # Run on the same network mode as the host
        network_mode = None
        if command[1:]:
            first_cmd = command[1:][0]

            # Avoid port conflict when running multiple commands
            if first_cmd not in ["start", "serve", "-m"]:
                ports = {}

            # Set a different container name to run a specific command
            name = self._get_container_name(first_cmd)
        else:
            name = self._get_container_name()
        if self.network_host_mode:
            # network_mode host is incompatible with ports option
            ports = None
            network_mode = "host"
        
        return self.docker_client.containers.create(
            image=image_name,
            name=name,
            hostname=name,
            mounts=self._prepare_mounts(command),
            working_dir=self.container_path,
            environment=[f"DOTRUN_VERSION={__version__}"],
            stdin_open=True,
            tty=True,
            command=command,
            ports=ports,
            network_mode=network_mode,
        )

def _start_container_with_image(dotrun, command_list, command_match, format="tag"):
    """
    Utility function to start dotrun using a specified 
    image.
    """
    # Extract the argument from the cli arg
    image_command = command_match.group(0)
    try:
        image_data = image_command.split(' ')[1]
    except IndexError:
        print("Image name not supplied.")
        sys.exit(1)

    # Determine the image name
    if format == "release":
        image_uri = dotrun._get_release_image_name(image_data)
    else:
        image_uri = dotrun._get_image_name(image_data) 
    print(f"Using image: {image_uri}")

    # Download the image
    dotrun._pull_image(image_uri, no_exit=True)
    
    # Remove the image command from command list
    new_command_list = ' '.join(command_list).replace(image_command, '').replace('  ', ' ')
    command_list = new_command_list.split(' ')

    # Start dotrun from the supplied base image
    return dotrun.create_container(command_list, image_name=image_uri)

def cli():
    dotrun = Dotrun()
    command = ["dotrun"]
    command.extend(sys.argv[1:])

    if command[-1] == "version":
        print(f"dotrun v{__version__}")
        sys.exit(1)
    
    if command[-1] == "refresh":
        dotrun._pull_image()
        print("Latest image pulled successfully.")
        sys.exit(1)
    
    # Options for starting the container on different base images
    if match := re.search(r'--image [^\s]+', ' '.join(command)):
        container = _start_container_with_image(dotrun, command, match)
    elif match := re.search(r'--release [^\s]+', ' '.join(command)):
        container = _start_container_with_image(dotrun, command, match, format="release")
    else:
        container = dotrun.create_container(command)

    # 1 by default
    status_code = 1

    try:
        dockerpty.start(dotrun.docker_client.api, container.id)
        status_code = container.wait().get("StatusCode", 1)
    finally:
        container.stop()
        container.remove()

    return status_code

if __name__ == "__main__":
    cli()