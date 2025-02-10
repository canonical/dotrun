<img src="https://assets.ubuntu.com/v1/14a3bac5-dotrun.svg?w=200" width="200" alt="dotrun" />

# A tool for developing Node.js and Python projects

`dotrun` makes use of a [Docker image](https://github.com/canonical/dotrun-image/) to provide a predictable sandbox for running Node and Python projects.

Features:

- Make use of standard `package.json` script entrypoints:
  - `dotrun` runs `yarn run start` within the Docker container
  - `dotrun foo` runs `yarn run foo` within the Docker container
- Detect changes in `package.json` and only run `yarn install` when needed
- Detect changes in `requirements.txt` and only run `pip3 install` when needed
- Run scripts using environment variables from `.env` and `.env.local` files
- Keep python dependencies in `.venv` in the project folder for easy access

## Usage

```bash
$ dotrun          # Install dependencies and run the `start` script from package.json
$ dotrun serve    # Run the python app only
$ dotrun clean    # Delete `node_modules`, `.venv`, `.dotrun.json`, and run `yarn run clean`
$ dotrun install  # Force install node and python dependencies
$ dotrun exec     # Start a shell inside the dotrun environment
$ dotrun exec {command}          # Run {command} inside the dotrun environment
$ dotrun {script-name}           # Install dependencies and run `yarn run {script-name}`
$ dotrun -s {script}             # Run {script} but skip installing dependencies
$ dotrun --env FOO=bar {script}  # Run {script} with FOO environment variable
$ dotrun -m "/path/to/mount":"localname"       # Mount additional directory and run `dotrun`
$ dotrun serve -m "/path/to/mount":"localname" # Mount additional directory and run `dotrun serve`
$ dotrun refresh image # Download the latest version of dotrun-image
$ dotrun --release {release-version} # Use a specific image tag for dotrun. Useful for switching versions
$ dotrun --image {image-name} # Use a specific image for dotrun. Useful for running dotrun off local images
$ dotrun use python 3.8 && dotrun clean && dotrun install # Use a specific python version for dotrun.
```

- Note that the `--image` and `--release` arguments cannot be used together, as `--image` will take precedence over `--release`

## Installation

### Requirements

- Docker ([Get Docker](https://docs.docker.com/get-docker/)): on Linux, you can install the [Docker snap](https://snapcraft.io/docker) instead.
- Python 3.10 or later
- On MacOS: [Homebrew](https://docs.brew.sh/Installation) is required
- `curl` command-line tool (usually pre-installed on macOS and most Linux distributions)

### Linux and MacOS

#### Quick installation

To install dotrun simply run:

```bash
curl -sSL https://raw.githubusercontent.com/canonical/dotrun/main/scripts/install.sh | bash
```

### Verifying the Installation

After installation, you can verify that `dotrun` is installed correctly by running:

```bash
dotrun version
```

### Manual Installation

If you prefer to install manually or encounter any issues with the installation script, you can install `dotrun` using the following steps:

1. Install `pipx` if you haven't already:

   - On macOS: `brew install pipx`
   - On Linux: Follow the installation instructions for your distribution from the [pipx documentation](https://pypa.github.io/pipx/installation/)

2. Ensure `pipx` is in your PATH:

```bash
pipx ensurepath
```

1. Install `dotrun` using `pipx`:

```bash
pipx install dotrun
```

If you experience problems, please open a GitHub issue.

### macOS performance

For optimal performance on Docker we recommend enabling a new experimental file sharing implementation called virtiofs. Virtiofs is only available to users of the following macOS versions:

- macOS 12.2 and above (for Apple Silicon)
- macOS 12.3 and above (for Intel)

[How to enable virtiofs](https://www.docker.com/blog/speed-boost-achievement-unlocked-on-docker-desktop-4-6-for-mac/)

## Add dotrun on new projects

To fully support dotrun in a new project you should do the following:

- For Python projects, ensure [Talisker](https://pypi.org/project/talisker/) is at `0.16.0` or greater in `requirements.txt`
- Add `.dotrun.json` and `.venv` to `.gitignore`
- Create a `start` script in `package.json` to do everything needed to set up local development. E.g.:
  `"start": "concurrently --raw 'yarn run watch' 'yarn run serve'"`
  - The above command makes use of [concurrently](https://www.npmjs.com/package/concurrently) - you might want to consider this
- Older versions of Gunicorn [are incompatible with](https://forum.snapcraft.io/t/problems-packaging-app-that-uses-gunicorn/11749) strict confinement so we need Gunicorn >= 20
  - The update [landed in Talisker](https://github.com/canonical-ols/talisker/pull/502) but at the time of writing hasn't made it into a new version
  - If there's no new version of Talisker, simply add `gunicorn==20.0.4` to the bottom of `requirements.txt`

However, once you're ready to completely switch over to `dotrun`, simply go ahead and remove the `run` script.

### Automated tests of pull requests

[The "PR" action](.github/workflows/pr.yaml) builds the Python package and runs a project with dotrun. This will run against every pull request.

### Publish

All the changes made to the main branch will be automatically published as a new version on PyPI.

To publish a new version manually, run:

```
docker buildx create --name mybuilder
docker buildx use mybuilder
docker buildx build --push --platform linux/arm/v7,linux/arm64/v8,linux/amd64 --tag canonicalwebteam/dotrun-image:latest .
```

## Hacking

You can install the package locally using either pip or poetry.

### Using pip

```bash
pip3 install . requests==2.31.0
```

### Using Poetry

```bash
pip install poetry
poetry install --no-interaction
```

To run dotrun off alternative base images such as local images, you can use the `--image` flag.

```bash
dotrun --image "localimage" exec echo hello
```

To run dotrun off alternative releases, besides the `:latest` release, you can use the `--release` flag.

```bash
dotrun --release "latest" serve
```

Note that before changing the base image you should run

```bash
dotrun clean
```

to get rid of the old virtualenv.
