## Installation

``` bash
snap install dotrun
```

OR

``` bash
multipass launch bionic dotrun
multipass exec dotrun -- sudo snap install dotrun
multipass mount $HOME dotrun
alias dotrun='multipass exec dotrun -- /snap/bin/dotrun -C `pwd`'
```
