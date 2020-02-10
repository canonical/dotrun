## Installation

``` bash
snap install --beta --devmode dotrun
```

OR

``` bash
multipass launch -n dotrun bionic
multipass exec dotrun -- sudo snap install --beta --devmode dotrun
multipass mount $HOME dotrun
alias dotrun='multipass exec dotrun -- /snap/bin/dotrun -C `pwd`'
```

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


### GitHub actions

We've [set up GitHub actions](.github/workflows/test-snap.yml) to build the snap and fully test it using the `tests`, similar to the "multipass" solution above. This will run against every pull request.
