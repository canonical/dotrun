![dotrun](https://assets.ubuntu.com/v1/9dcb3655-dotrun.png?w=200)

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
$ dotrun clean    # Delete `node_modules`, `.venv`, `.dotrun.json`, and run `yarn run clean`
$ dotrun install  # Force install node and python dependencies
$ dotrun exec     # Start a shell inside the dotrun environment
$ dotrun exec {command}          # Run {command} inside the dotrun environment
$ dotrun {script-name}           # Install dependencies and run `yarn run {script-name}`
$ dotrun -s {script}             # Run {script} but skip installing dependencies
$ dotrun --env FOO=bar {script}  # Run {script} with FOO environment variable
```

## Installation

To install dotrun run:
```
sudo pip3 install dotrun
```

### Requirements

- Linux / macOS
- Docker ([Get Docker](https://docs.docker.com/get-docker/))
- Python > 3.6 and PIP

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
