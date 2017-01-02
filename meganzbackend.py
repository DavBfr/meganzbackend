# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2016 David PHAM-VAN <dev.nfet.net@gmail.com>
#
# Duplicity is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# Duplicity is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with duplicity; if not, write to the Free Software Foundation,
# Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

import os
import json

import duplicity.backend
from duplicity import log
from duplicity import path
from duplicity.errors import BackendException


class MeganzBackend(duplicity.backend.Backend):
    """Use this backend when saving to mega.nz

    Urls look like
        mnz://user%40domain:pass@/Root/backup
        mmnz:///etc/duplicity/mega.yml

    You need to install megatools to have it working.

    Create a file /etc/duplicity/mega.json with:
    {
        'path': '/Root/backup',
        'accounts': {
            'login1':'password1',
            'login2':'password2',
            'login3':'password3',
            'login4':'password4'
        }
    }
    """

    def __init__(self, parsed_url):
        duplicity.backend.Backend.__init__(self, parsed_url)
        self.files_cache = None
        if parsed_url.scheme == 'mmnz':
            config_file = parsed_url.path
            config = json.load(open(config_file))
            self.accounts = config['accounts']
            self.remote_pathdir = config['path']
        else:
            self.accounts = {parsed_url.username: self.get_password()}
            self.remote_pathdir = parsed_url.path.split('@')[1]

        self._list()
        for username, password in self.accounts.items():
            self.subprocess_popen("megamkdir -u %s -p %s --no-ask-password %s" %
                                  (username, password, self.remote_pathdir))

    def _put(self, source_path, remote_filename):
        target_path = self.remote_pathdir + '/' + remote_filename
        self._list()
        max_free = (0, )
        for username, password in self.accounts.items():
            if username in self.files_cache and 'free' in self.files_cache[username]:
                if self.files_cache[username]['free'] > max_free[0]:
                    max_free = (self.files_cache[username][
                                'free'], username, password)

        size = os.path.getsize(source_path.name)
        if max_free[0] < size:
            raise Exception("no space left")
        username = max_free[1]
        password = max_free[2]
        ret = self.subprocess_popen("megaput -u %s -p %s --no-ask-password --disable-previews --path=%s %s" %
                                    (username, password, target_path, source_path.name))
        if ret[0] != 0:
            raise Exception(ret[2])
        self.files_cache[username]['files'].append(remote_filename)
        self.files_cache[username]['free'] -= size

    def _get(self, filename, local_path):
        source_path = self.remote_pathdir + '/' + filename
        self._list()
        for username, password in self.accounts.items():
            if filename in self.files_cache[username]['files']:
                self.subprocess_popen("megaget -u %s -p %s --no-ask-password --path=%s %s" %
                                      (username, password, local_path.name, source_path))
                break

    def list_account(self, username, password):
        ret = self.subprocess_popen("megals -u %s -p %s --no-ask-password %s" %
                                    (username, password, self.remote_pathdir))
        for filename in ret[1].split("\n"):
            filename = filename[len(self.remote_pathdir) + 1:]
            if len(filename) > 0:
                yield filename

    def _list(self):
        if self.files_cache is None:
            self.files_cache = {}
            for username, password in self.accounts.items():
                ret = self.subprocess_popen(
                    "megadf -u %s -p %s --free" % (username, password))
                if ret[0] == 0:
                    self.files_cache[username] = {}
                    self.files_cache[username]['free'] = int(ret[1])
                    self.files_cache[username]['files'] = list(
                        self.list_account(username, password))

        return [inner for outer in (self.files_cache[x]['files'] for x in self.files_cache) for inner in outer]

    def _delete(self, filename):
        target_path = self.remote_pathdir + '/' + filename
        for username, password in self.accounts.items():
            if filename in self.files_cache[username]['files']:
                self.subprocess_popen("megarm -u %s -p %s --no-ask-password %s" %
                                      (username, password, target_path))
                self.files_cache[username]['files'].remove(filename)
                ret = self.subprocess_popen(
                    "megadf -u %s -p %s --free" % (username, password))
                self.files_cache[username]['free'] = int(ret[1])


duplicity.backend.register_backend("mnz", MeganzBackend)
duplicity.backend.register_backend("mmnz", MeganzBackend)
