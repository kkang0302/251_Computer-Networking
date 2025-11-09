#
# Copyright (C) 2025 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course,
# and is released under the "MIT License Agreement". Please see the LICENSE
# file that should have been included as part of this package.
#
# WeApRous release
#
# The authors hereby grant to Licensee personal permission to use
# and modify the Licensed Source Code for the sole purpose of studying
# while attending the course
#


"""
start_sampleapp
~~~~~~~~~~~~~~~~~

This module provides a sample RESTful web application using the WeApRous framework.

It defines basic route handlers and launches a TCP-based backend server to serve
HTTP requests. The application includes a login endpoint and a greeting endpoint,
and can be configured via command-line arguments.
"""

import json
import socket
import argparse

import threading

from daemon.weaprous import WeApRous

PORT = 8000  # Default port

db_lock = threading.Lock()

# List to save login info
USERS = {}


# List to save online peers
ONLINE_PEERS = {}


# List to save chat channel
CHANNELS = {
    'general': set()
}

app = WeApRous()

# @app.route('/login', methods=['POST'])
# def login(headers="guest", body="anonymous"):
#     """
#     Handle user login via POST request.

#     This route simulates a login process and prints the provided headers and body
#     to the console.

#     :param headers (str): The request headers or user identifier.
#     :param body (str): The request body or login payload.
#     """
#     print ("[SampleApp] Logging in {} to {}".format(headers, body))

# @app.route('/hello', methods=['PUT'])
# def hello(headers, body):
#     """
#     Handle greeting via PUT request.

#     This route prints a greeting message to the console using the provided headers
#     and body.

#     :param headers (str): The request headers or user identifier.
#     :param body (str): The request body or message payload.
#     """
#     print ("[SampleApp] ['PUT'] Hello in {} to {}".format(headers, body))



### API 1: /register/
@app.route('/register', methods=['POST'])
def register_peers(headers, body):
    try: 
        # parse body to take info
        data = json.loads(body)
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return {'status': 400, 'message': 'Username and password are required'}
        
        # use db_lock
        with db_lock:
            # Check user existence
            if username in USERS:
                print(f"[Tracker] Register failed: User '{username}' already exists.")
                return {'status': 400, 'message': 'Username already exists'}
            

            # If not exists, add new user
            USERS[username] = password
            print(f"[Tracker] New user registered: '{username}'")
            return {'status': 200, 'message': 'User registered successfully'} # 201 = Created

    except Exception as e:
        return {'status': 400, 'message': str(e)}





### API 2: /login/
@app.route('/login', methods=['POST'])
def login(headers, body):
    try:
        data = json.loads(body)
        username = data.get('username')
        password = data.get('password')

        with db_lock:
            if username in USERS and USERS[username] == password:
                print(f"[Tracker] User '{username}' logged in.")
                return {'status': 200, 'message': 'Login successful'}
            
            else: 
                return {'status': 401, 'message': 'Invalid credentials'}
            
    except Exception as e:
        return {'status': 400, 'message': str(e)}
    




### API 3: /submit-info/
@app.route('/submit-info', methods=['POST'])
def submit_info(headers, body):
    try: 
        data = json.loads(body)
        username = data.get('username') 
        ip = data.get('ip')
        port = data.get('port')

        if not username or not ip or not port:
            return {'status': 400, 'message': 'Missing data'}
        
        with db_lock:
            ONLINE_PEERS[username] = {'ip': ip, 'port': port}
            CHANNELS.get('general', set()).add(username)

        print(f"[Tracker] Updated info for '{username}': {ip}:{port}")
        return {'status': 200, 'message': 'Info submitted'}
    
    except Exception as e:
        return {'status': 400, 'message': str(e)}





### API 4: /get-list/
@app.route('/get-list', methods=['GET'])
def get_list(headers, body):
    # API returns peer lists or channel lists
    with db_lock:
        # return peer list in channer 'general'
        general_users = CHANNELS.get('general', set())
        peer_list = {user: ONLINE_PEERS[user] for user in general_users if user in ONLINE_PEERS}
        
    print(f"[Tracker] Returning peer list for 'general': {len(peer_list)} peers.")
    return {'status': 200, 'channel': 'general', 'peers': peer_list}





### API 5: /get-channels/
@app.route('/get-channels', methods=['GET'])
def get_channels(headers, body):
    """
    Trả về một danh sách tất cả các kênh 
    và những user ĐANG ONLINE trong mỗi kênh.
    """
    try:
        with db_lock:
            # Tạo một dictionary mới để lưu kết quả
            all_channel_data = {}
            
            # Lặp qua từng kênh có trong CSDL (CHANNELS)
            for channel_name, users_in_channel_set in CHANNELS.items():
                
                # Lọc ra những user nào trong kênh này 
                # mà CŨNG đang có trong ONLINE_PEERS
                online_users_in_channel = []
                for username in users_in_channel_set:
                    if username in ONLINE_PEERS:
                        online_users_in_channel.append(username)
                
                # Gán danh sách user online vào kênh tương ứng
                all_channel_data[channel_name] = online_users_in_channel
        
        print(f"[Tracker] Returning full channel list.")
        return {'status': 200, 'channels': all_channel_data}
        
    except Exception as e:
        print(f"[Tracker] Error getting channel list: {e}")
        return {'status': 500, 'message': str(e)}




### API 6: /join-channel/
@app.route('/join-channel', methods=['POST'])
# API creates a new channel if not exists. 
# Users are always automatically added into channel 'general'.
def join_channel(headers, body):
    try:
        data = json.loads(body)
        username = data.get('username')
        channel = data.get('channel')

        with db_lock:
            if channel not in CHANNELS:
                CHANNELS[channel] = set() # Create new channel if not exists
            CHANNELS[channel].add(username)
            
        print(f"[Tracker] User '{username}' joined channel '{channel}'.")
        return {'status': 200, 'message': f"Joined {channel}"}
    except Exception as e:
        return {'status': 400, 'message': str(e)}
    




### API 7: /get_channel_peers/ (Get peer list in a channel)
@app.route('/get-channel-peers', methods=['POST'])
def get_channel_peers(headers, body):
    """
    Trả về danh sách các peer đang online trong một kênh cụ thể.
    """
    try:
        data = json.loads(body)
        channel_name = data.get('channel')
        username = data.get('username')
        
        if not channel_name or not username:
            return {'status': 400, 'message': 'Channel name required'}

        with db_lock:
            if channel_name not in CHANNELS:
                return {'status': 404, 'message': 'Channel not found'}
            
            # Lấy set các user trong kênh
            users_in_channel = CHANNELS.get(channel_name, set())

            # Kiểm tra xem người đang hỏi (username) có trong kênh không
            if username not in users_in_channel:
                print(f"[Tracker] Access denied: '{username}' tried to access channel '{channel_name}' without joining.")
                return {'status': 403, 'message': 'Forbidden. You are not a member of this channel.'}
            
            # Lọc ra những user nào trong số đó đang ONLINE
            peer_list = {
                user: ONLINE_PEERS[user] 
                for user in users_in_channel 
                if user in ONLINE_PEERS
            }
        
        print(f"[Tracker] Returning peer list for channel '{channel_name}': {len(peer_list)} peers.")
        return {'status': 200, 'channel': channel_name, 'peers': peer_list}
        
    except Exception as e:
        print(f"[Tracker] Error getting channel peers: {e}")
        return {'status': 500, 'message': str(e)}
    




### API 8: /leave-channel/
@app.route('/leave-channel', methods=['POST'])
def leave_channel(headers, body):
    """Xóa peer khỏi một kênh cụ thể"""
    try:
        data = json.loads(body)
        username = data.get('username')
        channel = data.get('channel')

        if not username or not channel:
            return {'status': 400, 'message': 'Username and channel are required'}
        
        with db_lock:
            # Kiểm tra xem kênh có tồn tại và user có trong đó không
            if channel in CHANNELS and username in CHANNELS[channel]:
                CHANNELS[channel].remove(username)
                print(f"[Tracker] User '{username}' left channel '{channel}'.")
                
                # Delete channel if empty
                if not CHANNELS[channel]:
                    del CHANNELS[channel]
                
                return {'status': 200, 'message': f"Successfully left {channel}"}
            
            else:
                return {'status': 404, 'message': 'Channel or user not found in that channel'}
    
    except Exception as e:
        return {'status': 400, 'message': str(e)}





### API 9: /logout/
@app.route('/logout', methods=['POST'])
def logout(headers, body):
    """Xóa peer khỏi danh sách online khi logout"""
    try:
        data = json.loads(body)
        username = data.get('username')

        if not username:
            return {'status': 400, 'message': 'Username is required'}
        
        with db_lock:
            # Xóa khỏi danh sách online peers
            if username in ONLINE_PEERS:
                del ONLINE_PEERS[username]
                print(f"[Tracker] User '{username}' removed from online peers.")
            
            # Xóa khỏi tất cả channels
            for channel_name, users in CHANNELS.items():
                if username in users:
                    users.remove(username)
                    print(f"[Tracker] User '{username}' removed from channel '{channel_name}'.")
            
        print(f"[Tracker] User '{username}' logged out.")
        return {'status': 200, 'message': 'Logout successful'}
    
    except Exception as e:
        return {'status': 400, 'message': str(e)}





if __name__ == "__main__":
    # Parse command-line arguments to configure server IP and port
    parser = argparse.ArgumentParser(prog='Backend', description='', epilog='Beckend daemon')
    parser.add_argument('--server-ip', default='0.0.0.0')
    parser.add_argument('--server-port', type=int, default=PORT)
 
    args = parser.parse_args()
    ip = args.server_ip
    port = args.server_port

    # Prepare and launch the RESTful application

    print(f"[Tracker Server] Starting on {ip}:{port}...")
    app.prepare_address(ip, port)
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n[SampleApp] Shutdown requested (Ctrl+C). Exiting...")

        