# LocalSFTPServer

`localsftpserver` is a simple single-threaded SFTP server based on Paramiko's SFTPServer.


## Installation

Using `pip`::
```shell
pip install git+https://github.com/dgegen/LocalSFTPServer.git
```


## Examples

### From shell

```shell
localsftpserver
```

### On a thread in Python

```python
import fsspec
import paramiko
from localsftpserver import SFTPServer


# Using the server as a context manager
with SFTPServer('test_rsa.key') as server:
    storage_options = {
        "host": server.host,
        "port": server.port,
        "username": "",
        "password": "",
        "key_filename": str(server.key_filename),
        "timeout": 10,
    }
    sftp_fs = fsspec.filesystem("sftp", **storage_options)
    print(sftp_fs.listdir(server.root_path))



# Or opening and closing it manually
server = SFTPServer('test_rsa.key')
server.start()  # See server.start_sync() for starting the server on the same thread.

storage_options = {
    "host": server.host,
    "port": server.port,
    "username": "",
    "password": "",
    "key_filename": str(server.key_filename),
    "timeout": 10,
}
sftp_fs = fsspec.filesystem("sftp", **storage_options)
print(sftp_fs.listdir(server.root_path))

server.stop()
```