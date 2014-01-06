import requests

from os import environ

from etcd.config import DEFAULT_HOSTNAME, DEFAULT_PORT, DEFAULT_SCHEME
from etcd.directory_ops import DirectoryOps
from etcd.node_ops import NodeOps
from etcd.server_ops import ServerOps
from etcd.inorder_ops import InOrderOps
from etcd.modules.lock import LockMod
from etcd.modules.leader import LeaderMod
from etcd.response import ResponseV2

# TODO: Add support for SSL: 
#   curl --key ./fixtures/ca/server2.key.insecure --cert ./fixtures/ca/server2.crt --cacert ./fixtures/ca/server-chain.pem -L https://127.0.0.1:4001/v2/keys/foo -XPUT -d value=bar -v


class _Modules(object):
    def __init__(self, client):
        self.__client = client

    @property
    def lock(self):
        """Return an instance of the class having the lock functionality.

        :rtype: :class:`etcd.response.ResponseV2`
        """

        try:
            return self.__lock
        except AttributeError:
            self.__lock = LockMod(self.__client)
            return self.__lock

    @property
    def leader(self):
        """Return an instance of the class having the leader-election 
        functionality.

        :rtype: :class:`etcd.modules.leader.LeaderMod`
        """

        try:
            return self.__leader
        except AttributeError:
            self.__leader = LeaderMod(self.__client)
            return self.__leader


class Client(object):
    """The main channel of functionality for the client. Connects to the 
    server, and provides functions via properties.
    """

    def __init__(self, hostname=DEFAULT_HOSTNAME, port=DEFAULT_PORT, scheme=DEFAULT_SCHEME, debug=False):
        """Set the given node.

        :param hostname: Hostname of server
        :param port: Port of server
        :param scheme: URI scheme
        :param debug: Whether to print debug verbosity (can be provided as the 
                      ETCD_DEBUG environment variable, as well)

        :type hostname: string
        :type port: int
        :type scheme: string
        :type debug: bool

        :raises: ValueError
        """

        debug_override = environ.get('ETCD_DEBUG')
        if debug_override is not None and debug_override == 'true':
            debug = True

        self.__debug = debug

        self.__hostname = hostname
        self.__port = port
        self.__scheme = scheme

        self.__prefix = ('%s://%s:%s' % (scheme, hostname, port))
        self.debug("PREFIX= [%s]" % (self.__prefix))

# TODO: Remove the version check after debugging.
# TODO: Can we implicitly read the version from the response/headers?
        self.__version = self.server.get_version()
        self.debug("Version: %s" % (self.__version))

        if self.__version.startswith('0.2') is False:
            raise ValueError("We don't support an etcd version older than 0.2.0 .")

    def __str__(self):
        return ('<ETCD %s>' % (self.__prefix))

    def debug(self, message):
        if self.__debug is True:
            print("EC: %s" % (message))

    def send(self, version, verb, path, value=None, parameters=None, data=None, module=None, return_raw=False):
        """Build and execute a request.

        :param version: Version of API
        :param verb: Verb of request ('get', 'post', etc..)
        :param path: URL path
        :param value: Value to be converted to string and passed as "value" in 
                      the POST data.
        :param parameters: Dictionary of values to be passed via URL query.
        :param data: Dictionary of values to be passed via POST data.
        :param module: Name of the etcd module that hosts the functionality.
        :param return_raw: Whether to return a 
                           :class:`etcd.response.ResponseV2` object or the raw 
                           Requests response.

        :type version: int
        :type verb: string
        :type path: string
        :type value: scalar or None
        :type parameters: dictionary or None
        :type data: dictionary or None
        :type module: string or None
        :type return_raw: bool

        :returns: Response object
        :rtype: :class:`etcd.response.ResponseV2`
        """

        if parameters is None:
            parameters = {}

        if data is None:
            data = {}

        if version != 2:
            raise ValueError("We were told to send a version (%d) request, "
                             "which is not supported." % (version))
        else:
            response_cls = ResponseV2

        send = getattr(requests, verb)

        if module is None:
            url = ('%s/v%d%s' % (self.__prefix, version, path))
        else:
            url = ('%s/mod/v%d/%s%s' % (self.__prefix, version, module, path))

        if value is not None:
            data['value'] = value

        args = { 'params': parameters, 'data': data }

        self.debug("Request(%s)=[%s] params=[%s] data_keys=[%s]" % 
                   (verb, url, parameters, args['data'].keys()))

        r = send(url, **args)
        r.raise_for_status()

        if return_raw is True:
            return r

        return response_cls(r, verb, path)

    @property
    def prefix(self):
        """Return the URL prefix for the server.

        :rtype: string
        """

        return self.__prefix

    @property
    def directory(self):
        """Return an instance of the class having the directory functionality.

        :rtype: :class:`etcd.directory_ops.DirectoryOps`
        """

        try:
            return self.__directory
        except AttributeError:
            self.__directory = DirectoryOps(self)
            return self.__directory

    @property
    def node(self):
        """Return an instance of the class having the general node 
        functionality.

        :rtype: :class:`etcd.node_ops.NodeOps`
        """

        try:
            return self.__node
        except AttributeError:
            self.__node = NodeOps(self)
            return self.__node

    @property
    def server(self):
        """Return an instance of the class having the server functionality.

        :rtype: :class:`etcd.server_ops.ServerOps`
        """

        try:
            return self.__server
        except AttributeError:
            self.__server = ServerOps(self)
            return self.__server

    @property
    def inorder(self):
        """Return an instance of the class having the "in-order keys" 
        functionality.

        :rtype: :class:`etcd.inorder_ops.InOrderOps`
        """

        try:
            return self.__inorder
        except AttributeError:
            self.__inorder = InOrderOps(self)
            return self.__inorder

    @property
    def module(self):
        """Return an instance of the class that hosts the functionality 
        provided by individual modules.

        :rtype: :class:`etcd.client._Modules`
        """

        try:
            return self.__module
        except AttributeError:
            self.__module = _Modules(self)
            return self.__module
