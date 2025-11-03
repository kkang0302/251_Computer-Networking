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
daemon.request
~~~~~~~~~~~~~~~~~

This module provides a Request object to manage and persist 
request settings (cookies, auth, proxies).
"""
from .dictionary import CaseInsensitiveDict

class Request():
    """The fully mutable "class" `Request <Request>` object,
    containing the exact bytes that will be sent to the server.

    Instances are generated from a "class" `Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    Usage::

      >>> import deamon.request
      >>> req = request.Request()
      ## Incoming message obtain aka. incoming_msg
      >>> r = req.prepare(incoming_msg)
      >>> r
      <Request>
    """
    __attrs__ = [
        "method",
        "url",
        "headers",
        "body",
        "reason",
        "cookies",
        "body",
        "routes",
        "hook",
    ]

    def __init__(self):
        #: HTTP verb to send to the server.
        self.method = None
        #: HTTP URL to send the request to.
        self.url = None
        #: dictionary of HTTP headers.
        self.headers = CaseInsensitiveDict()
        #: HTTP path
        self.path = None        
        # The cookies set used to create Cookie header
        self.cookies = CaseInsensitiveDict()
        #: request body to send to the server.
        self.body = None
        #: Routes
        self.routes = {}
        #: Hook point for routed mapped-path
        self.hook = None

    def extract_request_line(self, request):
        try:
            lines = request.split('\r\n')
            request_line = lines[0]
            parts = request_line.split(' ')
            method = parts[0]
            path = parts[1]
            version = parts[2]
            return method, path, version
        except Exception as e:
            print("[Request] Failed to extract request line: {}".format(e))
            return None, None, None
        
    def prepare_headers(self, request):
        """Prepares the given HTTP headers."""
        lines = request.split('\r\n')
        headers = {}
        for line in lines[1:]:
            if ': ' in line:
                key, val = line.split(': ', 1)
                headers[key.strip().lower()] = val.strip()
        return headers

    def prepare(self, msg, routes):
        """Parse HTTP request and set hook based on routes"""
        try:
            # reset per-request state
            self.headers = CaseInsensitiveDict()
            self.cookies = CaseInsensitiveDict()
            self.body = None

            lines = msg.split('\r\n')
            
            if not lines:
                return
            
            # Parse request line
            request_line = lines[0].split()
            if len(request_line) >= 2:
                self.method = request_line[0]
                self.path = request_line[1]
                self.url = self.path
            
            print("[Request] Parsing request: {} {}".format(self.method, self.path))
            
            # Parse headers
            header_end = 0
            for i, line in enumerate(lines[1:], 1):
                if line == '':
                    header_end = i
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    self.headers[key.strip().lower()] = value.strip()
            
            # Parse body
            if header_end > 0 and len(lines) > header_end + 1:
                self.body = '\r\n'.join(lines[header_end + 1:])
            else:
                self.body = ''
            
            print("[Request] Headers parsed: {}".format(dict(self.headers)))
            print("[Request] Body: {}".format(self.body[:100] if self.body else 'None'))
            
            # Find and set hook from routes
            self.hook = None
            if routes and self.path in routes:
                route = routes[self.path]
                print("[Request] Found route for path: {}".format(self.path))
                
                if self.method in route:
                    self.hook = route[self.method]
                    if hasattr(self.hook, '__name__'):
                        print("[Request] Hook set: {} for {} {}".format(self.hook.__name__, self.method, self.path))
                    else:
                        print("[Request] Hook set for {} {}".format(self.method, self.path))
                else:
                    print("[Request] Method {} not found in route".format(self.method))
                    print("[Request] Available methods: {}".format(list(route.keys())))
            else:
                print("[Request] No route found for path: {}".format(self.path))
                if routes:
                    print("[Request] Available routes: {}".format(list(routes.keys())))
                else:
                    print("[Request] Routes dict is empty or None")
                    
        except Exception as e:
            print("[Request] Error in prepare(): {}".format(e))
            import traceback
            traceback.print_exc()
            raise
        
    def prepare_body(self, data, files, json=None):
        if data:
            self.body = data
        elif json:
            import json as json_lib
            self.body = json_lib.dumps(json)
        else: 
            self.body = None
        self.prepare_content_length(self.body)
        #
        # TODO prepare the request authentication
        #
        if self.headers and 'authorization' in self.headers:
            self.prepare_auth(self.headers['authorization'], self.url)
	# self.auth = ...
        else :
            self.auth = None
        return


    def prepare_content_length(self, body):
        if not self.headers:
            self.headers = {}
        if body:
            if isinstance(body, str):
                length = len(body.encode('utf-8'))
            else:
                length = len(body)
            self.headers["Content-Length"] = str(length)
        else:
            self.headers["Content-Length"] = "0"
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        return


    def prepare_auth(self, auth, url=""):
        #
        # TODO prepare the request authentication
        #
	# self.auth = ...
        if auth and isinstance(auth, str):
            if auth.startswith("Basic "):
                try:
                    auth_data = auth.split(" ")[1]
                    self.auth = ('Basic', auth_data)
                    print("[Request] Basic Auth detected")
                except Exception as e:
                    print("[Request] Failed to decode Basic Auth: {}".format(e))
                    self.auth = None
            elif auth.startswith("Bearer "):
                token = auth.split(" ")[1]
                self.auth = token
                print("[Request] Bearer Token detected")
            else: 
                print("[Request] Unsupported auth type")
                self.auth = None
        else:
            self.auth = None

        return

    def prepare_cookies(self, cookies):
            self.headers["Cookie"] = cookies

    def parse_body(self):
        if not hasattr(self, 'body') or not self.body:
            return {}
        
        content_type = self.headers.get('content-type', '')
        if 'application/x-www-form-urlencoded' in content_type:
            params = {}
            for para in self.body.split('&'):
                if '=' in para:
                    key, val = para.split('=', 1)
                    try:
                        from urllib.parse import unquote_plus
                        params[key] = unquote_plus(val)
                    except (ImportError, AttributeError):
                        params[key] = val.replace('+', ' ')
            return params
        elif 'application/json' in content_type:
            try:
                import json
                return json.loads(self.body)
            except Exception as e:
                print("[Request] Failed to parse JSON body: {}".format(e))
                return {}
        return {'raw': self.body}