#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#

"""
daemon.httpadapter
~~~~~~~~~~~~~~~~~

This module provides a http adapter object to manage and persist 
http settings (headers, bodies). The adapter supports both
raw URL paths and RESTful route definitions, and integrates with
Request and Response objects to handle client-server communication.
"""

from .request import Request
from .response import Response
from .dictionary import CaseInsensitiveDict

class HttpAdapter:
    """
    A mutable :class:`HTTP adapter <HTTP adapter>` for managing client connections
    and routing requests.

    The `HttpAdapter` class encapsulates the logic for receiving HTTP requests,
    dispatching them to appropriate route handlers, and constructing responses.
    It supports RESTful routing via hooks and integrates with :class:`Request <Request>` 
    and :class:`Response <Response>` objects for full request lifecycle management.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket): Active socket connection.
        connaddr (tuple): Address of the connected client.
        routes (dict): Mapping of route paths to handler functions.
        request (Request): Request object for parsing incoming data.
        response (Response): Response object for building and sending replies.
    """

    __attrs__ = [
        "ip",
        "port",
        "conn",
        "connaddr",
        "routes",
        "request",
        "response",
    ]

    def __init__(self, ip, port, conn, connaddr, routes):
        """
        Initialize a new HttpAdapter instance.

        :param ip (str): IP address of the client.
        :param port (int): Port number of the client.
        :param conn (socket): Active socket connection.
        :param connaddr (tuple): Address of the connected client.
        :param routes (dict): Mapping of route paths to handler functions.
        """

        #: IP address.
        self.ip = ip
        #: Port.
        self.port = port
        #: Connection
        self.conn = conn
        #: Conndection address
        self.connaddr = connaddr
        #: Routes
        self.routes = routes
        #: Request
        self.request = Request()
        #: Response
        self.response = Response()

    def handle_client(self, conn, addr, routes):
        """
        Handle incoming client connection
        
        This method reads the request from the socket, prepares the request object,
        invokes the appropriate route handler if available, builds the response,
        and sends it back to the client.

        :param conn (socket): The client socket connection.
        :param addr (tuple): The client's address.
        :param routes (dict): The route mapping for dispatching requests.
        """
        # Connection handler.
        self.conn = conn        
        # Connection address.
        self.connaddr = addr
        # Request handler
        req = self.request
        # Response handler
        resp = Response()
        self.response = resp

        try:
            msg = conn.recv(1024).decode('utf-8')
            if not msg:
                conn.close()
                return
            
            print("[HttpAdapter] Raw request from {}:\n{}".format(addr, msg[:200]))
            
            req.prepare(msg, routes)
            
            print("[HttpAdapter] Parsed - METHOD: {} PATH: {}".format(req.method, req.path))
            print("[HttpAdapter] Headers: {}".format(req.headers))
            print("[HttpAdapter] Body: {}".format(req.body[:100] if req.body else 'None'))

            if req.hook:
                print("[HttpAdapter] Executing hook for path: {}".format(req.path))
                try:
                    hook_result = req.hook(headers=req.headers, body=req.body)
                    
                    print("[HttpAdapter] Hook returned: {}".format(hook_result))
                    
                    # Process hook result
                    if hook_result and isinstance(hook_result, dict):
                        # Set status code
                        if 'status' in hook_result:
                            resp.status_code = hook_result['status']
                            print("[HttpAdapter] Set status: {}".format(resp.status_code))
                        
                        # Set headers
                        if 'headers' in hook_result:
                            for key, value in hook_result['headers'].items():
                                resp.headers[key] = value
                                print("[HttpAdapter] Set header {}: {}".format(key, value))
                        
                        # Set cookie if present
                        if 'set_cookie' in hook_result:
                            resp.headers['Set-Cookie'] = hook_result['set_cookie']
                            print("[HttpAdapter] Set cookie: {}".format(hook_result['set_cookie']))
                        
                        # Set body/content
                        if 'body' in hook_result:
                            resp._content = hook_result['body']
                            if isinstance(resp._content, str):
                                resp._content = resp._content.encode('utf-8')
                            print("[HttpAdapter] Set content length: {}".format(len(resp._content)))
                        
                        # Update path if redirect
                        if 'path' in hook_result:
                            req.path = hook_result['path']
                            print("[HttpAdapter] Updated path to: {}".format(req.path))
                    
                except Exception as e:
                    print("[HttpAdapter] Hook execution error: {}".format(e))
                    import traceback
                    traceback.print_exc()
                    resp.status_code = 500
                    resp._content = b"Internal Server Error"
            else:
                print("[HttpAdapter] No hook found for path: {} (falling back to static handler)".format(req.path))

            # Build and send response
            print("[HttpAdapter] Building response with status: {}".format(resp.status_code))
            response = resp.build_response(req)
            print("[HttpAdapter] Sending response ({} bytes)".format(len(response)))
            conn.sendall(response)
            
        except Exception as e:
            print("[HttpAdapter] Error handling client: {}".format(e))
            import traceback
            traceback.print_exc()
            try:
                error_response = b"HTTP/1.1 500 Internal Server Error\r\n\r\n500 Internal Server Error"
                conn.sendall(error_response)
            except:
                pass
        finally:
            try:
                conn.close()
            except:
                pass
            print("[HttpAdapter] Connection closed for {}".format(addr))

    @property
    def extract_cookies(self, req, resp):
        """
        Build cookies from the :class:`Request <Request>` headers.

        :param req:(Request) The :class:`Request <Request>` object.
        :param resp: (Response) The res:class:`Response <Response>` object.
        :rtype: cookies - A dictionary of cookie key-value pairs.
        """
        cookies = {}
        if hasattr(req, 'headers') and req.headers:
            cookie_header = req.headers.get('cookie', '')
            if cookie_header:
                for pair in cookie_header.split(';'):
                    pair = pair.strip()
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        cookies[key.strip()] = value.strip()
        
        return cookies

    def build_response(self, req, resp):
        """Builds a :class:`Response <Response>` object 

        :param req: The :class:`Request <Request>` used to generate the response.
        :param resp: The  response object.
        :rtype: Response
        """
        response = Response()

        # Set encoding.
        response.encoding = 'utf-8'  # Default encoding
        response.raw = resp
        response.reason = response.raw.reason

        if isinstance(req.url, bytes):
            response.url = req.url.decode("utf-8")
        else:
            response.url = req.url

        # Add new cookies from the server.
        response.cookies = self.extract_cookies(req, resp)

        # Give the Response some context.
        response.request = req
        response.connection = self

        return response

    # def get_connection(self, url, proxies=None):
        # """Returns a url connection for the given URL. 

        # :param url: The URL to connect to.
        # :param proxies: (optional) A Requests-style dictionary of proxies used on this request.
        # :rtype: int
        # """

        # proxy = select_proxy(url, proxies)

        # if proxy:
            # proxy = prepend_scheme_if_needed(proxy, "http")
            # proxy_url = parse_url(proxy)
            # if not proxy_url.host:
                # raise InvalidProxyURL(
                    # "Please check proxy URL. It is malformed "
                    # "and could be missing the host."
                # )
            # proxy_manager = self.proxy_manager_for(proxy)
            # conn = proxy_manager.connection_from_url(url)
        # else:
            # # Only scheme should be lower case
            # parsed = urlparse(url)
            # url = parsed.geturl()
            # conn = self.poolmanager.connection_from_url(url)

        # return conn


    def add_headers(self, request):
        """
        Add headers to the request.

        This method is intended to be overridden by subclasses to inject
        custom headers. It does nothing by default.

        
        :param request: :class:`Request <Request>` to add headers to.
        """
        pass

    def build_proxy_headers(self, proxy):
        """Returns a dictionary of the headers to add to any request sent
        through a proxy. 

        :class:`HttpAdapter <HttpAdapter>`.

        :param proxy: The url of the proxy being used for this request.
        :rtype: dict
        """
        headers = {}
        #
        # TODO: build your authentication here
        #       username, password =...
        # we provide dummy auth here
        #
        # Extract authentication credentials
        # In a real implementation, this could come from config, environment variables, or request
        username, password = ("user1", "password")
        
        # Build Proxy-Authorization header using Basic Authentication
        # Format: "Basic base64(username:password)"
        if username and password:
            import base64
            # Encode credentials in base64 format for Basic Auth
            credentials = "{}:{}".format(username, password)
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            headers["Proxy-Authorization"] = "Basic {}".format(encoded_credentials)

        return headers