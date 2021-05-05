![dotrun](https://assets.ubuntu.com/v1/9dcb3655-dotrun.png?w=200)

# A tool for developing Node.js and Python projects

[![dotrun](https://snapcraft.io//dotrun/badge.svg)](https://snapcraft.io/dotrun)

`dotrun` makes use of [snap confinement](https://snapcraft.io/docs/snap-confinement) to provide a predictable sandbox for running Node and Python projects.

Features:

- Make use of standard `package.json` script entrypoints:
  - `dotrun` runs `yarn run start` within the snap confinement
  - `dotrun foo` runs `yarn run foo` within the snap confinement
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

### Ubuntu

```bash
sudo snap install dotrun
sudo snap connect dotrun:dot-npmrc
sudo snap connect dotrun:dot-yarnrc
```

Note: The `dotrun:dot-npmrc` and `dotrun:dot-yarnrc` [plugs](https://snapcraft.io/docs/interface-management) gives the snap access to read the `~/.npmrc` and `~/.yarnrc` files in your home directory. This is only necessary if you have these files on your system, but if they do exist, the snap will fail to run `yarn` unless it's given access.

### MacOS

On MacOS, `dotrun` should be installed and run inside [a multipass VM](https://multipass.run/), using `sudo snap install dotrun` as above. Any server running within the multipass VM will then be available at the VM's IP address, which can be obtained from `multipass list`.

Given that file access over a virtual network share [is incredibly slow](https://forums.docker.com/t/file-access-in-mounted-volumes-extremely-slow-cpu-bound/8076) in MacOS, it is recommended to keep your project files inside the multipass VM directly and then share them with your host system from there if you want to open them in a graphical editor.

See @hatched's [guide](https://fromanegg.com/post/2020/02/28/use-ubuntu-on-mac-os-with-multipass/) for how to achieve this setup.

#### Automated installation with Multipass

We are maintaining a bash script that will install Multipass in your system and configure your machine to proxy the dotrun command to a Multipass instance.

To use it:
```bash
curl -s https://raw.githubusercontent.com/canonical-web-and-design/dotrun/master/scripts/install-with-multipass.sh | bash
```

It will create a `dotrun-projects` folder in your home directory, you can clone projects here and use `dotrun` transparently.

## Converting existing projects

On the whole, our existing projects should run out of the box with:

```bash
dotrun build
dotrun serve
```

A caveat to this for our Python website projects is that `dotrun` will only work with [Gunicorn](https://pypi.org/project/gunicorn/) >= `20.0.0`. To achieve this, our projects should upgrade to using at least version `0.4.3` of [flask-base](https://github.com/canonical-web-and-design/canonicalwebteam.flask-base/).

**Updating projects**

To fully support it you should do the following:

- For Python projects, ensure [Talisker](https://pypi.org/project/talisker/) is at `0.16.0` or greater in `requirements.txt`
- Add `.dotrun.json` and `.venv` to `.gitignore`
- Create a `start` script in `package.json` to do everything needed to set up local development. E.g.:
  `"start": "concurrently --raw 'yarn run watch' 'yarn run serve'"`
  - The above command makes use of [concurrently](https://www.npmjs.com/package/concurrently) - you might want to consider this
- Older versions of Gunicorn [are incompatible with](https://forum.snapcraft.io/t/problems-packaging-app-that-uses-gunicorn/11749) strict confinement so we need Gunicorn >= 20
  - The update [landed in Talisker](https://github.com/canonical-ols/talisker/pull/502) but at the time of writing hasn't made it into a new version
  - If there's no new version of Talisker, simply add `gunicorn==20.0.4` to the bottom of `requirements.txt`

These steps can be completed without effecting the old `./run` script, which should continue working.

However, once you're ready to completely switch over to `dotrun`, simply go ahead and remove the `run` script.

## Testing

The `test` folder contains a bunch of tests, written in Python, against the `dotrun` binary, using example projects in the `test/fixtures` folder.

These tests can be run against the current codebase in a couple of different ways:

### Testing the python module

This is the quickest way to test the code, but it's not as complete as it won't find error that might relate to the snap confinement.

```bash
python3 -m venv .venv  # Create a python environment for testing
source .venv/bin/activate
pip3 install -e .  # Install the dotrun module as a python package
python3 -m unittest discover --start-directory tests  # Run the tests against the installed python package
```

### Testing the snap

To do a complete test, it's wise to build the snap from the current codebase and then test the snap itself.

If you have [multipass](https://multipass.run/) installed, you can do this using multipass for confinement pretty simply:

```bash
scripts/test-snap-using-multipass
```

This runs the same tests in the `tests` directory against an actual snap installed into multipass.

### Automated tests of pull requests

[The "PR" action](.github/workflows/pr.yml) builds the snap and runs the `tests`, similar to the "multipass" solution above. This will run against every pull request.
