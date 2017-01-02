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

import duplicity.backend
from duplicity import log
from duplicity import path
from duplicity.errors import BackendException


class MeganzBackend(duplicity.backend.Backend):
    """Use this backend when saving to mega.nz

    Urls look like mnz://user%40\domain:pass@/Root/backup
    
    You need to install megatools to have it working.

    """

    def __init__(self, parsed_url):
        duplicity.backend.Backend.__init__(self, parsed_url)
        self.username = parsed_url.username
        self.password = self.get_password()
        self.remote_pathdir = parsed_url.path.split('@')[1]
        self.subprocess_popen("megamkdir -u %s -p %s --no-ask-password %s" %
                                    (self.username, self.password, self.remote_pathdir))

    def _put(self, source_path, remote_filename):
        target_path = self.remote_pathdir + '/' + remote_filename
        self.subprocess_popen("megaput -u %s -p %s --no-ask-password --disable-previews --path=%s %s" %
                              (self.username, self.password, target_path, source_path.name))

    def _get(self, filename, local_path):
        source_path = self.remote_pathdir + '/' + filename
        self.subprocess_popen("megaget -u %s -p %s --no-ask-password --path=%s %s" %
                              (self.username, self.password, local_path.name, source_path))

    def _list(self):
        ret = self.subprocess_popen("megals -u %s -p %s --no-ask-password %s" %
                                    (self.username, self.password, self.remote_pathdir))
        for filename in ret[1].split("\n"):
            filename = filename[len(self.remote_pathdir) + 1:]
            if len(filename) > 0:
                print(filename)
                yield filename

    def _delete(self, filename):
        target_path = self.remote_pathdir + '/' + filename
        self.subprocess_popen("megarm -u %s -p %s --no-ask-password %s" %
                              (self.username, self.password, target_path))


duplicity.backend.register_backend("mnz", MeganzBackend)
