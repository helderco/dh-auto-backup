#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Dreamhost Auto Backup - version 0.1
# https://github.com/helderco/dh-auto-backup
#
# Copyright (c) 2012 Helder Correia <helder.mc@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import urllib2, urllib, uuid
import os, sys, time
from subprocess import Popen, PIPE
from bz2 import BZ2File

url = 'https://api.dreamhost.com'
key = '6SHU5P2HLDAYECUM'

db_user = 'user_backups'
db_pass = 's3cr3tp4'

backup_dir = "backups/"

class DreamhostApi(object):
    def __init__(self, url, key):
        self.url = url
        self.key = key

    def request(self, cmd, *args, **kwargs):
        params = {'cmd': cmd, 'key': self.key, 'unique_id': str(uuid.uuid4())}
        params.update(kwargs)
        connection = urllib2.urlopen(self.url, urllib.urlencode(params))
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


def backup_mysql(db, archive=''):
    """
    Usually you simply do: mysqldump [args] | bzip2 > file,
      but I want to avoid writing empty files in case of an error from mysqldump
    """
    sql_file = archive + db['db'] + '.' + time.strftime('%w') + '.sql'
    dump_cmd = "mysqldump -c -u%(username)s -p%(password)s -h%(home)s %(db)s" % db

    process = Popen(dump_cmd, stdout=PIPE, stderr=PIPE, shell=True)
    (out, err) = process.communicate()

    if not err:
        bz2_file = compress(sql_file, out)
        print db['db'] + " was backed up successfully to " + bz2_file + "."
        return True

    print "WARNING: An error occurred while attempting to backup " + db['db'] + " to " + sql_file + "."
    print >> sys.stderr, "-->", err
    return False


def compress(file, content):
    file += '.bz2'
    bz2 = BZ2File(file, 'wb')
    bz2.write(content)
    bz2.close()
    return file

if __name__ == '__main__':
    api = DreamhostApi(url, key)
    mysql_users = api.request('mysql-list_users')

    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    print "Backing up databases..."
    for db in mysql_users.list('username', db_user):
        db.update(password=db_pass)
        backup_mysql(db, backup_dir)
	