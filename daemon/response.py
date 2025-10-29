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
daemon.response
~~~~~~~~~~~~~~~~~

This module provides a :class: `Response <Response>` object to manage and persist 
response settings (cookies, auth, proxies), and to construct HTTP responses
based on incoming requests. 

The current version supports MIME type detection, content loading and header formatting
"""
import datetime
import os
import mimetypes
from .dictionary import CaseInsensitiveDict

# Get the absolute path of the current file (response.py)
current_file = os.path.abspath(__file__)
# Get the daemon directory
daemon_dir = os.path.dirname(current_file)
# Get the project root directory (parent of daemon)
BASE_DIR = os.path.dirname(daemon_dir) + os.sep
print("[Response] Module file: {}".format(current_file))
print("[Response] Daemon dir: {}".format(daemon_dir))
print("[Response] BASE_DIR: {}".format(BASE_DIR))

class Response():   
    """The :class:`Response <Response>` object, which contains a
    server's response to an HTTP request.

    Instances are generated from a :class:`Request <Request>` object, and
    should not be instantiated manually; doing so may produce undesirable
    effects.

    :class:`Response <Response>` object encapsulates headers, content, 
    status code, cookies, and metadata related to the request-response cycle.
    It is used to construct and serve HTTP responses in a custom web server.

    :attrs status_code (int): HTTP status code (e.g., 200, 404).
    :attrs headers (dict): dictionary of response headers.
    :attrs url (str): url of the response.
    :attrsencoding (str): encoding used for decoding response content.
    :attrs history (list): list of previous Response objects (for redirects).
    :attrs reason (str): textual reason for the status code (e.g., "OK", "Not Found").
    :attrs cookies (CaseInsensitiveDict): response cookies.
    :attrs elapsed (datetime.timedelta): time taken to complete the request.
    :attrs request (PreparedRequest): the original request object.

    Usage::

      >>> import Response
      >>> resp = Response()
      >>> resp.build_response(req)
      >>> resp
      <Response>
    """

    __attrs__ = [
        "_content",
        "_header",
        "status_code",
        "method",
        "headers",
        "url",
        "history",
        "encoding",
        "reason",
        "cookies",
        "elapsed",
        "request",
        "body",
        "reason",
    ]


    def __init__(self, request=None):
        """
        Initializes a new :class:`Response <Response>` object.

        : params request : The originating request object.
        """

        self._content = False
        self._content_consumed = False
        self._next = None

        #: Integer Code of responded HTTP Status, e.g. 404 or 200.
        self.status_code = None

        #: Case-insensitive Dictionary of Response Headers.
        #: For example, ``headers['content-type']`` will return the
        #: value of a ``'Content-Type'`` response header.
        self.headers = {}

        #: URL location of Response.
        self.url = None

        #: Encoding to decode with when accessing response text.
        self.encoding = None

        #: A list of :class:`Response <Response>` objects from
        #: the history of the Request.
        self.history = []

        #: Textual reason of responded HTTP Status, e.g. "Not Found" or "OK".
        self.reason = None

        #: A of Cookies the response headers.
        self.cookies = CaseInsensitiveDict()

        #: The amount of time elapsed between sending the request
        self.elapsed = datetime.timedelta(0)

        #: The :class:`PreparedRequest <PreparedRequest>` object to which this
        #: is a response.
        self.request = None
        self.status_code = 200
        self.reason = "OK"
        self.headers = {}
        self.request = request


    def get_mime_type(self, path):
        """
        Determines the MIME type of a file based on its path.

        "params path (str): Path to the file.

        :rtype str: MIME type string (e.g., 'text/html', 'image/png').
        """

        try:
            mime_type, _ = mimetypes.guess_type(path)
        except Exception:
            return 'application/octet-stream'
        return mime_type or 'application/octet-stream'


    def prepare_content_type(self, mime_type='text/html'):
        """
        Prepares the Content-Type header and determines the base directory
        for serving the file based on its MIME type.

        :params mime_type (str): MIME type of the requested resource.

        :rtype str: Base directory path for locating the resource.

        :raises ValueError: If the MIME type is unsupported.
        """
        
        base_dir = ""

        # Processing mime_type based on main_type and sub_type
        main_type, sub_type = mime_type.split('/', 1)
        print("[Response] processing MIME main_type={} sub_type={}".format(main_type,sub_type))
        if main_type == 'text':
            self.headers['Content-Type']='text/{}'.format(sub_type)
            if sub_type == 'css':
                base_dir = BASE_DIR  # Don't append static/ since it's in the URL
                print("[Response] CSS file - using base_dir: {}".format(base_dir))
            elif sub_type == 'html':
                base_dir = BASE_DIR+"www/"
                print("[Response] HTML file - using base_dir: {}".format(base_dir))
            elif sub_type == 'plain' or sub_type == 'csv' or sub_type == 'xml':
                base_dir = BASE_DIR+"static/"
                print("[Response] Other text file - using base_dir: {}".format(base_dir))
            else:
                raise ValueError("Invalid MIME type: main_type={} sub_type={}".format(main_type,sub_type))
        elif main_type == 'image':
            base_dir = BASE_DIR  # Don't append static/ as it's in the URL path
            self.headers['Content-Type'] = 'image/{}'.format(sub_type)
            self.headers['Cache-Control'] = 'public, max-age=31536000'
            self.headers['Accept-Ranges'] = 'bytes'
            print("[Response] Image file - using base_dir: {}".format(base_dir))
        elif main_type == 'application':
            base_dir = BASE_DIR+"apps/"
            self.headers['Content-Type']='application/{}'.format(sub_type)
        elif main_type == 'video':
            base_dir = BASE_DIR+"static/"
            self.headers['Content-Type']='video/{}'.format(sub_type)
        #
        #  TODO: process other mime_type
        #        application/xml       
        #        application/zip
        #        ...
        #        text/csv
        #        text/xml
        #        ...
        #        video/mp4 
        #        video/mpeg
        #        ...
        #
        else:
            raise ValueError("Invalid MEME type: main_type={} sub_type={}".format(main_type,sub_type))

        return base_dir


    def build_content(self, path, base_dir):
        """
        Loads the objects file from storage space.

        :params path (str): relative path to the file.
        :params base_dir (str): base directory where the file is located.

        :rtype tuple: (int, bytes) representing content length and content data.
        """
        rel_path = path.lstrip('/') or 'index.html'
        print("[Response] BASE_DIR is: {}".format(BASE_DIR))
        print("[Response] Original path: {}, base_dir: {}".format(path, base_dir))

        # Keep the full path for static/ requests since base_dir is already set correctly
        # Only strip www/ prefix since that's handled differently
        if rel_path.startswith('www/'):
            rel_path = rel_path[len('www/'):]
            print("[Response] Stripped www/ prefix, new rel_path: {}".format(rel_path))

        filepath = os.path.join(base_dir, rel_path)
        abs_filepath = os.path.abspath(filepath)

        print("[Response] Debug paths:")
        print("  Base dir: {}".format(base_dir))
        print("  Original path from request: {}".format(path))
        print("  Relative path after processing: {}".format(rel_path))
        print("  Full filepath: {}".format(filepath))
        print("  Absolute filepath: {}".format(abs_filepath))
        print("  File exists: {}".format(os.path.exists(abs_filepath)))
        
        content = b''
        
        try: 
            # Check if file exists
            if not os.path.exists(filepath):
                print("[Response] File not found at path: {}".format(filepath))
                print("[Response] Absolute path was: {}".format(os.path.abspath(filepath)))
                print("[Response] Parent dir exists: {}".format(os.path.exists(os.path.dirname(filepath))))
                print("[Response] Parent dir contents: {}".format(os.listdir(os.path.dirname(filepath)) if os.path.exists(os.path.dirname(filepath)) else "parent not found"))
                return 0, b'404 Not Found'
            
            # Read file in binary mode
            with open(filepath, 'rb') as f:
                content = f.read()
            
            print("[Response] Successfully read {} bytes from {}".format(len(content), filepath))
            
        except Exception as e:
            print("[Response] Error reading file {}: {}".format(filepath, e))
            import traceback
            traceback.print_exc()
            content = b'500 Internal Server Error'
            
        return len(content), content

    def build_response_header(self, request):
        """
        Constructs the HTTP response headers based on the class:`Request <Request>
        and internal attributes.

        :params request (class:`Request <Request>`): incoming request object.

        :rtypes bytes: encoded HTTP response header.
        """
        reqhdr = request.headers
        rsphdr = self.headers

        # Build dynamic headers
        content_type = self.headers.get('Content-Type', 'text/html; charset=utf-8')

        headers = {
            "Accept": "{}".format(reqhdr.get("Accept", "application/json")),
            "Accept-Language": "{}".format(reqhdr.get("Accept-Language", "en-US,en;q=0.9")),
            "Authorization": "{}".format(reqhdr.get("Authorization", "Basic <credentials>")),
            "Cache-Control": "no-cache",
            "Content-Type": "{}".format(content_type),
            "Content-Length": "{}".format(len(self._content)),
            "Date": "{}".format(datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")),
            "Connection": "close",
            "Server": "WeApRous-HTTP-Server/1.0"
        }

        # Merge custom headers from the response (Location, Set-Cookie, etc.)
        for key, value in self.headers.items():
            headers[key] = value

        fmt_header = "HTTP/1.1 {} {}\r\n".format(
            self.status_code if self.status_code else 200,
            self.reason if self.reason else "OK"
        )

        for key, value in headers.items():
            fmt_header += "{}: {}\r\n".format(key, value)
        fmt_header += "\r\n"

        return str(fmt_header).encode('utf-8')


    def build_notfound(self):
        """
        Constructs a standard 404 Not Found HTTP response.

        :rtype bytes: Encoded 404 response.
        """

        return (
                "HTTP/1.1 404 Not Found\r\n"
                "Accept-Ranges: bytes\r\n"
                "Content-Type: text/html\r\n"
                "Content-Length: 13\r\n"
                "Cache-Control: max-age=86000\r\n"
                "Connection: close\r\n"
                "\r\n"
                "404 Not Found"
            ).encode('utf-8')
        
    def build_unauthorized(self):
        """
        Constructs a standard 401 Unauthorized HTTP response.

        :rtype bytes: Encoded 401 response.
        """
        unauthorized_html = """<!DOCTYPE html>
    <html>
    <head><title>401 Unauthorized</title></head>
    <body>
    <h1>401 Unauthorized</h1>
    <p>Access denied. Please login first.</p>
    </body>
    </html>"""
        
        content = unauthorized_html.encode('utf-8')
        
        return (
            "HTTP/1.1 401 Unauthorized\r\n"
            "Content-Type: text/html\r\n"
            "Content-Length: {}\r\n"
            "Connection: close\r\n"
            "\r\n".format(len(content))
        ).encode('utf-8') + content

    def build_response(self, request):
        """
        Builds a full HTTP response including headers and content based on the request.

        :params request (class:`Request <Request>`): incoming request object.

        :rtype bytes: complete HTTP response using prepared headers and content.
        """
        try:
            # If status and content already set by hook, use them
            if self.status_code == 401:
                return self.build_unauthorized()
            
            if self.status_code == 404:
                return self.build_notfound()
            
            # If content was set by hook handler
            if self._content:
                if isinstance(self._content, str):
                    self._content = self._content.encode('utf-8')
                
                if 'Content-Type' not in self.headers:
                    self.headers['Content-Type'] = 'text/html; charset=utf-8'
                
                if not self.status_code:
                    self.status_code = 200
                if not self.reason:
                    self.reason = "OK"
                    
                self._header = self.build_response_header(request)
                return self._header + self._content

            # Otherwise, try to serve file based on path
            path = request.path if hasattr(request, 'path') else '/'
            method = request.method if hasattr(request, 'method') else 'GET'

            mime_type = self.get_mime_type(path)
            print("[Response] {} path {} mime_type {}".format(method, path, mime_type))

            base_dir = ""

            # Determine content type and base directory
            if path.endswith('.html') or mime_type == 'text/html':
                base_dir = self.prepare_content_type(mime_type='text/html')
            elif mime_type == 'text/css':
                base_dir = self.prepare_content_type(mime_type='text/css')
                print("[Response] CSS request - base_dir: {}".format(base_dir))
            elif mime_type in ['image/png', 'image/jpeg', 'image/gif']:
                base_dir = self.prepare_content_type(mime_type=mime_type)
            elif mime_type in ['application/json', 'application/xml', 'application/zip']:
                base_dir = self.prepare_content_type(mime_type=mime_type)
            else:
                print("[Response] Unknown mime type, returning 404")
                return self.build_notfound()

            # Build content
            c_len, self._content = self.build_content(path, base_dir)

            # If content length is zero the file was not found or couldn't be read.
            # Return a proper 404 response instead of sending a 200 with a "404 Not Found" body.
            if c_len == 0:
                print("[Response] No content found for path {}, returning 404".format(path))
                return self.build_notfound()

            if not self.status_code:
                self.status_code = 200
            if not self.reason:
                self.reason = "OK"
                
            self._header = self.build_response_header(request)

            return self._header + self._content
            
        except Exception as e:
            print("[Response] Error building response: {}".format(e))
            import traceback
            traceback.print_exc()
            return self.build_notfound()