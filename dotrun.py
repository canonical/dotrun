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
from dotenv import dotenv_values
from slugify import slugify

__version__ = metadata.version("dotrun")


class Dotrun:
    BASE_IMAGE_NAME = "canonicalwebteam/dotrun-image:latest"

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
            self.docker_client.images.get(self.BASE_IMAGE_NAME)
            # Pull the image in the background
            print("Checking for dotrun image updates...")
            threading.Thread(target=self._pull_image)
        except docker.errors.ImageNotFound:
            print("Getting the dotrun image...")
            self._pull_image()

    def _pull_image(self, image_name=None, exit_on_download_error=True):
        """Pull the dotrun image (if updated) from Docker Hub"""
        if not image_name:
            image_name = self.BASE_IMAGE_NAME
        image_uri = self._get_image_name(image_name)
        repository, tag = image_uri.split(":")
        try:
            self.docker_client.images.pull(repository=repository, tag=tag)
        except (docker.errors.APIError, docker.errors.ImageNotFound) as e:
            print(f"Unable to download image: {image_name}")
            # Optionally quit if image download fails
            if exit_on_download_error:
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
                self.BASE_IMAGE_NAME,
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
            image_name = self.BASE_IMAGE_NAME
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


def _extract_cli_command_arg(pattern, command_list):
    """
    Return the value from the format

    --command <value>

    and remove the command from the command list.
    """
    pattern = re.compile(f"--{pattern} [^\s]+")  # noqa
    if match := re.search(pattern, " ".join(command_list)):
        # Extract the value from the cli arg
        command_arg = match.group(0)
        try:
            value = command_arg.split(" ")[1]
        except IndexError:
            print(f"Value for arg {command_arg} not supplied.")
            sys.exit(1)

        # Remove the command from command list
        new_command_list = (
            " ".join(command_list).replace(command_arg, "").replace("  ", " ")
        )
        return value, new_command_list.split(" ")
    return None


def _handle_image_cli_param(dotrun, command_list):
    """
    Handle the --image cli parameter, if supplied, and return the
    created container and the modified command list.
    """
    if result := _extract_cli_command_arg("image", command_list):
        image_name, commands = result
        # Sanitize the image name
        image_name = dotrun._get_image_name(image_name)
        return (
            _start_container_with_image(dotrun, image_name, commands),
            commands,
        )


def _handle_release_cli_param(dotrun, command_list):
    """
    Handle the --release cli parameter, if supplied, and return the
    created container and the modified command list.
    """
    if result := _extract_cli_command_arg("release", command_list):
        image_tag, commands = result
        # Get the release image uri
        image_name, _ = dotrun.BASE_IMAGE_NAME.split(":")
        image_tag = f"{image_name}:{image_tag}"
        return (
            _start_container_with_image(dotrun, image_tag, commands),
            commands,
        )


def _start_container_with_image(dotrun, image_uri, command_list):
    """
    Utility function to start dotrun using a specified
    image.
    """

    print(f"Using image: {image_uri}")

    # Download the image
    dotrun._pull_image(image_uri, exit_on_download_error=True)

    # Start dotrun from the supplied base image
    try:
        return dotrun.create_container(command_list, image_name=image_uri)
    except docker.errors.ImageNotFound as e:
        print(e)
        sys.exit(1)


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

    # Options for starting the container using different base images
    if result := _handle_image_cli_param(dotrun, command):
        container, command = result
    elif result := _handle_release_cli_param(dotrun, command):
        container, command = result
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
