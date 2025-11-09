import threading
import socket
import json
import time
import argparse
from daemon.weaprous import WeApRous 

# --- Cấu hình Client ---
TRACKER_API_URL = "http://127.0.0.1:8000" # Địa chỉ của Tracker Server
MY_USERNAME = ""
MY_IP = "127.0.0.1" # This computer
MY_PORT = 8000
MY_PEER_PORT = 0 # Cổng P2P mà client này sẽ lắng nghe



# # Parse Host và Port của Tracker
# try:
#     tracker_url_parts = urlparse(TRACKER_RAW_URL)
#     TRACKER_HOST = tracker_url_parts.hostname
#     TRACKER_PORT = tracker_url_parts.port
# except Exception as e:
#     print(f"Lỗi: URL của Tracker không hợp lệ: {TRACKER_RAW_URL}")
#     exit()

# --- Phần Server P2P của Client ---
peer_app = WeApRous()

# Danh sách các peer đã connect (handshake thành công)
# Lưu cả 2 chiều: khi mình connect đến họ, và khi họ connect đến mình
connected_peers = set()
connected_peers_lock = threading.Lock()  # Lock để thread-safe




### API 1: /connect-peer/ 
@peer_app.route('/connect-peer', methods=['POST'])
def connect_peer(headers, body):
    try:
        data = json.loads(body)
        username = data.get('username')

        # Lưu peer này vào danh sách đã connect
        with connected_peers_lock:
            connected_peers.add(username)
        
        print(f"\n[P2P] Peer '{username}' connected (handshake).")
        return {'status': 200, 'message': 'ACK'}
    
    except Exception as e:
        return {'status': 400, 'message': str(e)}
    




### API 2: /disconnect-peer/
@peer_app.route('/disconnect-peer', methods=['POST'])
def disconnect_peer(headers, body):
    try:
        data = json.loads(body)
        username = data.get('username')

        # Xóa peer này khỏi danh sách connected
        with connected_peers_lock:
            if username in connected_peers:
                connected_peers.remove(username)
        
        print(f"\n[P2P] Peer '{username}' has disconnected.")
        return {'status': 200, 'message': 'ACK'}
    
    except Exception as e:
        return {'status': 400, 'message': str(e)}


    




### API 3: /send-peer/ (Nhận tin nhắn 1-1) 
@peer_app.route('/send-peer', methods=['POST'])
def send_message(headers, body):
    try:
        data = json.loads(body)
        from_user = data.get('from_user')
        message = data.get('message')

        print(f"\n[Direct message from {from_user}]: {message}")
        return {'status': 200, 'message': 'Received'}
    
    except Exception as e:
        return {'status': 400, 'message': str(e)}





### API 4: /broadcast-peer/ (Nhận tin nhắn broadcast) 
@peer_app.route('/broadcast-peer', methods=['POST'])
def broadcast_message(headers, body):
    try:
        data = json.loads(body)
        from_user = data.get('from_user')
        message = data.get('message')

        # Ignore if it is self message
        if from_user == MY_USERNAME:
            return {'status': 200, 'message': 'Self-broadcast ignored'}
            
        print(f"\n[Broadcast message from {from_user}]: {message}")
        return {'status': 200, 'message': 'Received'}
    
    except Exception as e:
        return {'status': 400, 'message': str(e)}
    



### API 5: /send-message-in-channel/
@peer_app.route('/send-channel-message', methods=['POST'])
def send_channel_message(headers, body):
    try:
        data = json.loads(body)
        from_user = data.get('from_user')
        channel_name = data.get('channel')
        message = data.get('message')

        # Bỏ qua nếu là tin nhắn của chính mình
        if from_user == MY_USERNAME:
            return {'status': 200, 'message': 'Self-message ignored'}
            
        print(f"\n[Channel: {channel_name} | {from_user}]: {message}")
        return {'status': 200, 'message': 'Received'}
    
    except Exception as e:
        return {'status': 400, 'message': str(e)}





# Hàm chạy P2P server trên luồng riêng
def start_p2p_server():
    print(f"[P2P Server] Starting listening P2P on {MY_IP}:{MY_PEER_PORT}...")
    peer_app.prepare_address(MY_IP, MY_PEER_PORT)
    peer_app.run()





# Hàm gọi API 
def call_API(host, port, method, path, dict=None):
    # 1. Chuẩn bị body (nếu có)
    body_str = ""
    if dict:
        body_str = json.dumps(dict)
    

    # 2. Tự tay xây dựng chuỗi HTTP Request thô
    request_lines = [
        f"{method} {path} HTTP/1.1",
        f"Host: {host}:{port}",
        "Connection: close"
    ]
    
    # Chỉ thêm Content-Type và Content-Length khi có body
    if body_str:
        request_lines.append(f"Content-Type: application/json")
        request_lines.append(f"Content-Length: {len(body_str.encode('utf-8'))}")
    
    request_lines.append("\r\n")  # Dòng trống bắt buộc
    request_str = "\r\n".join(request_lines) + body_str


    # 3. Gửi request bằng socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((host, port))
            s.sendall(request_str.encode('utf-8'))
            response_raw = b""

            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response_raw += chunk
            s.close()

        except socket.error as e:
            print(f"Socket error: {e}")
            s.close()
            return None
        
        # 4. Parse response
        if not response_raw:
            return None
        
        try:
            response_str = response_raw.decode('utf-8')
        except UnicodeDecodeError as e:
            print(f"Decode error: {e}")
            return None
        
        # 5. Tách phần body của response ra
        parts = response_str.split("\r\n\r\n", 1) # Tách header và body
        
        if len(parts) == 2:
            body = parts[1].strip()
            if not body:
                # Response không có body
                return None
            try:
                return json.loads(body) # Trả về dictionary
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Response body: {body[:200]}")  # In 200 ký tự đầu để debug
                return None
        else:
            # Response không có body
            return None

    except Exception as e:
        print(f"API called error: {e}")
        return None





# --- Phần Client (Gọi API) ---

def register_to_tracker(username, password):
    """Đăng ký tài khoản mới trên tracker server"""
    payload = {'username': username, 'password': password}
    
    response_body = call_API(
        MY_IP,
        MY_PORT,
        'POST',
        '/register',
        payload
    )
    
    if response_body and response_body.get('status') == 200:
        print("[Tracker] Registration successful.")
        return True
    else:
        error_msg = response_body.get('message', 'Unknown error') if response_body else 'Connection failed'
        print(f"[Tracker] Registration failed: {error_msg}")
        return False


def login_to_tracker(username, password):
    payload = {'username': username, 'password': password}

    response_body = call_API(
        MY_IP, 
        MY_PORT, 
        'POST', 
        '/login', 
        payload
    )

    if response_body and response_body.get('status') == 200:
        print("[Tracker] Login successful.")
        return True
    
    else:
        error_msg = response_body.get('message', 'Connection failed') if response_body else 'Cannot connect to tracker server. Make sure tracker server is running.'
        print(f"[Tracker] Login failed: {error_msg}")
        return False





def submit_info_to_tracker():
    payload = {'username': MY_USERNAME, 'ip': MY_IP, 'port': MY_PEER_PORT}

    submit = call_API(
        MY_IP,
        MY_PORT,
        'POST',
        '/submit-info',
        payload
    )

    if submit and submit.get('status') == 200:
        print("[Tracker] Send info to tracker successfully.")
        return True
    
    else:
        print(f"[Tracker] Send info failed: {submit}")
        return False


def logout_from_tracker():
    """Thông báo logout đến tracker server"""
    # Xóa tất cả connected peers
    with connected_peers_lock:
        connected_peers.clear()
    
    payload = {'username': MY_USERNAME}
    
    response_body = call_API(
        MY_IP,
        MY_PORT,
        'POST',
        '/logout',
        payload
    )
    
    if response_body and response_body.get('status') == 200:
        print("[Tracker] Logged out successfully.")
        return True
    else:
        # Không báo lỗi nếu không kết nối được, vì có thể tracker đã tắt
        return False





def get_peer_list():
    get_body = call_API(
        MY_IP,
        MY_PORT,
        'GET',
        '/get-list',
        dict=None
    )

    if get_body and get_body.get('status') == 200:
        return get_body.get('peers', {})
    
    else:
        print(f"[Tracker] Failed to get peer list: {get_body}")
        return {}
    




def get_channel_list():
    get_body = call_API(
        MY_IP, 
        MY_PORT,
        'GET',
        '/get-channels',
        dict=None
    )

    if get_body and get_body.get('status') == 200:
        return get_body.get('channels', {})
    
    else:
        print(f"[Tracker] Failed to get channel list: {get_body}")
        return {}
    





def join_channel(channel_name):
    payload = {'username': MY_USERNAME, 'channel': channel_name}

    body = call_API(
        MY_IP,
        MY_PORT,
        'POST',
        '/join-channel',
        dict=payload
    )

    if body and body.get('status') == 200:
        print("[Tracker] Join channel successfully.")
        return True
    
    else:
        print(f"[Tracker] Failed to join channel")
        return False





def leave_channel(channel_name):
    """Gọi API tracker để rời khỏi một kênh"""
    payload = {'username': MY_USERNAME, 'channel': channel_name}

    body = call_API(
        MY_IP,
        MY_PORT,
        'POST',
        '/leave-channel',
        dict=payload
    )

    if body and body.get('status') == 200:
        return True
    
    else:
        error_msg = body.get('message', 'Failed') if body else 'Failed'
        print(f"[Tracker] Failed to leave channel: {error_msg}")
        return False




def connect_to_peer(target_username):
    """Gửi handshake đến peer trước khi chat"""
    peer_list = get_peer_list()
    
    if target_username not in peer_list:
        print(f"[P2P Client] Peer '{target_username}' not found in peer list.")
        return False
    
    if target_username == MY_USERNAME:
        print(f"[P2P Client] Cannot connect to yourself.")
        return False
    
    # Kiểm tra xem đã connect chưa
    with connected_peers_lock:
        if target_username in connected_peers:
            print(f"[P2P Client] Already connected to '{target_username}'.")
            return True
    
    info = peer_list[target_username]
    payload = {'username': MY_USERNAME}
    
    try:
        response = call_API(
            info['ip'],
            info['port'],
            'POST',
            '/connect-peer',
            payload
        )
        if response and response.get('status') == 200:
            # Lưu vào danh sách đã connect
            with connected_peers_lock:
                connected_peers.add(target_username)
            return True
        else:
            return False
    except Exception as e:
        print(f"[P2P Client] Failed to connect to {target_username}: {e}")
        return False
    




def disconnect_from_peer(target_username):
    """Thông báo cho peer khác và xóa khỏi danh sách connected"""
    with connected_peers_lock:
        if target_username not in connected_peers:
            print(f"[P2P Client] Not currently connected to '{target_username}'.")
            return False
            
    peer_list = get_peer_list()

    if target_username not in peer_list:
        # Peer đã offline, chỉ cần xóa cục bộ
        with connected_peers_lock:
            connected_peers.remove(target_username)
        print(f"[P2P Client] Peer '{target_username}' is offline. Removed locally.")
        return True

    info = peer_list[target_username]
    payload = {'username': MY_USERNAME}
    
    try:
        # Gửi API /disconnect-peer đến họ
        call_API(
            info['ip'],
            int(info['port']), # Đảm bảo port là int
            'POST',
            '/disconnect-peer',
            payload
        )

    except Exception as e:
        print(f"[P2P Client] Error sending disconnect notice: {e}")

    
    # Xóa khỏi danh sách cục bộ
    with connected_peers_lock:
        connected_peers.remove(target_username)
    
    print(f"[P2P Client] Disconnected from '{target_username}'.")
    return True
    







def send_direct_message(target_username, message):
    """Gửi tin nhắn 1-1 đến một peer cụ thể (yêu cầu đã connect trước)"""
    peer_list = get_peer_list()
    
    if target_username not in peer_list:
        print(f"[P2P Client] Peer '{target_username}' not found in peer list.")
        return False
    
    if target_username == MY_USERNAME:
        print(f"[P2P Client] Cannot send message to yourself.")
        return False
    
    # Kiểm tra xem đã connect chưa
    with connected_peers_lock:
        if target_username not in connected_peers:
            print(f"[P2P Client] ❌ Chưa connect đến '{target_username}'.")
            print(f"[P2P Client] Vui lòng dùng lệnh: /connect {target_username}")
            return False
    
    info = peer_list[target_username]
    payload = {
        'from_user': MY_USERNAME,
        'message': message
    }
    
    try:
        response = call_API(
            info['ip'],
            info['port'],
            'POST',
            '/send-peer',
            payload
        )
        if response and response.get('status') == 200:
            print(f"[P2P Client] Message sent to {target_username}.")
            return True
        else:
            print(f"[P2P Client] Failed to send message: {response}")
            return False
    except Exception as e:
        print(f"[P2P Client] Error sending message to {target_username}: {e}")
        return False


def send_broadcast_message(message):
    """Gửi tin nhắn broadcast đến tất cả peers"""
    print("[P2P Client] Sending broadcast...")
    peer_list = get_peer_list()
    
    payload = {
        'from_user': MY_USERNAME,
        'message': message
    }
    
    success_count = 0
    for username, info in peer_list.items():
        if username == MY_USERNAME: # Pass self message
            continue
            
        try:
            response = call_API(
                info['ip'],
                info['port'],
                'POST',
                '/broadcast-peer',
                payload
            )
            if response and response.get('status') == 200:
                success_count += 1
        except Exception as e:
            pass
    
    print(f"[P2P Client] Broadcast sent to {success_count} peer(s).")




def get_peers_in_channel(channel_name):
    payload = {'username': MY_USERNAME, 'channel': channel_name}

    get_body = call_API(
        MY_IP, 
        MY_PORT, 
        'POST', 
        '/get-channel-peers', 
        payload
    )
    
    if get_body and get_body.get('status') == 200:
        return get_body.get('peers', {})
    
    else:
        print(f"[Tracker] Failed to get peer list for channel '{channel_name}': {get_body}")
        return None # Trả về None nếu có lỗi





def send_message_in_channel(channel_name, message):
    print(f"[P2P Client] Sending message to channel '{channel_name}'...")

    peer_list = get_peers_in_channel(channel_name)
    
    if peer_list is None:
        print(f"[P2P Client] 🔕 Cannot send: Channel '{channel_name}' not found or error.")
        return

    if not peer_list:
        print(f"[P2P Client] 🔕 Channel '{channel_name}' is empty.")
        return

    payload = {
        'from_user': MY_USERNAME,
        'channel': channel_name,
        'message': message
    }
    
    success_count = 0
    for username, info in peer_list.items():
        if username == MY_USERNAME: # Bỏ qua chính mình
            continue
            
        try:
            # Gọi API P2P mới
            response = call_API(
                info['ip'],
                info['port'],
                'POST',
                '/send-channel-message', # API P2P mới
                payload
            )

            if response and response.get('status') == 200:
                success_count += 1

        except Exception as e:
            print(f"[P2P Client] ❌ Failed to send to {username}: {e}")
            # pass # Bỏ qua nếu peer bị offline
    
    print(f"[P2P Client] Channel message sent to {success_count} peer(s).")




# --- Vòng lặp UI chính ---
def start_ui():
    print(f"\n{'='*50}")
    print(f"--- Welcome, {MY_USERNAME}! ---")
    print(f"{'='*50}")
    print("\nCommands:")
    print("  - Type message and Enter to send broadcast")
    print("  - /list_peers                   - Show online peers")
    print("  - /list_channels                - Show channels and online peers in channel")
    print("  - /connect <username>       - Connect to peer (handshake)")
    print("  - /disconnect <username>       - Disconnect from peer")
    print("  - /msg <username> <message> - Send direct message")
    print("  - /join <channel_name>       - Join a new channel")
    print("  - /local <channel> <message>   - Send message to a channel")
    print("  - /leave <channel_name>       - Leave a channel")
    print("  - /quit                    - Exit")
    print(f"{'='*50}\n")
    
    while True:
        try:
            user_input = input(f"{MY_USERNAME}> ").strip()
            
            if not user_input:
                continue
            
            # Xử lý lệnh quit
            if user_input.lower() == 'quit' or user_input.lower() == '/quit':
                logout_from_tracker()
                break
            
            # Xử lý lệnh list
            elif user_input.lower() == '/list_peers':
                peer_list = get_peer_list()
                if peer_list:
                    print(f"\n[Online Peers] ({len(peer_list)} peer(s)):")
                    with connected_peers_lock:
                        for username, info in peer_list.items():
                            if username == MY_USERNAME:
                                # Bản thân không cần hiển thị trạng thái connected
                                print(f"  - {username}: {info['ip']}:{info['port']} (you)")
                            else:
                                # Chỉ hiển thị trạng thái cho peer khác
                                connected_marker = " [connected]" if username in connected_peers else " [not connected]"
                                print(f"  - {username}: {info['ip']}:{info['port']}{connected_marker}")
                else:
                    print("[Online Peers] No peers online.")
                print()


            # List channels
            elif user_input.lower() == '/list_channels':
                channel_list = get_channel_list()
                if channel_list:
                    print(f"\n[All channels] ({len(channel_list)} channel(s)):")
                    with connected_peers_lock:
                        for channel_name, users in channel_list.items():
                            print(f"  > {channel_name}:")
                            if users:
                                # Lặp qua các user trong kênh đó
                                for user in users:
                                    print(f"    - {user}")
                            else:
                                print("    (empty)")
                else:
                    print("[All Channels] No channels found or error.")
                print()


            
            # Xử lý lệnh connect
            elif user_input.lower().startswith('/connect '):
                parts = user_input.split(' ', 1)
                if len(parts) == 2:
                    target_username = parts[1].strip()
                    if connect_to_peer(target_username):
                        print(f"[P2P Client] Successfully connected to {target_username}.\n")
                    else:
                        print(f"[P2P Client] Failed to connect to {target_username}.\n")
                else:
                    print("[P2P Client] Usage: /connect <username>\n")


            # Disconnect
            elif user_input.lower().startswith('/disconnect '):
                parts = user_input.split(' ', 1)
                if len(parts) == 2:
                    target_username = parts[1].strip()
                    disconnect_from_peer(target_username)
                    print() # Thêm dòng mới
                else:
                    print("[P2P Client] Usage: /disconnect <username>\n")


            # Xử lý lệnh msg (direct message)
            elif user_input.lower().startswith('/msg '):
                parts = user_input.split(' ', 2)
                if len(parts) >= 3:
                    target_username = parts[1].strip()
                    message = parts[2].strip()
                    if message:
                        send_direct_message(target_username, message)
                    else:
                        print("[P2P Client] Message cannot be empty.\n")
                else:
                    print("[P2P Client] Usage: /msg <username> <message>\n")

            
            # join channel
            elif user_input.lower().startswith('/join '):
                parts = user_input.split(' ', 1)
                if len(parts) == 2:
                    channel = parts[1].strip()

                    if channel:
                        if join_channel(channel):
                            print(f"[P2P Client] Successfully join channel {channel}.\n")

                        else:
                            print(f"[P2P Client] Failed to join channel {channel}.\n")

                    else:
                        print("[P2P Client] Channel name cannot be empty.\n")
                else:
                    print("[P2P Client] Usage: /join <channel_name>\n")


            # leave channel
            elif user_input.lower().startswith('/leave '):
                parts = user_input.split(' ', 1)
                if len(parts) == 2:
                    channel = parts[1].strip()
                    if channel:
                        if leave_channel(channel):
                            print(f"[P2P Client] Successfully left channel {channel}.\n")
                        else:
                            print(f"[P2P Client] Failed to leave channel {channel}.\n")
                    else:
                        print("[P2P Client] Channel name cannot be empty.\n")
                else:
                    print("[P2P Client] Usage: /leave <channel_name>\n")



            # Send message in channel
            elif user_input.lower().startswith('/local '):
                parts = user_input.split(' ', 2)
                if len(parts) >= 3:
                    channel_name = parts[1].strip()
                    message = parts[2].strip()

                    if message:
                        send_message_in_channel (channel_name, message)

                    else:
                        print("[P2P Client] Message cannot be empty.\n")

                else:
                    print("[P2P Client] Usage: /local <channel_name> <message>\n")

            
            # Mặc định: gửi broadcast
            else:
                send_broadcast_message(user_input)
        
        except KeyboardInterrupt:
            print("\n\n[P2P Client] Interrupted by user.")
            logout_from_tracker()
            break
        except Exception as e:
            print(f"[P2P Client] Error: {e}\n")





# --- Hàm Main ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Peer-to-Peer Chat Client")
    parser.add_argument("username", help="Tên đăng nhập của bạn (vd: alice, bob)")
    parser.add_argument("password", help="Mật khẩu của bạn (vd: 123, 456)")
    parser.add_argument("port", type=int, help="Cổng P2P bạn muốn lắng nghe (vd: 9001, 9002)")
    args = parser.parse_args()

    MY_USERNAME = args.username
    MY_PEER_PORT = args.port

    # 1. Đăng nhập vào Tracker
    if not login_to_tracker(MY_USERNAME, args.password):
        exit()

    # 2. Khởi động P2P Server (trên luồng riêng)
    # daemon=True để luồng này tự tắt khi chương trình chính (UI) thoát
    server_thread = threading.Thread(target=start_p2p_server, daemon=True)
    server_thread.start()
    
    # Chờ server khởi động một chút
    time.sleep(3) 

    # 3. Gửi thông tin IP/Port của P2P server cho Tracker
    submit_info_to_tracker()

    # 4. Khởi động UI (trên luồng chính)
    try:
        start_ui()
    finally:
        # Đảm bảo logout khi thoát (dù bằng cách nào)
        logout_from_tracker()
    
    print("Exit!")