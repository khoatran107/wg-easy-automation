# wg-easy-automation

## Installation

### Clone and edit info.txt
```bash
git clone https://github.com/khoatran107/wg-easy-automation.git
cd ./wg-easy-automation
```
Edit the `info.txt` file:
```
# change this to your server's public IP
IP=192.168.1.1
# change this to your wg-easy password
password=123123123
```

### Install google-chrome
```bash
sudo apt update
sudo apt upgrade

wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt-get install -y ./google-chrome-stable_current_amd64.deb
google-chrome --version
```

### Set up python venv
```bash
python3 -m venv env
pip install -r requirements.txt
```

## Usage
```
usage: python3 solve.py [-h] {add-list,add-one,download-list,download-one} ...

Web automation tool for managing configurations.

positional arguments:
  {add-list,add-one,download-list,download-one}
                        Operation mode
    add-list            Add names from a file
    add-one             Add a single name
    download-list       Download configurations from file
    download-one        Download single configuration

options:
  -h, --help            show this help message and exit
```

## Examples:
`users.txt`:
```
team_01-mem_01
team_01-mem_02
team_01-mem_03
team_02-mem_01
team_02-mem_02
team_02-mem_03
```
Commands:
```bash
python3 solve.py add-list ./users.txt
python3 solve.py download-list ./users.txt
# saves 6 files team_0x-mem_0y.conf in ./config_files/

python3 solve.py add-one ktranowl
python3 solve.py download-one ktranowl
# saved as ./config_files/ktranowl.conf
```
## Note
Make sure that `users.txt` file contains unique names. If not, the script adds all duplicate names, but only download the first one added.
