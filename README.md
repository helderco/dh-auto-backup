# Dreamhost Auto Backup

Good backup systems need to be automatic. I needed a simple script to backup all mysql databases and user files on my Dreamhost account. This is my attempt to automate this process as much as possible.

You can read more from Dreamhost's Personal Backups at <http://wiki.dreamhost.com/Personal_Backup>.

*Note: this script is yet under the early stages of development. All planned features are recorded in the [issues section](https://github.com/helderco/dh-auto-backup/issues?milestone=1). See how you can contribute below.*


## Requirements

* Activate your dreamhost [backups user account](http://wiki.dreamhost.com/Personal_Backup);
* Set up [passwordless login](http://wiki.dreamhost.com/Ssh#Passwordless_Login) between your main account and the backups server;
* Create an [API](http://wiki.dreamhost.com/Api) key with the following functions:
  [user-list_users](http://wiki.dreamhost.com/Api#user-list_users),
  [mysql-list_users](http://wiki.dreamhost.com/Api#mysql-list_users);

I also recommend creating a separate mysql user with only `SELECT` permissions and add it to any database that you wish to backup.


## Usage

1. Download the script and put it anywhere you want.

2. Provide the script with a mysql user and password to backup the databases the user has access to (see my recommendation above for a dedicated backups user).

Optionally provide a local directory where dumps should be saved (defaults to `~/backups/mysql`).

## Example

The following commands are provided as examples. You should replace names accordingly.

### Download

    mkdir -p scripts
    cd scripts
    git clone https://github.com/helderco/dh-auto-backup.git

### Run from anywhere

If you already have a `$PATH` accessible folder in your home, skip the first two commands.

    mkdir -p ~/bin
    echo 'export PATH="$PATH:~/bin"' >> ~/.bash_profile

    ln -s ~/scripts/dh-auto-backup/dhbackup.py ~/bin/dhbackup

### Usage: see available options

    dhbackup -h

### Usage: backup

    dhbackup -u user_backups -p s3cr3tp4 6SHU5P2HLDAYECUM

### Update

    cd ~/scripts/dh-auto-backup
    git pull

## Make it run automatically

The whole idea is to make the script run daily or at another set period. Create a [cronjon](http://wiki.dreamhost.com/Goodies_Control_Panel#Cron_Jobs), and optionally receive a report by email each time it's run.


## Contribute

I'm interested in community improvements, so be free to [contribute](http://help.github.com/send-pull-requests/). You can also submit feature requests and report any issues or bugs with the script in the [issues section](https://github.com/helderco/dh-auto-backup/issues).


### Guidelines

I'm taking a few guidelines in consideration for writing this script.

* Make it compatible with Python 2.5, since at this time it's what you have by default.
* Avoid as much as possible external dependencies. This way the user doesn't need to install anything else.
* Make it a single script:
  * freedom to move the file around without having to have a group of files  under the same subdirectory;
  * configuration file should be able to be found on a few standard places (i.e., user's home dir, script's dir).

