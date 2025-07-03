###############################################################################
#
# Copyright (c) 2011-2017 Ruslan Spivak
# Copyright (c) 2025 David Degen
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

import os
import logging

from paramiko import (
    ServerInterface,
    SFTPAttributes,
    SFTPHandle,
    SFTPServer,
    SFTPServerInterface,
)
from paramiko.common import AUTH_SUCCESSFUL, OPEN_SUCCEEDED
from paramiko.sftp import SFTP_OK


class StubServer(ServerInterface):
    def check_auth_password(self, username, password):
        # all are allowed
        return AUTH_SUCCESSFUL

    def check_auth_publickey(self, username, key):
        # all are allowed
        return AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        return OPEN_SUCCEEDED

    def get_allowed_auths(self, username):
        """List availble auth mechanisms."""
        return "password,publickey"


class StubSFTPHandle(SFTPHandle):
    def stat(self):
        try:
            return SFTPAttributes.from_stat(os.fstat(self.readfile.fileno()))
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)

    def chattr(self, attr):
        # python doesn't have equivalents to fchown or fchmod, so we have to
        # use the stored filename
        try:
            SFTPServer.set_file_attr(self.filename, attr)
            return SFTP_OK
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)


class StubSFTPServer(SFTPServerInterface):
    ROOT = os.getcwd()

    def _realpath(self, path):
        normalized_path = os.path.normpath(path)
        full_path = os.path.join(self.ROOT, normalized_path)
        absolute_path = os.path.abspath(full_path)
        if not absolute_path.startswith(self.ROOT):
            raise ValueError("Access denied: path is outside the root directory.")

        logging.debug(f"Real path for '{path}': {absolute_path}")
        return absolute_path

    def list_folder(self, path):
        path = self._realpath(path)
        logging.debug(f"list_folder called for path: {path}")
        try:
            out = []
            file_list = os.listdir(path)
            logging.debug(f"Listing folder: {path}, files: {file_list}")
            for file_name in file_list:
                attr = SFTPAttributes.from_stat(
                    os.lstat(os.path.join(path, file_name)), filename=file_name
                )
                # attr.filename = str(file_name)
                attr.filename = str(file_name)
                out.append(attr)
            return out
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)

    def stat(self, path):
        path = self._realpath(path)
        logging.debug(f"stat called for path: {path}")
        try:
            return SFTPAttributes.from_stat(os.stat(path))
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)

    def lstat(self, path):
        path = self._realpath(path)
        logging.debug(f"lstat called for path: {path}")
        try:
            return SFTPAttributes.from_stat(os.lstat(path))
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)

    def open(self, path, flags, attr):
        path = self._realpath(path)
        logging.debug(f"open called for path: {path}, flags: {flags}, attr: {attr}")
        try:
            binary_flag = getattr(os, "O_BINARY", 0)
            flags |= binary_flag
            mode = getattr(attr, "st_mode", None)
            if mode is not None:
                fd = os.open(path, flags, mode)
            else:
                # os.open() defaults to 0777 which is
                # an odd default mode for files
                fd = os.open(path, flags, 0o666)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        if (flags & os.O_CREAT) and (attr is not None):
            attr._flags &= ~attr.FLAG_PERMISSIONS
            SFTPServer.set_file_attr(path, attr)
        if flags & os.O_WRONLY:
            if flags & os.O_APPEND:
                fstr = "ab"
            else:
                fstr = "wb"
        elif flags & os.O_RDWR:
            if flags & os.O_APPEND:
                fstr = "a+b"
            else:
                fstr = "r+b"
        else:
            # O_RDONLY (== 0)
            fstr = "rb"
        try:
            f = os.fdopen(fd, fstr)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        fobj = StubSFTPHandle(flags)
        fobj.filename = path
        fobj.readfile = f
        fobj.writefile = f
        return fobj

    def remove(self, path):
        path = self._realpath(path)
        logging.debug(f"remove called for path: {path}")
        try:
            os.remove(path)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def rename(self, oldpath, newpath):
        oldpath = self._realpath(oldpath)
        newpath = self._realpath(newpath)
        logging.debug(f"rename called from {oldpath} to {newpath}")
        try:
            os.rename(oldpath, newpath)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def mkdir(self, path, attr):
        path = self._realpath(path)
        logging.debug(f"mkdir called for path: {path}, attr: {attr}")
        try:
            os.mkdir(path)
            if attr is not None:
                SFTPServer.set_file_attr(path, attr)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def rmdir(self, path):
        path = self._realpath(path)
        logging.debug(f"rmdir called for path: {path}")
        try:
            os.rmdir(path)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def chattr(self, path, attr):
        path = self._realpath(path)
        logging.debug(f"chattr called for path: {path}, attr: {attr}")
        try:
            SFTPServer.set_file_attr(path, attr)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def symlink(self, target_path, path):
        path = self._realpath(path)
        logging.debug(f"symlink called for target: {target_path}, path: {path}")
        if (len(target_path) > 0) and (target_path[0] == "/"):
            # absolute symlink
            target_path = os.path.join(self.ROOT, target_path[1:])
            if target_path[:2] == "//":
                # bug in os.path.join
                target_path = target_path[1:]
        else:
            # compute relative to path
            abspath = os.path.join(os.path.dirname(path), target_path)
            if abspath[: len(self.ROOT)] != self.ROOT:
                # this symlink isn't going to work anyway -- just break it immediately
                target_path = "<error>"
        try:
            os.symlink(target_path, path)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        return SFTP_OK

    def readlink(self, path):
        path = self._realpath(path)
        logging.debug(f"readlink called for path: {path}")
        try:
            symlink = os.readlink(path)
        except OSError as e:
            return SFTPServer.convert_errno(e.errno)
        # if it's absolute, remove the root
        if os.path.isabs(symlink):
            if symlink[: len(self.ROOT)] == self.ROOT:
                symlink = symlink[len(self.ROOT) :]
                if (len(symlink) == 0) or (symlink[0] != "/"):
                    symlink = "/" + symlink
            else:
                symlink = "<error>"
        return symlink
