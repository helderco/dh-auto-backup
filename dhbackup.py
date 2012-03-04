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

__version__ = '0.3'

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
    def __init__(self, key, url="https://api.dreamhost.com"):
        self.url = url
        self.key = key

    def request(self, cmd, **kwargs):
        params = {'cmd': cmd, 'key': self.key, 'unique_id': str(uuid4())}
        params.update(kwargs)
        connection = urlopen(self.url, urlencode(params))
        return Response(connection, cmd)


class Response(object):
    def __init__(self, response, cmd):
        self.cmd = cmd
        self.raw = response
        self.data = []
        self.success = False
        self.parse(response)

    def parse(self, response):
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
        result = []
        for item in self.data:
            result.append(item[prop])
        return result

    def list(self, prop, value, return_prop=None):
        result = []
        for item in self.data:
            if item[prop] == value:
                result.append(item if not return_prop else item[return_prop])
        return result

    def find(self, prop, value, return_prop=None):
        result = self.list(prop, value, return_prop)
        return result[0] if len(result) > 0 else None

    def __repr__(self):
        return repr(self.raw)


class Backup(object):
    def __init__(self, api, config):
        self.api = api
        self.config = config

    def mysql(self):
        users = api.request('mysql-list_users')
        if not users.success:
            return False

        print "Backing up databases..."

        done = set()
        for db in users.data:
            if db['db'] in done:
                continue
            password = config.get('mysql_users', db['username'])
            if password:
                db.update(password=password)
                self.dump(db, config.mysql_dir) and done.add(db['db'])

        for db in set(users.filter('db')).difference(done):
            print "warning: could not find authentication for database %s" % db


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
        path = os.path.join(to, '')
        sql_file = path + db['db'] + '.w' + time.strftime('%w') + '.sql'

        # Usually you simply do: mysqldump [args] | bzip2 > file, but I
        # want to avoid writing empty files in case of an error from mysqldump
        dump = "mysqldump -c -u%(username)s -p%(password)s -h%(home)s %(db)s" % db

        process = Popen(dump, stdout=PIPE, stderr=PIPE, shell=True)
        (out, err) = process.communicate()

        if not err:
            bz2_file = compress_file(sql_file, out)
            print db['db'] + " was backed up successfully to " + bz2_file + "."
            return True

        print >> sys.stderr, (
            "warning: An error occurred while attempting to backup %s." %
            db['db'])
        print >> sys.stderr, "--> %s" % err
        return False


def compress_file(file, content):
    """Compresses `content` with bzip2 into a file with name `file`.bz2"""
    file = os.path.expanduser(file) + '.bz2'
    (path, filename) = os.path.split(file)
    if not os.path.exists(path):
        os.makedirs(path)
    bz2 = BZ2File(file, 'wb')
    bz2.write(content)
    bz2.close()
    return collapseuser(file)


def collapseuser(file):
    return file.replace(os.path.expanduser('~'), '~')


class Config(SafeConfigParser, OptionParser):
    def __init__(self, args=None):
        SafeConfigParser.__init__(self)
        OptionParser.__init__(self, version=__version__)

        self.set_description(
            "This command line interface provide basic functionality. For"
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
                  " (defaults to ~/backups/mysql)"))

        self.add_option_group(mysql)

    def check_values(self, values, args):
        """Called just after parse_args()."""

        self.parse_files(values.config_file)
        self.set('general', 'key', values.key)
        self.set('general', 'verbose', values.verbose)

        if not self.key:
            self.error("no api key provided")

        self.set('general', 'mysql_dir', values.mysql_dir, '~/backups/mysql')

        if values.mysql_user and values.mysql_pass:
            self.set('mysql_users', values.mysql_user, values.mysql_pass)

        if values.verbose:
            if values.mysql_user and not values.mysql_pass:
                self.warning("missing mysql password. Ignoring user.")
            if values.mysql_pass and not values.mysql_user:
                self.warning("missing mysql user. Ignoring password.")


    def parse_files(self, additional=''):
        path = os.path.splitext(os.path.realpath(__file__))[0]

        (basepath, name) = os.path.split(path)

        locations = [("%s.cfg" % path), ("~/.%s" % name), str(additional)]
        locations = map(os.path.expanduser, locations)

        self.files_parsed = self.read(locations)

    def get(self, section, option, override=None, default=None):
        kwargs = {}
        if override is not None:
            kwargs = {'vars': {option: override}}
        try:
            return SafeConfigParser.get(self, section, option, **kwargs)
        except (NoSectionError, NoOptionError):
            return override or default

    def set(self, section, option, value, default=None):
        if value is None:
            value = default
        if value is not None:
            SafeConfigParser.set(self, section, option, value)

    def __getattr__(self, item):
        return self.get('general', item)

    def warning(self, msg):
        """Similar to error, but does not exit."""
        self.print_usage(sys.stderr)
        print >> sys.stderr, "%s: warning: %s" % (
            self.get_prog_name(), msg)


if __name__ == '__main__':
    config = Config()

    api = DreamhostAPI(config.key)
    backup = Backup(api, config)

    backup.mysql()
