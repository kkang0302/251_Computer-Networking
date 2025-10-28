# #
# # Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# # All rights reserved.
# # This file is part of the CO3093/CO3094 course,
# # and is released under the "MIT License Agreement". Please see the LICENSE
# # file that should have been included as part of this package.
# #
# # WeApRous release
# #
# # The authors hereby grant to Licensee personal permission to use
# # and modify the Licensed Source Code for the sole purpose of studying
# # while attending the course
# #


# """
# start_backend
# ~~~~~~~~~~~~~~~~~

# This module provides a simple entry point for deploying backend server process
# using the socket framework. It parses command-line arguments to configure the
# server's IP address and port, and then launches the backend server.
# """

# import socket
# import argparse

# from daemon import create_backend

# # Default port number used if none is specified via command-line arguments.
# PORT = 9000 

# if __name__ == "__main__":
#     """
#     Entry point for launching the backend server.

#     This block parses command-line arguments to determine the server's IP address
#     and port. It then calls `create_backend(ip, port)` to start the RESTful
#     application server.

#     :arg --server-ip (str): IP address to bind the server (default: 127.0.0.1).
#     :arg --server-port (int): Port number to bind the server (default: 9000).
#     """

#     parser = argparse.ArgumentParser(
#         prog='Backend',
#         description='Start the backend process',
#         epilog='Backend daemon for http_deamon application'
#     )
#     parser.add_argument('--server-ip',
#         type=str,
#         default='0.0.0.0',
#         help='IP address to bind the server. Default is 0.0.0.0'
#     )
#     parser.add_argument(
#         '--server-port',
#         type=int,
#         default=PORT,
#         help='Port number to bind the server. Default is {}.'.format(PORT)
#     )
 
#     args = parser.parse_args()
#     ip = args.server_ip
#     port = args.server_port

#     create_backend(ip, port)

import socket
import argparse
import os
import urllib.parse

from daemon import create_backend

# Default port number used if none is specified via command-line arguments.
PORT = 9000 

def serve_static_file(filepath):
    """Serve static files from www/ directory"""
    try:
        # Construct full path relative to script location
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, 'www', filepath)
        
        print("[Backend] Attempting to serve file: {}".format(full_path))
        
        if not os.path.exists(full_path):
            print("[Backend] File not found: {}".format(full_path))
            return {'status': 404, 'body': '404 Not Found'}
        
        # Read file content
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Determine content type
        if filepath.endswith('.html'):
            content_type = 'text/html'
        elif filepath.endswith('.css'):
            content_type = 'text/css'
        elif filepath.endswith('.js'):
            content_type = 'application/javascript'
        else:
            content_type = 'text/plain'
        
        print("[Backend] Successfully served: {}".format(filepath))
        return {
            'status': 200,
            'headers': {'Content-Type': content_type},
            'body': content
        }
    
    except Exception as e:
        print("[Backend] Error serving file: {}".format(str(e)))
        return {'status': 500, 'body': 'Internal Server Error: {}'.format(str(e))}

def handle_login_get(headers, body):
    """Handle GET request to /login - serve login page"""
    print("[Backend] Serving login page")
    return serve_static_file('login.html')

def handle_login_post(headers, body):
    """Handle POST request to /login - process login"""
    print("[Backend] Login POST handler called")
    print("[Backend] Body: {}".format(body))
    
    credentials = {}
    if body:
        for param in body.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                credentials[urllib.parse.unquote(key)] = urllib.parse.unquote(value)
    
    username = credentials.get('username', '')
    password = credentials.get('password', '')
    
    print("[Backend] Login attempt - username: {}, password: {}".format(username, password))
    
    if username == 'admin' and password == 'password':
        print("[Backend] Login successful - setting auth cookie")
        # Return redirect with Set-Cookie header
        return {
            'status': 302,  # Redirect
            'headers': {
                'Location': '/index.html',
                'Set-Cookie': 'auth=true; Path=/; HttpOnly'
            },
            'body': 'Redirecting...'
        }
    else:
        print("[Backend] Login failed")
        return {
            'status': 401,
            'body': 'Invalid username or password'
        }

def handle_index(headers, body):
    """Handle GET request to / or /index.html - check authentication"""
    print("[Backend] Index handler called")
    print("[Backend] Headers: {}".format(headers))
    
    # Extract cookies from headers
    cookies = {}
    cookie_header = headers.get('cookie', '') if headers else ''
    
    print("[Backend] Cookie header: {}".format(cookie_header))
    
    if cookie_header:
        for pair in cookie_header.split(';'):
            pair = pair.strip()
            if '=' in pair:
                key, value = pair.split('=', 1)
                cookies[key.strip()] = value.strip()
    
    print("[Backend] Parsed cookies: {}".format(cookies))
    
    # Check authentication
    if cookies.get('auth') == 'true':
        print("[Backend] Authenticated user - serving index.html")
        return serve_static_file('index.html')
    else:
        print("[Backend] Unauthenticated user - access denied")
        return {
            'status': 401,
            'body': '<!DOCTYPE html><html><head><title>401 Unauthorized</title></head><body><h1>401 Unauthorized</h1><p>Access denied. Please <a href="/login">login</a> first.</p></body></html>'
        }

# Define routes
routes = {
    '/': {
        'GET': handle_index
    },
    '/index.html': {
        'GET': handle_index
    },
    '/login': {
        'GET': handle_login_get,
        'POST': handle_login_post
    }
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Backend',
        description='Start the backend process',
        epilog='Backend daemon for http_deamon application'
    )
    parser.add_argument('--server-ip',
        type=str,
        default='0.0.0.0',
        help='IP address to bind the server. Default is 0.0.0.0'
    )
    parser.add_argument(
        '--server-port',
        type=int,
        default=PORT,
        help='Port number to bind the server. Default is {}.'.format(PORT)
    )
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    print("[Backend] Routes configured: {}".format(list(routes.keys())))
    try:
        create_backend(ip, port, routes=routes)
    except KeyboardInterrupt:
        print("\n[Backend] Shutdown requested (Ctrl+C). Goodbye!")