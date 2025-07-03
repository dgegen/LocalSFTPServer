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

import argparse
import sys
import textwrap
import logging

from localsftpserver.sftp_server import SFTPServer, HOST, PORT, BACKLOG


def parse_args():
    usage = """\
    usage: sftpserver [options]
    -k/--key_filename should be specified
    """
    parser = argparse.ArgumentParser(usage=textwrap.dedent(usage))
    parser.add_argument(
        "--host",
        dest="host",
        default=HOST,
        help="listen on HOST [default: %(default)s]",
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        type=int,
        default=PORT,
        help="listen on PORT [default: %(default)d]",
    )
    parser.add_argument(
        "-l",
        "--level",
        dest="level",
        default="INFO",
        help="Debug level: WARNING, INFO, DEBUG [default: %(default)s]",
    )
    parser.add_argument(
        "-k",
        "--key_filename",
        dest="key_filename",
        metavar="FILE",
        help="Path to private key, for example /tmp/test_rsa.key",
    )
    parser.add_argument(
        "--backlog",
        dest="backlog",
        type=int,
        default=BACKLOG,
        help="Maximum number of queued connections [default: %(default)d]",
    )
    parser.add_argument(
        "--root_path",
        dest="root_path",
        default="",
        help="Path to the server root directory [default: current working directory]",
    )

    args = parser.parse_args()
    if args.key_filename is None:
        parser.print_help()
        sys.exit(-1)

    return args


def main():
    args = parse_args()

    logging.basicConfig(level=args.level)
    logging.info(
        f"Starting SFTP server on {args.host}:{args.port} with key file {args.key_filename}"
    )
    sftp_server = SFTPServer(
        host=args.host,
        port=args.port,
        key_filename=args.key_filename,
        level=args.level.upper(),
        backlog=args.backlog,
        root_path=args.root_path,
    )
    try:
        sftp_server.start_sync()
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    finally:
        sftp_server.stop()


if __name__ == "__main__":
    main()
