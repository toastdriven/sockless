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
import select
import socket


__author__ = 'Daniel Lindsley'
__license__ = 'BSD'
__version__ = (0, 9, 0)


DEFAULT_TIMEOUT = 60
DEFAULT_MAX_CONNS = 5


class SocklessException(Exception): pass
class TimedOut(SocklessException): pass
class AddressNotFound(SocklessException): pass
class BrokenConnection(SocklessException): pass
class NotConnected(SocklessException): pass


def split_address(address):
    host, port = address.split(':')
    return host, int(port)


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
        return split_address(address)

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
        return self

    def __next__(self):
        return self.readline()

    def next(self):
        return self.__next__()

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


class NonBlockingSocket(object):
    def __init__(self, address):
        self.address = address
        self._conn = None
        self._buffer = ''
        self._readable = False
        self._writable = False

    def split_address(self, address):
        return split_address(address)

    def _check_conn(self):
        if not self._conn:
            raise NotConnected("Not connected to {}".format(
                self.address
            ))

    def open(self, mode='rw'):
        host, port = self.split_address(self.address)

        if mode == 'rw':
            self._readable = True
            self._writable = True
        elif mode == 'r':
            self._readable = True
        elif mode == 'w':
            self._writable = True

        try:
            self._conn = socket.create_connection((host, port))
            self._conn.setblocking(0)
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

    def close(self):
        self._check_conn()
        self._conn.close()

    def select(self):
        self._check_conn()
        rlist = []
        wlist = []

        if self._readable:
            rlist.append(self._conn)

        if self._writable:
            wlist.append(self._conn)

        return select.select(rlist, wlist, [])

    def readable(self):
        rlist, wlist, xlist = self.select()
        return len(rlist) > 0

    def writable(self):
        rlist, wlist, xlist = self.select()
        return len(wlist) > 0

    def read(self, size=4096):
        rlist, wlist, xlist = self.select()
        amount_read = 0

        if not rlist:
            return amount_read

        rsock = rlist[0]

        while rsock:
            received = rsock.recv(size)
            # Unfortunately, we can't detect broken connections here, since
            # this method doesn't block until the send *actually* happens.
            # Lots of false positivites trying to detect zero conditions.
            amount_read += len(received)
            self._buffer += received
            rlist, wlist, xlist = self.select()

            if rlist:
                rsock = rlist[0]
            else:
                rsock = None

        return amount_read

    def readline(self):
        return self.readlines(limit=1)

    def readlines(self, limit=-1):
        if limit == 0:
            return []

        while True:
            rsize = self.read()

            if not rsize:
                break

        if not self._buffer:
            return []

        if limit >= 0:
            line, self._buffer = self._buffer.split('\n', 1)
            return [line]

        lines = self._buffer.split('\n')

        if not self._buffer.endswith('\n'):
            self._buffer = lines.pop()
        else:
            self._buffer = ''

        return lines

    def write(self, data):
        rlist, wlist, xlist = self.select()

        if not wlist:
            # FIXME: Not sure this should just fail. Should I buffer instead?
            return False

        wsock = wlist[0]
        amount_sent = wsock.sendall(data)
        return amount_sent

    def __iter__(self):
        return self

    def __next__(self):
        return self.readline()


@contextlib.contextmanager
def open(address, timeout=DEFAULT_TIMEOUT, mode='rw'):
    sock = Socket(address, timeout=timeout)
    sock.open(mode)

    try:
        yield sock
    finally:
        sock.close()
