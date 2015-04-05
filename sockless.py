"""
sockless
========

A friendlier interface to `socket`.

``sockless`` emulates file-like objects, allowing you to call familiar methods
& iterate over the lines. It also includes

Usage::

    import sockless


    with sockless.open('irc.freenode.net:6665', mode='rw') as sock:
        # Writing.
        sock.write('NICK atestbot\r\n')
        sock.write('USER atestbot bot@aserver.com unused :atestbot\r\n')
        sock.write('JOIN #testbot\r\n')

        # Reading lines from a socket.
        for line in sock:
            if not line:
                break

            if 'End of /NAMES list' in line:
                print "Successfully connected & joined. Quitting."
                break

            print line.strip()

"""
import contextlib

try:
    from gevent import socket
except ImportError:
    import socket


__author__ = 'Daniel Lindsley'
__license__ = 'BSD'
__version__ = (0, 8, 0)


DEFAULT_TIMEOUT = 60
DEFAULT_MAX_CONNS = 5


class SocklessException(Exception): pass
class TimedOut(SocklessException): pass
class AddressNotFound(SocklessException): pass
class BrokenConnection(SocklessException): pass
class NotConnected(SocklessException): pass


class Socket(object):
    def __init__(
        self,
        address,
        timeout=DEFAULT_TIMEOUT,
    ):
        self.address = address
        self.timeout = timeout

        self.closed = True

        self._conn = None
        self._conn_file = None
        self._readable = True
        self._writable = False

    def split_address(self, address):
        host, port = address.split(':')
        return host, int(port)

    def open(self, mode='rw'):
        host, port = self.split_address(self.address)

        if mode == 'r':
            self._set_readable()
        elif mode == 'w':
            self._set_writable()
        elif mode == 'rw':
            self._set_read_write()

        try:
            self._conn = socket.create_connection(
                (host, port),
                timeout=self.timeout
            )
        except socket.gaierror:
            raise AddressNotFound("Could connect to {}:{}".format(
                host,
                port
            ))
        except socket.timeout:
            raise TimedOut("Connection to {}:{} timed out".format(
                host,
                port
            ))

        self._conn_file = self._conn.makefile(mode)

    def _set_readable(self):
        self._readable = True
        self._writable = False

    def _set_writable(self):
        self._readable = False
        self._writable = True

    def _set_read_write(self):
        self._readable = True
        self._writable = True

    def _send(self, data):
        self._conn_file.write(data)
        self._conn_file.flush()

    # File-like methods

    def _check_conn(self):
        if not self._conn or not self._conn_file:
            raise NotConnected("Not connected to {}".format(
                self.address
            ))

    def close(self):
        self._check_conn()
        # Need to close both to be doing the right thing.
        self._conn_file.close()
        self._conn.close()

    def readable(self):
        return self._readable

    def writable(self):
        return self._writable

    def read(self, size=-1):
        if size <= -1:
            return self.readall()

        self._check_conn()
        return self._conn_file.read(size)

    def readall(self):
        self._check_conn()
        return self._conn_file.read()

    def readline(self):
        self._check_conn()
        return self._conn_file.readline()

    def readlines(self):
        self._check_conn()
        return self._conn_file.readlines()

    def write(self, data):
        return self._send(data)

    def __iter__(self):
        # FIXME: Check yo'self.
        return self

    def next(self):
        # FIXME: Check yo'self.
        return self.readline()

    # Socket-specific methods

    @property
    def hostname(self):
        return socket.gethostname()

    @property
    def fully_qualified_domain_name(self):
        return socket.getfqdn()

    fqdn = fully_qualified_domain_name

    @property
    def remote_ip(self):
        self._check_conn()
        return self._conn.getpeername()[0]

    @property
    def remote_port(self):
        self._check_conn()
        return self._conn.getpeername()[1]

    @property
    def local_ip(self):
        self._check_conn()
        return self._conn.getsockname()[0]

    @property
    def local_port(self):
        self._check_conn()
        return self._conn.getsockname()[1]

    def resolve_dns(self, address=None):
        if address is None:
            address = self.address

        host, port = self.split_address(address)
        bits = socket.getaddrinfo(host, port)
        return [bit[4] for bit in bits]


@contextlib.contextmanager
def open(address, timeout=DEFAULT_TIMEOUT, mode='rw'):
    sock = Socket(address, timeout=timeout)
    sock.open(mode)

    try:
        yield sock
    finally:
        sock.close()
