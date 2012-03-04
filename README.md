# Dreamhost Auto Backup

Good backup systems need to be automatic. I needed a simple script to backup all mysql databases and user files on my Dreamhost account. This is my attempt to automate this process as much as possible.

You can read more from Dreamhost's Personal Backups at <http://wiki.dreamhost.com/Personal_Backup>.

*Note: this script is yet under the early stages of development. All planned features are recorded in the [issues section](https://github.com/helderco/dh-auto-backup/issues?milestone=1). See how you can contribute below.*


## Requirements

1. Create an [API key](http://wiki.dreamhost.com/Api) with the following functions:
  [user-list_users](http://wiki.dreamhost.com/Api#user-list_users),
  [mysql-list_users](http://wiki.dreamhost.com/Api#mysql-list_users);
2. Activate your dreamhost [backups user account](http://wiki.dreamhost.com/Personal_Backup);
3. Set up [passwordless login](http://wiki.dreamhost.com/Ssh#Passwordless_Login) between your main account and the backups server;

I also recommend creating a separate mysql user with only `SELECT` permissions and add it to any database that you wish to backup.


## Installation

The quick summary is as follows:

1. Download the script and put it anywhere you want.
2. Configure using command line options or a configuration file.
3. Schedule the backup with a [cron job]().


## Download

You can download the zipball/tarball from [github](), or the script file directly from the tree, but the prefered way is to do a git clone. This way it's easy to stay up to date.

### Example

    mkdir -p ~/scripts
    cd ~/scripts
    git clone https://github.com/helderco/dh-auto-backup.git

### Update

    cd ~/scripts/dh-auto-backup
    git pull

### Run from anywhere (optional)

If you already have a `$PATH` accessible folder in your home, skip the first two commands.

    mkdir -p ~/bin
    echo 'export PATH="$PATH:~/bin"' >> ~/.bash_profile

    ln -s ~/scripts/dh-auto-backup/dhbackup.py ~/bin/dhbackup


## Configure

The script is configurable through command line options, configuration files, or both. If both are provided, command line options override configuration file options.

### Command line

The command line interface provides a basic configuration mechanism to avoid having to store passwords and other sensitive information in configuration files.

The simplest setup is to create a mysql user for backups only and assign it to any database you want to backup. Then provide the authentication to the script:

    dhbackup -u user_backups -p s3cr3tp4 -k 6SHU5P2HLDAYECUM

Run win **`dhbackup -h`** for available options.

### Configuration file

A configuration file has more options. Read the `dhbackup.cfg.sample` file for instructions.


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


[github]: https://github.com/helderco/dh-auto-backup
[cronjon]: http://wiki.dreamhost.com/Goodies_Control_Panel#Cron_Jobs
