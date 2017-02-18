#!/usr/bin/env python

from __future__ import with_statement

import os
import sys
import errno
import putiopy
import json
import pwd
import time
import urllib2
from stat import S_IFDIR, S_IFLNK, S_IFREG
from fuse import FUSE, FuseOSError, Operations

foldersIds = {}
downloaders = {}

class PutioMount(Operations):
    def __init__(self):
        with open('.credentials.json') as json_data:
            self.putioToken = json.load(json_data)['token']

        if self.putioToken is None:
            print "Please put your token in .credentials.json file."
            sys.exit()

        self.putio = putiopy.Client(self.putioToken)

    def _set_files(self, folder, files):
        for file in files:
            folderName = (folder + '/' + file.name).replace('//', '/').encode('utf-8')
            foldersIds[folderName] = file

    def _get_id(self, path):
        if path == '/':
            return 0

        return self._get_file(path).id

    def _get_parent_path(self, path):
        return os.path.split(path)[0]

    def _get_file(self, path):
        path = self._full_path(path)
        try:
            return foldersIds[self._full_path(path)]
        except:
            self.readdir(self._get_parent_path(path), False)
            return foldersIds[self._full_path(path)]

    def _full_path(self, partial):
        return partial.encode('utf-8')

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        uid = pwd.getpwuid(os.getuid()).pw_uid
        gid = pwd.getpwuid(os.getuid()).pw_gid
        self.now = int(time.time())
        parentPath = self._get_parent_path(path)

        if path == '/':
            return dict(
                 st_mode=040777,
                 st_size=4096,
                 st_ctime=self.now,
                 st_mtime=self.now,
                 st_atime=self.now,
                 st_nlink=1
             )

        try:
            file = self._get_file(path)
        except:
            st = os.lstat('/tmp/a-fake-file-which-not-exists')
            return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

        if file.content_type == 'application/x-directory':
           return dict(
                st_mode=040777,
                st_size=4096,
                st_ctime=self.now,
                st_mtime=self.now,
                st_atime=self.now,
                st_nlink=1
            )
        return dict(
            st_mode=S_IFREG | 0444,
            st_size=file.size,
            st_ctime=0,
            st_mtime=0,
            st_atime=0,
            st_nlink=1
        )

    def readdir(self, path, fh):
        full_path = self._full_path(path)
        dirents = ['.', '..']
        if full_path != '/':
            file = self._get_file(full_path)
            files = file.dir()
        else:
            files = self.putio.File.list();


        self._set_files(full_path, files)
        for file in files:
            dirents.append(file.name.encode('utf-8'))

        return dirents

    def mkdir(self, path, mode):
        pathInfos = os.path.split(path)
        parentPath = pathInfos[0]
        if (parentPath != '/'):
            parentId = self._get_file(parentPath).id
        else:
            parentId = 0

        self.putio.File.create_folder(pathInfos[1], parentId)

    def statfs(self, path):
        return dict(
                  bsize= 1000000,
                  frsize= 1000000,
                  blocks= 1000000,
                  bfree= 1000000,
                  bavail= 1000000,
                  files= 1000000,
                  ffree= 1000000,
                  favail= 1000000,
                  fsid= 1000000,
                  flag= 1000000,
                  namemax= 1000000
               )
    def unlink(self, path):
        file = self._get_file(path);
        return file.delete()

    def rmdir(self, path):
        file = self._get_file(path);
        file.delete()

    def rename(self, old, new):
        file = self._get_file(old)
        pathInfos = os.path.split(path)
        return file.rename(pathInfos[1])

    # File methods
    # ============

    def open(self, path, flags):
        return True

    def create(self, path, mode, fi=None):
        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        try:
            downloader = downloaders[path]
        except:
            try:
                fileUrl = links[path]
            except:
                file = self._get_file(path)
                fileUrl = file.get_stream_link()
                if fileUrl.replace('oauth_token', '') == fileUrl:
                    fileUrl = fileUrl +'?oauth_token='+self.putioToken

            downloader = Downloader(fileUrl, file.size, file.id)
            downloaders[path] = downloader

        return downloader.read(offset, length)

class Downloader:
    def __init__(self, fileUrl, fileSize, fileId):
        self.url = fileUrl
        self.size = fileSize
        self.fileId = fileId

    def read(self, offset, length):
        req = urllib2.Request(self.url)
        req.add_header('Range', 'bytes=' + str(offset) + '-' + str(offset + length - 1))
        resp = urllib2.urlopen(req)
        return resp.read()

def main(mountpoint):
    FUSE(PutioMount(), mountpoint, nothreads=False, foreground=False,**{'allow_other': True})

if __name__ == '__main__':
    main(sys.argv[1])
