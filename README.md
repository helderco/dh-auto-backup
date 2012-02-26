# Dreamhost Auto Backup

Good backup systems need to be automatic. I needed a simple script to backup all mysql databases and user files on my Dreamhost account. This is my attempt to automate this process as much as possible.

You can read more from Dreamhost's Personal Backups at <http://wiki.dreamhost.com/Personal_Backup>

*Note: this script is yet under the early stages of development. All planned features are recorded in the [issues section](https://github.com/helderco/dh-auto-backup/issues?milestone=1). See how you can contribute below.*


## Requirements

* Activate your dreamhost [backups user account](http://wiki.dreamhost.com/Personal_Backup);

* Set up [passwordless login](http://wiki.dreamhost.com/Ssh#Passwordless_Login) between your main account and the backups server;

* Create an [API](http://wiki.dreamhost.com/Api) key with the following functions:
  [user-list_users](http://wiki.dreamhost.com/Api#user-list_users),
  [mysql-list_users](http://wiki.dreamhost.com/Api#mysql-list_users);

I also recommend creating a separate mysql user with only `SELECT` permissions and add it to any database that you wish to backup.


## Usage

Download the script and put it anywhere you want.

Edit the file and replace `key` with your Dreamhost API key, `db_user` and `db_pass` with your mysql backups user access  as recommended above, and `backup_dir` with the location where the mysql backups should be saved (relative to the script or absolute).

### To run with default python from Dreamhost

Make sure it's executable

`$ chmod u+x path/to/script`

Run directly

`$ path/to/script`

### To run with a different python binary

`$ path/to/python path/to/script`


## Make it run automatically

The whole idea is to make the script run daily or at another set period. Create a [cronjon](http://wiki.dreamhost.com/Goodies_Control_Panel#Cron_Jobs), and optionally receive a report by email each time it's run.


## Contribute

I'm interested in community improvements, so be free to [contribute](http://help.github.com/send-pull-requests/). You can also submit feature requests and report any issues or bugs with the script in the [issues section](https://github.com/helderco/dh-auto-backup/issues).


## Guidelines

I'm taking a few guidelines in consideration for writing this script.

* Make it compatible with Python 2.5, since at this time it's what you have by default from Dreamhost.
* Avoid as much as possible external dependencies. This way the user doesn't need to install anything else.
* Make it a single script:
  * freedom to move the file around without having to have a group of files  under the same subdirectory;
  * configuration file should be able to be found on a few standard places (i.e., user's home dir, script's dir).

