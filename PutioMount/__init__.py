from __future__ import with_statement

import os
from sys import exit, argv
import putiopy
import pwd
import time
import requests
from stat import S_IFDIR, S_IFLNK, S_IFREG
from fuse import FUSE, FuseOSError, Operations
import threading
import inotify.adapters
import tempfile

foldersIds = {}
downloaders = {}

tmp_path = os.path.join(tempfile.gettempdir(), 'putio')
credentials_path = os.path.join(os.path.expanduser('~'), '.putio-token')
putio_token = None

class PutioMounter(Operations):
    def __init__(self):
        global putio_token
        self.putio = putiopy.Client(putio_token)

    def _set_files(self, folder, files):
        for file in files:
            folderName = os.path.join(folder, file.name).replace(os.path.sep + os.path.sep, os.path.sep).encode('utf-8')
            foldersIds[folderName] = file

    def _get_id(self, path):
        if path == os.path.sep:
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


    def chmod(self, path, mode):
        full_path = self._full_path(path)


    def chown(self, path, uid, gid):
        full_path = self._full_path(path)


    def getattr(self, path, fh=None):
        uid = pwd.getpwuid(os.getuid()).pw_uid
        gid = pwd.getpwuid(os.getuid()).pw_gid
        self.now = int(time.time())
        parentPath = self._get_parent_path(path)

        if path == os.path.sep:
            return dict(
                 st_mode=S_IFDIR | 0755,
                 st_size=4096,
                 st_ctime=self.now,
                 st_mtime=self.now,
                 st_uid= os.getuid(),
                 st_gid=os.getuid(),
                 st_atime=0,
                 st_nlink=1
             )
        try:
            file = self._get_file(path)
        except:
            st = os.lstat('a-fake-file-which-not-exists')
            return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
        try:
            ctime = time.mktime(file.created_at.timetuple())
        except:
            ctime = self.now

        if file.content_type == 'application/x-directory':
           return dict(
                st_mode=040777,
                st_size=4096,
                st_ctime=ctime,
                st_mtime=ctime,
                st_atime=0,
                st_uid=os.getuid(),
                st_gid=os.getuid(),
                st_nlink=1
            )
        return dict(
            st_mode=S_IFREG | 0777,
            st_size=file.size,
            st_ctime=ctime,
            st_mtime=ctime,
            st_uid= os.getuid(),
            st_gid=os.getuid(),
            st_atime=0,
            st_nlink=1
        )

    def readdir(self, path, fh):
        full_path = self._full_path(path)
        dirents = ['.', '..']
        if full_path != os.path.sep:
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
        if (parentPath != os.path.sep):
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
            fileUrl = links[path]
        except:
            file = self._get_file(path)
            fileUrl = file.get_stream_link()
            if fileUrl.replace('oauth_token', '') == fileUrl:
                fileUrl = "%s?oauth_token=%s" % (fileUrl, putio_token)
        try:
            downloader = downloaders[path]
        except:
            downloader = Downloader(fileUrl, file.size, file.id)
            downloaders[path] = downloader

        return downloader.read(offset, length, fileUrl)

class Downloader:
    packetSize = 1024 * 2048

    def __init__(self, fileUrl, fileSize, fileId):
        self.packets = []

        self.url = fileUrl
        self.size = fileSize
        self.fileId = fileId

    def _create_packet(self, packet, url):
        if os.path.exists(packet.file):
            return packet

        headers = {"Range": 'bytes=%s-%s' % (str(packet.start), str(packet.end - 1))}
        req = requests.get(url, headers=headers, stream=True)

        with open(packet.file, 'w') as fp:
            for chunk in req.iter_content(chunk_size=512):
                if chunk:
                    fp.write(chunk)
                    fp.flush()

                if os.path.getsize(packet.file) >= self.packetSize or fp.tell()  >= self.packetSize:
                    return packet

        return packet

    def _get_packet(self, offset, length, url):
        for packet in self.packets:
            if packet.start <= offset and packet.end >= offset + length:
                return packet

        packet = type('lamdbaobject', (object,), {})()
        packet.start = 0
        packet.end = self.packetSize
        packet.id = 1

        while packet.end < offset + length:
            packet.start += self.packetSize
            packet.end = packet.start + self.packetSize
            packet.id += 1

        if packet.end > self.size:
            packet.end = self.size

        packet.file = os.path.join(tmp_path, '%s-%s' % (str(self.fileId), str(packet.start)))
        if not os.path.exists(packet.file):
            clean_old_files()
            thr = threading.Thread(target=self._create_packet, args=(), kwargs={"packet": packet, "url": url})
            thr.start()

        return packet

    def read(self, offset, length, url):
        if offset + length > self.size:
            length = self.size - offset

        packet = self._get_packet(offset, length, url)

        if not os.path.exists(packet.file) or os.path.getsize(packet.file) < offset - packet.start + length or packet.end < offset + length or offset - packet.start < 0:
            headers = {"Range": 'bytes=%s-%s' % (str(offset), str(offset + length - 1))}
            return requests.get(url, headers=headers).content

        fp = open(packet.file, 'r')
        fp.seek(offset - packet.start)
        data = fp.read(length)
        fp.close()

        if packet.end < self.size and os.path.getsize(packet.file) >= self.packetSize:
            nextPacket = self._get_packet(packet.end + 1, 2, url)

        return data

def clean_old_files() :
    now = time.time()
    for f in os.listdir(tmp_path):
        f = os.path.join(tmp_path, f)
        if os.stat(f).st_atime < now - 60 * 60 and os.path.isfile(f):
            os.remove(f)

def main(mount_point):
    mount(mount_point)

def mount(new_mount_point):
    global mount_point
    global putio_token

    mount_point = new_mount_point
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)

    if not os.path.exists(credentials_path):
        with open(credentials_path, 'w') as f:
            f.write("YOUR_TOKEN_HERE")

    with open(credentials_path, 'r') as f:
        putio_token = f.read().replace("\n", "").replace("\r", "")

    if putio_token is None or putio_token == 'YOUR_TOKEN_HERE':
        print "Please put your token in %s file." % credentials_path
        exit()

    FUSE(PutioMounter(), mount_point, nothreads=False, foreground=False,**{'allow_other': True})
    i = inotify.adapters.Inotify()
    i.add_watch(mount_point)

def get_mount_point():
    global mount_point

    return mount_point

def set_credentials_path(custom_credentials_path):
    global credentials_path
    credentials_path = custom_credentials_path

def set_tmp_path(custom_tmp_path):
    global tmp_path
    tmp_path = custom_tmp_path

if __name__ == '__main__':
    main(sys.argv[1])
