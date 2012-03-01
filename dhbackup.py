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

__version__ = '0.2'

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

import os
import sys
import time
from uuid import uuid4
from urllib import urlencode
from urllib2 import urlopen
from subprocess import Popen, PIPE
from bz2 import BZ2File
from optparse import OptionParser, OptionGroup


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


def mysqldump(db, archive=''):
    """Backup a database to disk using mysqldump, and compress with bzip2.

    Expected keys in `db` dictionary:
      - db (database name)
      - home (host)
      - username
      - password

    These keys come from the Dreamhost API, but the password needs to be added.
    """
    sql_file = archive + db['db'] + '.' + time.strftime('%w') + '.sql'

    # Usually you simply do: mysqldump [args] | bzip2 > file, but I
    # want to avoid writing empty files in case of an error from mysqldump
    dump = "mysqldump -c -u%(username)s -p%(password)s -h%(home)s %(db)s" % db

    process = Popen(dump, stdout=PIPE, stderr=PIPE, shell=True)
    (out, err) = process.communicate()

    if not err:
        bz2_file = compress(sql_file, out)
        print db['db'] + " was backed up successfully to " + bz2_file + "."
        return True

    print >> sys.stderr, ("warning: An error occurred while attempting to"
                          "backup %s to %s.\n--> %s" %
                          db['db'], sql_file, err)
    return False


def compress(file, content):
    """Compresses `content` with bzip2 into a file with name `file`.bz2"""
    file += '.bz2'
    bz2 = BZ2File(file, 'wb')
    bz2.write(content)
    bz2.close()
    return file


class Arguments(OptionParser):
    """Define and parse command line arguments."""

    class Group(OptionGroup):
        def add_option(self, *args, **kwargs):
            if kwargs.has_key('default') and kwargs.has_key('help'):
                kwargs['help'] += " (defaults to %default)"
            OptionGroup.add_option(self, *args, **kwargs)


    def print_copy(self):
        """Print copyright and license notice."""
        print "Dreamhost Auto Backup, v%s" % self.get_version()
        print "Copyright (C) 2012  Helder Correia"
        print "This program comes with ABSOLUTELY NO WARRANTY."
        print "This is free software, and you are welcome to redistribute"
        print "it under certain conditions; see source for details."
        print

    def print_usage(self, file=None):
        print >> file, "usage: " + self.expand_prog_name(self.usage)
        print >> file, "use option -h or --help for more information."

    def print_help(self, file=None):
        self.print_copy()
        OptionParser.print_help(self, file)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('version', __version__)
        OptionParser.__init__(self, *args, **kwargs)
        self.usage = "%prog [options] api_key"
        self._add_options()

    def _add_options(self):
        mysql = self.Group(self, "MySQL backup options")

        mysql.add_option("-u", "--mysql-user",
            dest="mysql_user", metavar="USER",
            help="the mysql username to use for backing up databases")

        mysql.add_option("-p", "--mysql-pass",
            dest="mysql_pass", metavar="PASS",
            help="the mysql password for the backups user")

        mysql.add_option("-d", "--backup-dir",
            dest="backup_dir", metavar="DIR", default="~/backups/mysql",
            help="the local dir where the mysql dumps should be saved")

        self.add_option_group(mysql)

    def parse_args(self, *args, **kwargs):
        (options, args) = OptionParser.parse_args(self, *args, **kwargs)

        if len(args) != 1:
            self.error("no api key provided")

        if not options.mysql_user and not options.mysql_pass:
            self.error("no mysql user authentication provided")

        if options.mysql_user and not options.mysql_pass:
            self.error(
                "no mysql password provided for user " + options.mysql_user)

        if not options.mysql_user and options.mysql_pass:
            self.warning("no mysql user given, ignoring password")
            options.mysql_pass = None

        return args[0], options

    def warning(self, msg):
        """Similar to error, but does not exit."""
        self.print_usage(sys.stderr)
        print >> sys.stderr, "%s: warning: %s" % (self.get_prog_name(), msg)


if __name__ == '__main__':
    key, options = Arguments().parse_args()

    api = DreamhostAPI(key)
    mysql_users = api.request('mysql-list_users')

    if mysql_users.success and options.mysql_user and options.mysql_pass:
        print "Backing up databases..."
        if not os.path.exists(options.backup_dir):
            os.makedirs(options.backup_dir)

        for db in mysql_users.list('username', options.mysql_user):
            db.update(password=options.mysql_pass)
            mysqldump(db, options.backup_dir)

