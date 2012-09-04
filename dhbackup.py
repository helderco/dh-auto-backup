#!/usr/bin/env python

"""Dreamhost Auto Backup

Good backup systems need to be automatic. This is an attempt to automate
as much as possible the process of backing up all mysql databases and
user files under a Dreamhost account.

You can read more from Dreamhost's Personal Backups at
<http://wiki.dreamhost.com/Personal_Backup>.

You should have received a copy of the README.md file along with this
script. If not, go to https://github.com/helderco/dh-auto-backup for
more information.
"""

__version__ = '0.4.1'

__copyright__ = """
Copyright (c) 2012 Helder Correia <helder.mc@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

_title = "Dreamhost Auto Backup"

_copyright_short = """
Copyright (c) 2012 Helder Correia
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
"""

import os
import sys
import time
from uuid import uuid4
from urllib import urlencode
from urllib2 import urlopen
from subprocess import Popen, PIPE
from bz2 import BZ2File
from optparse import OptionParser, OptionGroup
from ConfigParser import SafeConfigParser, NoSectionError, NoOptionError


class DreamhostAPI(object):
    requests = {}

    def __init__(self, key, url="https://api.dreamhost.com"):
        self.url = url
        self.key = key

    def request(self, cmd, **kwargs):
        if cmd in self.requests:
            self.requests.get(cmd)

        params = {'cmd': cmd, 'key': self.key, 'unique_id': str(uuid4())}
        params.update(kwargs)
        connection = urlopen(self.url, urlencode(params))
        response = Response(connection, cmd)

        self.requests[cmd] = response
        return response


class Response(object):
    """Response object (urllib2.urlopen) from an API request.

    Example data for command 'user-list_users':

    username |  type  |     shell     | home
    ---------+--------+---------------+----------------------
    apts718  | shell  | /usr/bin/bash | angel.dreamhost.com
    b1       | backup | /usr/bin/rssh | hanjin.dreamhost.com
    re432t3  | shell  | /usr/bin/bash | angel.dreamhost.com
    t43t24t  | ftp    | /etc/ftponly  | angel.dreamhost.com
    """

    def __init__(self, response, cmd):
        self.cmd = cmd
        self.raw = response
        self.data = []
        self.success = False
        self.parse(response)

    def parse(self, response):
        """Parse a tab based response with data into a dictionary."""
        lines = [line.strip() for line in response.readlines()]
        self.success = lines[0] == 'success'

        if not self.success:
            print >> sys.stderr, "Error (%s): %s" % (self.cmd, lines[1])
            return False

        keys = lines[1].split('\t')
        for line in lines[2:]:
            values = line.split('\t')
            self.data.append(dict(zip(keys, values)))

        return True

    def filter(self, prop):
        """Filter the list of items by a single column (prop).

        Example:
        filter('username'): ['apts718', 'b1', 're432t3', 't43t24t']
        """
        result = []
        for item in self.data:
            result.append(item[prop])
        return result

    def find(self, prop, value, return_prop=None):
        """Find the first item for a given property and value.

        Example 1:
        find('type', 'backup'): {
            'username': 'b1',
            'type': 'backup',
            'shell': '/usr/bin/rssh',
            'home': 'hanjin.dreamhost.com'
        }

        Optionally return only one property.

        Example 2:
        find('type', 'backup', 'username'): 'b1'
        """
        result = self.list(prop, value, return_prop)
        return result[0] if len(result) > 0 else None

    def list(self, prop, value, return_prop=None):
        """Return a list of items for a given property and value.

        This is the same as find(), but returns all matches,
        not only the first one.
        """
        result = []
        for item in self.data:
            if item[prop] == value:
                result.append(item if not return_prop else item[return_prop])
        return result

    def __repr__(self):
        return repr(self.raw)


class Backup(object):
    _account = None

    def __init__(self, api, config):
        self.api = api
        self.config = config

    @property
    def account(self):
        if self._account is None:
            users = api.request('user-list_users')

            if not users.success:
                self.config.warning("Unable to access users list")
                return False

            self._account = users.find('type', 'backup') or False

        return self._account

    def mysql(self):
        if self.config.skip_mysql:
            return False

        self.mysql_dumps()
        self.mysql_rsync()

    def mysql_dumps(self):
        if self.config.skip_mysql_dumps:
            return False

        users = api.request('mysql-list_users')
        if not users.success:
            self.config.warning("could not retrieve mysql users list")
            return False

        print "Backing up databases..."

        done = set()
        for db in users.data:
            if db['db'] in done:
                continue
            password = self.config.get('mysql_users', db['username'])
            if password:
                db.update(password=password)
                self.dump(db, self.config.mysql_dir) and done.add(db['db'])

        for db in set(users.filter('db')).difference(done):
            self.config.warning("could not find authentication for database %s" % db)

        print

    def mysql_rsync(self):
        if self.config.skip_mysql_rsync:
            return False

        print "Copying mysql dumps to backups account..."

        if not self.account:
            self.config.warning("could not find your backups user account")
            return False

        remote = self.account['username']+'@'+self.account['home']

        if not System.check_publickey(remote):
            self.config.warning("please setup ssh key authentication between your account and the backups user account")
            return False

        origin = os.path.join('~', self.config.mysql_dir, '')
        destination = remote + ':mysql/'

        System.rsync(origin, destination)



    def dump(self, db, to):
        """Backup a database to disk using mysqldump, and compress with bzip2.

        Expected keys in `db` dictionary:
          - db (database name)
          - home (host)
          - username
          - password

        These keys come from the Dreamhost API, but the password needs to be
        added.
        """
        path = os.path.join('~', to, '') # by ending os.path.join with an empty string we add `/` at the end
        sql_file = path + db['db'] + '.w' + time.strftime('%w') + '.sql'

        # Usually you simply do: mysqldump [args] | bzip2 > file, but I
        # want to avoid writing empty files in case of an error from mysqldump
        dump = "mysqldump -c -u%(username)s -p%(password)s -h%(home)s %(db)s" % db

        (out, err, ret) = shell(dump)

        if not err:
            bz2_file, size = compress_file(sql_file, out)
            print db['db'] + " was backed up successfully to " + bz2_file + " (" + str(size/1024) + "KB)."
            return True

        self.config.warning("an error occurred while attempting to backup %s." % db['db'])
        self.config.warning("--> %s" % err)
        return False


def shell(command):
    """Run a shell command and return (out, err, returncode)"""
    process = Popen(command, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = process.communicate()
    return out, err, process.returncode


def compress_file(file, content):
    """Compresses `content` with bzip2 into a file with name `file`.bz2"""
    file = expanduser(file) + '.bz2'
    (path, filename) = os.path.split(file)
    if not os.path.exists(path):
        os.makedirs(path)
    bz2 = BZ2File(file, 'wb')
    bz2.write(content)
    bz2.close()
    return collapseuser(file), os.path.getsize(file)


def expanduser(file):
    return os.path.expanduser(file)

def collapseuser(file):
    return file.replace(os.path.expanduser('~'), '~')


class System(object):
    @staticmethod
    def check_publickey(destination, return_cmd=False):
        cmd = "ssh -o 'PreferredAuthentications=publickey' %s 'hostname'" % destination

        if return_cmd:
            return cmd

        (out, err, returncode) = shell(cmd)
        return returncode == 0

    @staticmethod
    def rsync(origin, destination, return_cmd=False):
        cmd = "rsync -e ssh -avhz %s %s" % (origin, destination)

        if return_cmd:
            return cmd

        (out, err, returncode) = shell(cmd)

        if err:
            print >> sys.stderr, err

        if out:
            print out

        return returncode == 0


class Config(SafeConfigParser, OptionParser):
    def __init__(self, args=None):
        SafeConfigParser.__init__(self)
        OptionParser.__init__(self, version=__version__)

        self.set_description(
            "This command line interface provides basic functionality. For"
            " more flexibility and options, create a configuration file."
            " Note that any options provided through this interface take"
            " precedence over any file configurations, thus overriding them."
            " See README file for more details.")

        self._add_options()
        self.parse_args(args)

    def print_version(self, file=None):
        print >> file, _title, self.get_version()
        print >> file, _copyright_short

    def print_usage(self, file=None):
        print >> file, "usage: " + self.expand_prog_name(self.usage)
        print >> file, "use option -h or --help for more information."

    def _add_options(self):
        self.add_option("-v", "--verbose", action="store_true",
            help="show more information during the backup process")

        self.add_option("-c", "--config-file", metavar="FILE",
            help="alternate configuration file to use")

        general = OptionGroup(self, "General options")
        general.add_option("-k", "--key", help="dreamhost's API key")
        self.add_option_group(general)

        mysql = OptionGroup(self, "MySQL options")

        mysql.add_option("-u", "--mysql-user", metavar="USER",
            help="the mysql username to use for backing up databases")

        mysql.add_option("-p", "--mysql-pass", metavar="PASS",
            help="the mysql password for the backups user")

        mysql.add_option("-d", "--mysql-dir", metavar="DIR",
            help=("save the mysql backup files to this directory"
                  " (defaults to backups/mysql)"))

        mysql.add_option("--skip-mysql", action="store_true",
            help=("skip mysql database backup"))

        mysql.add_option("--skip-mysql-rsync", action="store_true",
            help=("skip sending mysql backups to backup account"
                  " (only if --skip-mysql is not set)"))

        mysql.add_option("--skip-mysql-dumps", action="store_true",
            help=("skip making mysql dumps"
                  " (only if --skip-mysql is not set)"))

        self.add_option_group(mysql)

    def check_values(self, values, args):
        """Called just after parse_args()."""

        self.parse_files(values.config_file)
        self.set('general', 'key', values.key)
        self.set('general', 'verbose', values.verbose)

        if not self.key:
            self.error("no api key provided")

        self.set('general', 'mysql_dir', values.mysql_dir, 'backups/mysql')
        self.set('general', 'skip_mysql', values.skip_mysql)
        self.set('general', 'skip_mysql_rsync', values.skip_mysql_rsync)
        self.set('general', 'skip_mysql_dumps', values.skip_mysql_dumps)

        if values.mysql_user and values.mysql_pass:
            self.set('mysql_users', values.mysql_user, values.mysql_pass)

        if values.verbose:
            if values.mysql_user and not values.mysql_pass:
                self.uwarning("missing mysql password. Ignoring user.")
            if values.mysql_pass and not values.mysql_user:
                self.uwarning("missing mysql user. Ignoring password.")


    def parse_files(self, additional=''):
        path = os.path.splitext(os.path.realpath(__file__))[0]

        (basepath, name) = os.path.split(path)

        locations = [("%s.cfg" % path), ("~/.%s" % name), str(additional)]
        locations = map(os.path.expanduser, locations)

        self.files_parsed = self.read(locations)

    def set(self, section, option, value, default=None):
        if value is None:
            value = default

        if value is not None:
            if not isinstance(value, str):
                value = str(value)

            if not self.has_section(section):
                self.add_section(section)

            SafeConfigParser.set(self, section, option, value)

    def get(self, section, option, override=None, default=None):
        kwargs = {}
        if override is not None:
            kwargs = {'vars': {option: override}}

        try:
            value = SafeConfigParser.get(self, section, option, **kwargs)
            if value == 'True':
                value = True
            if value == 'False':
                value = False

            return value

        except (NoSectionError, NoOptionError):
            return override or default


    def __getattr__(self, item):
        return self.get('general', item)

    def warning(self, msg):
        """Similar to error, but does not exit."""
        print >> sys.stderr, "%s: warning: %s" % (
            self.get_prog_name(), msg)

    def uwarning(self, msg):
        """Similar to warning, but also prints usage."""
        self.print_usage(sys.stderr)
        self.warning(msg)


if __name__ == '__main__':
    config = Config()

    api = DreamhostAPI(config.key)
    backup = Backup(api, config)

    backup.mysql()
