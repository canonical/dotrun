![dotrun](https://assets.ubuntu.com/v1/9dcb3655-dotrun.png?w=200)

# A tool for developing Node.js and Python projects

`dotrun` makes use of [snap confinement](https://snapcraft.io/docs/snap-confinement) to provide a predictable sandbox for running Node and Python projects.

Features:

- Make use of standard `package.json` script entrypoints:
  * `dotrun` runs `yarn run start` within the snap confinement
  * `dotrun foo` runs `yarn run foo` within the snap confinement
- Detect changes in `package.json` and only run `yarn install` when needed
- Detect changes in `requirements.txt` and only run `pip3 install` when needed
- Run scripts using environment variables from `.env` and `.env.local` files
- Keep python dependencies in `.venv` in the project folder for easy access

## Usage

``` bash
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

``` bash
sudo snap install dotrun
```

## Converting existing projects

Although you should be able to use `dotrun` out-of-the-box in most of our pure-Node or Python projects as follows:

``` bash
dotrun build
dotrun serve
```

To fully support it you should do the following:

- Add `.dotrun.json` and `.venv` to `.gitignore`
- Swap `0.0.0.0` with `$(hostname -I | awk '{print $1;}')` in `package.json`
  - This will allow macOS users to click on the link in the command-line output to find the development server
- Create a `start` script in `package.json` to do everything needed to set up local development. E.g.:
  `"start": "concurrently 'yarn run watch' 'yarn run serve'"`
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

``` bash
python3 -m venv .venv  # Create a python environment for testing
source .venv/bin/activate
pip3 install -e .  # Install the dotrun module as a python package
python3 -m unittest discover --start-directory tests  # Run the tests against the installed python package
```

### Testing the snap

To do a complete test, it's wise to build the snap from the current codebase and then test the snap itself.

If you have [multipass](https://multipass.run/) installed, you can do this using multipass for confinement pretty simply:

``` bash
scripts/test-snap-using-multipass
```

This runs the same tests in the `tests` directory against an actual snap installed into multipass.


### Automated tests of pull requests

[The "PR" action](.github/workflows/pr.yml) builds the snap and runs the `tests`, similar to the "multipass" solution above. This will run against every pull request.
