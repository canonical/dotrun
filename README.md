## Installation

``` bash
snap install --beta dotrun
```

OR

``` bash
multipass launch -n dotrun bionic
multipass exec dotrun -- sudo snap install --beta dotrun
multipass mount $HOME dotrun
alias dotrun='multipass exec dotrun -- /snap/bin/dotrun -C `pwd`'
```
