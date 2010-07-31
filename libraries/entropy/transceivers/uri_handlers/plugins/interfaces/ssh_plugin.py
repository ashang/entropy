# -*- coding: utf-8 -*-
"""

    @author: Fabio Erculiani <lxnay@sabayon.org>
    @contact: lxnay@sabayon.org
    @copyright: Fabio Erculiani
    @license: GPL-2

    B{EntropyTransceiver SSH URI Handler module}.

"""
import os
import time
import tempfile
import shutil

from entropy.const import const_isnumber
from entropy.output import brown, darkgreen, teal
from entropy.i18n import _
from entropy.exceptions import ConnectionError
from entropy.transceivers.uri_handlers.skel import EntropyUriHandler

class EntropySshUriHandler(EntropyUriHandler):

    """
    EntropyUriHandler based SSH (with pubkey) transceiver plugin.
    """

    PLUGIN_API_VERSION = 1

    _DEFAULT_TIMEOUT = 60
    _DEFAULT_PORT = 22
    _TXC_CMD = "/usr/bin/scp"
    _SSH_CMD = "/usr/bin/ssh"

    @staticmethod
    def approve_uri(uri):
        if uri.startswith("ssh://"):
            return True
        return False

    @staticmethod
    def get_uri_name(uri):
        myuri = uri.split("/")[2:][0].split(":")[0]
        myuri = myuri.split("@")[-1]
        return myuri

    @staticmethod
    def hide_sensible_data(uri):
        return uri

    def __init__(self, uri):
        EntropyUriHandler.__init__(self, uri)

        self._timeout = EntropySshUriHandler._DEFAULT_TIMEOUT
        import socket, subprocess, pty
        self._socket, self._subprocess = socket, subprocess
        self._pty = pty
        self.__host = EntropySshUriHandler.get_uri_name(self._uri)
        self.__user, self.__port, self.__dir = self.__extract_scp_data(
            self._uri)

        # as documentation suggests
        # test out connection first
        self.__test_connection()

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __test_connection(self):
        tries = 5
        while tries:
            tries -= 1
            try:
                sock = self._socket.create_connection(
                    (self.__host, self.__port), 5)
                sock.close()
                return
            except self._socket.error:
                time.sleep(5)
                continue

        raise ConnectionError("cannot connect to %s on port %s" % (
            self.__host, self.__port,))

    def __extract_scp_data(self, uri):

        no_ssh_split = uri.split("ssh://")[-1]
        user = ''
        if "@" in no_ssh_split:
            user = no_ssh_split.split("@")[0]

        port = uri.split(":")[-1]
        try:
            port = int(port)
        except ValueError:
            port = EntropySshUriHandler._DEFAULT_PORT

        sdir = '~/'
        proposed_sdir = no_ssh_split.split(":", 1)[-1].split(":")[0]
        if proposed_sdir:
            sdir = proposed_sdir

        return user, port, sdir

    def _parse_progress_line(self, line):

        line_data = line.strip().split()
        if len(line_data) < 5:
            # mmh... not possible to properly parse data
            self.output(line.strip(), back = True)
            return

        file_name = line_data[0]
        percent = line_data[1]
        tx_speed = line_data[3]
        tx_size = line_data[2]
        eta = line_data[4]

        # create text
        mytxt = _("Transfer status")
        current_txt = "<-> (%s) %s: " % (teal(file_name), brown(mytxt),) + \
            darkgreen(tx_size) + " " + \
            brown("[") + str(percent) + brown("]") + \
            " " + eta + " " + tx_speed

        self.output(current_txt, back = True, header = "    ")

    def _update_progress(self, std_r):
        read_buf = ""
        try:
            char = std_r.read(1)
            while char:
                if (char == "\r") and read_buf:
                    self._parse_progress_line(read_buf)
                    read_buf = ""
                elif (char != "\r"):
                    read_buf += char
                char = std_r.read(1)
        except IOError:
            return

    def _fork_cmd(self, args):

        pid, fd = self._pty.fork()

        if pid == 0:
            proc = self._subprocess.Popen(args)
            os._exit(proc.wait())
        elif pid == -1:
            raise ConnectionError("cannot forkpty()")
        else:
            dead = False
            return_code = 1
            std_r = os.fdopen(fd, "r")
            while not dead:

                try:
                    dead, return_code = os.waitpid(pid, os.WNOHANG)
                except OSError as e:
                    if e.errno != 10:
                        raise
                    dead = True

                time.sleep(0.5)
                self._update_progress(std_r)
            std_r.close()

            return return_code

    def _exec_cmd(self, args):

        fd, tmp_path = tempfile.mkstemp()
        fd_err, tmp_path_err = tempfile.mkstemp()
        os.close(fd)
        os.close(fd_err)

        with open(tmp_path, "wb") as std_f:
            with open(tmp_path_err, "wb") as std_f_err:
                proc = self._subprocess.Popen(args, stdout = std_f,
                    stderr = std_f_err)
                exec_rc = proc.wait()

        std_f = open(tmp_path, "rb")
        output = std_f.read()
        std_f.close()
        std_f = open(tmp_path_err, "rb")
        error = std_f.read()
        std_f.close()

        os.remove(tmp_path)
        os.remove(tmp_path_err)
        return exec_rc, output, error

    def _setup_common_args(self, remote_path):
        args = []
        if const_isnumber(self._timeout):
            args += ["-o", "ConnectTimeout=%s" % (self._timeout,),
                "-o", "ServerAliveCountMax=4", # hardcoded
                "-o", "ServerAliveInterval=15"] # hardcoded
        if self._speed_limit:
            args += ["-l", str(self._speed_limit*8)] # scp wants kbits/sec
        remote_ptr = os.path.join(self.__dir, remote_path)
        remote_str = ""
        if self.__user:
            remote_str += self.__user + "@"
        remote_str += self.__host + ":" + remote_ptr

        return args, remote_str

    def download(self, remote_path, save_path):

        args = [EntropySshUriHandler._TXC_CMD]
        c_args, remote_str = self._setup_common_args(remote_path)
        tmp_save_path = save_path + EntropyUriHandler.TMP_TXC_FILE_EXT
        args.extend(c_args)
        args += ["-B", "-P", str(self.__port), remote_str, tmp_save_path]

        down_sts = self._fork_cmd(args) == 0
        if not down_sts:
            try:
                os.remove(tmp_save_path)
            except OSError:
                return False
            return False

        os.rename(tmp_save_path, save_path)
        return True

    def download_many(self, remote_paths, save_dir):

        if not remote_paths: # nothing to download
            return True

        def do_rmdir(path):
            try:
                shutil.rmtree(path, True)
            except (shutil.Error, OSError, IOError,):
                pass

        tmp_dir = tempfile.mkdtemp()

        args = [EntropySshUriHandler._TXC_CMD]
        c_args, remote_str = self._setup_common_args(remote_paths.pop())
        args += c_args
        args += ["-B", "-P", str(self.__port)]
        args += [remote_str] + [self._setup_common_args(x)[1] for x in \
            remote_paths] + [tmp_dir]

        down_sts = self._fork_cmd(args) == 0
        if not down_sts:
            do_rmdir(tmp_dir)
            return False

        # now move
        for tmp_file in os.listdir(tmp_dir):
            tmp_path = os.path.join(tmp_dir, tmp_file)
            save_path = os.path.join(save_dir, tmp_file)
            try:
                os.rename(tmp_path, save_path)
            except OSError:
                shutil.move(tmp_path, save_path)

        do_rmdir(tmp_dir)
        return True

    def upload(self, load_path, remote_path):

        args = [EntropySshUriHandler._TXC_CMD]
        tmp_remote_path = remote_path + EntropyUriHandler.TMP_TXC_FILE_EXT
        c_args, remote_str = self._setup_common_args(tmp_remote_path)
        args.extend(c_args)
        args += ["-B", "-P", str(self.__port), load_path, remote_str]

        upload_sts = self._fork_cmd(args) == 0
        if not upload_sts:
            self.delete(tmp_remote_path)
            return False

        # atomic rename
        return self.rename(tmp_remote_path, remote_path)

    def upload_many(self, load_path_list, remote_dir):

        def do_rm(path):
            try:
                os.remove(path)
            except OSError:
                pass

        # first of all, copy files renaming them
        tmp_file_map = {}
        for load_path in load_path_list:
            tmp_fd, tmp_path = tempfile.mkstemp(
                suffix = EntropyUriHandler.TMP_TXC_FILE_EXT,
                prefix = "._%s" % (os.path.basename(load_path),))
            os.close(tmp_fd)
            shutil.copy2(load_path, tmp_path)
            tmp_file_map[tmp_path] = load_path

        args = [EntropySshUriHandler._TXC_CMD]
        c_args, remote_str = self._setup_common_args(remote_dir)

        args += c_args
        args += ["-B", "-P", str(self.__port)]
        args += sorted(tmp_file_map.keys())
        args += [remote_str]

        upload_sts = self._fork_cmd(args) == 0
        if not upload_sts:
            for path in tmp_file_map.keys():
                do_rm(path)
            return False

        # atomic rename
        rename_fine = True
        for tmp_path, orig_path in tmp_file_map.items():
            tmp_file = os.path.basename(tmp_path)
            orig_file = os.path.basename(orig_path)
            tmp_remote_path = os.path.join(remote_dir, tmp_file)
            remote_path = os.path.join(remote_dir, orig_file)
            self.output(
                "<-> %s %s %s" % (
                    brown(tmp_file),
                    teal("=>"),
                    darkgreen(orig_file),
                ),
                header = "    ",
                back = True
            )
            rc = self.rename(tmp_remote_path, remote_path)
            if not rc:
                rename_fine = False
            do_rm(tmp_path)

        return rename_fine

    def _setup_fs_args(self):
        args = [EntropySshUriHandler._SSH_CMD]
        remote_str = ""
        if self.__user:
            remote_str += self.__user + "@"
        remote_str += self.__host
        return args, remote_str

    def rename(self, remote_path_old, remote_path_new):
        args, remote_str = self._setup_fs_args()
        remote_ptr_old = os.path.join(self.__dir, remote_path_old)
        remote_ptr_new = os.path.join(self.__dir, remote_path_new)
        args += [remote_str, "mv", remote_ptr_old, remote_ptr_new]
        return self._exec_cmd(args)[0] == 0

    def delete(self, remote_path):
        args, remote_str = self._setup_fs_args()
        remote_ptr = os.path.join(self.__dir, remote_path)
        args += [remote_str, "rm", remote_ptr]
        return self._exec_cmd(args)[0] == 0

    def delete_many(self, remote_paths):
        remote_ptrs = []
        args, remote_str = self._setup_fs_args()
        for remote_path in remote_paths:
            remote_ptr = os.path.join(self.__dir, remote_path)
            remote_ptrs.append(remote_ptr)
        args += [remote_str, "rm"] + remote_ptrs
        return self._exec_cmd(args)[0] == 0

    def get_md5(self, remote_path):
        args, remote_str = self._setup_fs_args()
        remote_ptr = os.path.join(self.__dir, remote_path)
        args += [remote_str, "md5sum", remote_ptr]
        exec_rc, output, error = self._exec_cmd(args)
        if exec_rc:
            return None
        return output.strip().split()[0]

    def list_content(self, remote_path):
        args, remote_str = self._setup_fs_args()
        remote_ptr = os.path.join(self.__dir, remote_path)
        args += [remote_str, "ls", "-1", remote_ptr]
        exec_rc, output, error = self._exec_cmd(args)
        if exec_rc:
            return []
        return [x for x in output.split("\n") if x]

    def list_content_metadata(self, remote_path):
        args, remote_str = self._setup_fs_args()
        remote_ptr = os.path.join(self.__dir, remote_path)
        args += [remote_str, "ls", "-1lA", remote_ptr]
        exec_rc, output, error = self._exec_cmd(args)
        if exec_rc:
            return []

        data = []
        for item in output.split("\n"):
            item = item.strip().split()
            if len(item) < 5:
                continue
            perms, owner, group, size, name = item[0], item[2], item[3], \
                item[4], item[-1]
            data.append((name, size, owner, group, perms,))
        return data

    def is_dir(self, remote_path):
        args, remote_str = self._setup_fs_args()
        remote_ptr = os.path.join(self.__dir, remote_path)
        args += [remote_str, "test", "-d", remote_ptr]
        exec_rc, output, error = self._exec_cmd(args)
        return exec_rc == 0

    def is_file(self, remote_path):
        args, remote_str = self._setup_fs_args()
        remote_ptr = os.path.join(self.__dir, remote_path)
        args += [remote_str, "test", "-f", remote_ptr]
        exec_rc, output, error = self._exec_cmd(args)
        return exec_rc == 0

    def is_path_available(self, remote_path):
        args, remote_str = self._setup_fs_args()
        remote_ptr = os.path.join(self.__dir, remote_path)
        args += [remote_str, "stat", remote_ptr]
        exec_rc, output, error = self._exec_cmd(args)
        return exec_rc == 0

    def makedirs(self, remote_path):
        args, remote_str = self._setup_fs_args()
        remote_ptr = os.path.join(self.__dir, remote_path)
        args += [remote_str, "mkdir", "-p", remote_ptr]
        exec_rc, output, error = self._exec_cmd(args)
        return exec_rc == 0

    def keep_alive(self):
        return

    def close(self):
        return
