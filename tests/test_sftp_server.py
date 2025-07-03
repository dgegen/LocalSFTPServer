import os
import os.path
import tempfile
import pytest
import fsspec
from localsftpserver import SFTPServer
import time


@pytest.fixture
def sftp_server():
    """Fixture to start and stop the SFTP server."""
    key_filename = os.path.join(tempfile.gettempdir(), "test_rsa.key")
    if os.path.exists(key_filename):
        os.remove(key_filename)
    server = SFTPServer(key_filename)
    server.start()
    yield server
    server.stop()
    if os.path.exists(key_filename):
        os.remove(key_filename)


def test_sftp_server_start_and_listdir(sftp_server):
    """Test starting the SFTP server and listing directories."""
    storage_options = {
        "host": sftp_server.host,
        "port": sftp_server.port,
        "username": "",
        "password": "",
        "key_filename": str(sftp_server.key_filename),
        "timeout": 10,
    }

    # Create an SFTP filesystem instance
    sftp_fs = fsspec.filesystem("sftp", **storage_options)

    # List the root path of the server
    dir_list = sftp_fs.listdir(sftp_server.root_path)

    # Check if the directory list is as expected (it may be empty initially)
    assert isinstance(dir_list, list)


def test_sftp_server_context_manager():
    """Test using the SFTP server as a context manager."""
    key_filename = os.path.join(tempfile.gettempdir(), "test_rsa.key")

    with SFTPServer(key_filename) as server:
        storage_options = {
            "host": server.host,
            "port": server.port,
            "username": "",
            "password": "",
            "key_filename": str(server.key_filename),
            "timeout": 10,
        }

        # Create an SFTP filesystem instance
        sftp_fs = fsspec.filesystem("sftp", **storage_options)

        # List the root path of the server
        dir_list = sftp_fs.listdir(server.root_path)

        # Check if the directory list is as expected (it may be empty initially)
        assert isinstance(dir_list, list)


def test_rsa_key_generation():
    """Test RSA key generation."""
    key_filename = os.path.join(tempfile.gettempdir(), "test_rsa.key")

    # Ensure the key file does not exist before starting the server
    if os.path.exists(key_filename):
        os.remove(key_filename)

    assert not os.path.exists(key_filename)
    server = SFTPServer(key_filename)
    server.start()
    server.stop()
    os.remove(key_filename)  # Clean up the key file after the test


def test_file_upload(sftp_server):
    """Test uploading a file to the SFTP server."""
    storage_options = {
        "host": sftp_server.host,
        "port": sftp_server.port,
        "username": "",
        "password": "",
        "key_filename": str(sftp_server.key_filename),
        "timeout": 10,
    }

    # Create an SFTP filesystem instance
    sftp_fs = fsspec.filesystem("sftp", **storage_options)

    # Create a temporary file to upload
    local_file_path = tempfile.mktemp()
    with open(local_file_path, "w") as f:
        f.write("Hello, SFTP!")

    # Upload the file
    sftp_fs.put(local_file_path, "uploaded_file.txt")

    # Check if the file exists on the server
    dir_list = sftp_fs.listdir(sftp_server.root_path)
    assert any(item["name"].endswith("uploaded_file.txt") for item in dir_list)


def test_directory_creation_and_removal(sftp_server):
    """Test creating a directory on the SFTP server."""
    storage_options = {
        "host": sftp_server.host,
        "port": sftp_server.port,
        "username": "",
        "password": "",
        "key_filename": str(sftp_server.key_filename),
        "timeout": 10,
    }

    # Create an SFTP filesystem instance
    sftp_fs = fsspec.filesystem("sftp", **storage_options)

    # Define the new directory name
    new_dir = "new_directory"

    # Check if the directory already exists and remove it if it does
    if new_dir in [item["name"] for item in sftp_fs.listdir(sftp_server.root_path)]:
        sftp_fs.rm(new_dir)

    # Delete the directory if it exists
    if os.path.exists(os.path.join(sftp_server.root_path, new_dir)):
        sftp_fs.rm(new_dir)
    assert new_dir not in [
        item["name"] for item in sftp_fs.listdir(sftp_server.root_path)
    ], f"Directory {new_dir} already exists before test."

    # Create a new directory
    sftp_fs.mkdir(new_dir)

    # Verify the directory was created
    assert os.path.exists(os.path.join(sftp_server.root_path, new_dir)), (
        f"Directory {new_dir} was not created."
    )

    # Clean up: remove the created directory
    sftp_fs.rm(new_dir)

    # Verify the directory has been removed
    dir_list_after_removal = sftp_fs.listdir(sftp_server.root_path)
    assert not any(item["name"] == new_dir for item in dir_list_after_removal)


def test_file_download(sftp_server):
    """Test downloading a file from the SFTP server."""
    storage_options = {
        "host": sftp_server.host,
        "port": sftp_server.port,
        "username": "",
        "password": "",
        "key_filename": str(sftp_server.key_filename),
        "timeout": 10,
    }

    # Create an SFTP filesystem instance
    sftp_fs = fsspec.filesystem("sftp", **storage_options)

    # Create and upload a file
    local_file_path = tempfile.mktemp()
    with open(local_file_path, "w") as f:
        f.write("Hello, SFTP!")
    sftp_fs.put(local_file_path, "download_test.txt")

    # Download the file
    download_path = tempfile.mktemp()
    sftp_fs.get("download_test.txt", download_path)

    # Verify the content of the downloaded file
    with open(download_path, "r") as f:
        content = f.read()
    assert content == "Hello, SFTP!"


def test_file_deletion(sftp_server):
    """Test deleting a file from the SFTP server."""
    storage_options = {
        "host": sftp_server.host,
        "port": sftp_server.port,
        "username": "",
        "password": "",
        "key_filename": str(sftp_server.key_filename),
        "timeout": 10,
    }

    # Create an SFTP filesystem instance
    sftp_fs = fsspec.filesystem("sftp", **storage_options)

    # Create and upload a file
    local_file_path = tempfile.mktemp()
    with open(local_file_path, "w") as f:
        f.write("This file will be deleted.")
    sftp_fs.put(local_file_path, "file_to_delete.txt")

    # Delete the file
    sftp_fs.rm("file_to_delete.txt")

    # Verify the file has been deleted
    assert "file_to_delete.txt" not in sftp_fs.listdir(sftp_server.root_path)


if __name__ == "__main__":
    pytest.main()
