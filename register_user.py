#!/usr/bin/env python3
"""
Script đăng ký user mới vào tracker server
Usage: python register_user.py <username> <password> [tracker_ip] [tracker_port]
"""

import sys
import socket
import json

# Cấu hình mặc định
DEFAULT_TRACKER_IP = "127.0.0.1"
DEFAULT_TRACKER_PORT = 8000


def call_API(host, port, method, path, dict=None):
    """Gọi API đến tracker server"""
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
                return None
            try:
                return json.loads(body) # Trả về dictionary
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                print(f"Response body: {body[:200]}")  # In 200 ký tự đầu để debug
                return None
        else:
            return None

    except Exception as e:
        print(f"API called error: {e}")
        return None


def register_user(username, password, tracker_ip=DEFAULT_TRACKER_IP, tracker_port=DEFAULT_TRACKER_PORT):
    """Đăng ký user mới"""
    print(f"[Register] Đang đăng ký user '{username}'...")
    print(f"[Register] Kết nối đến tracker: {tracker_ip}:{tracker_port}")
    
    payload = {'username': username, 'password': password}
    
    response_body = call_API(
        tracker_ip,
        tracker_port,
        'POST',
        '/register',
        payload
    )
    
    if response_body:
        status = response_body.get('status')
        message = response_body.get('message', 'Unknown error')
        
        if status == 200:
            print(f"[Register] ✅ Đăng ký thành công!")
            print(f"[Register] Username: {username}")
            return True
        else:
            print(f"[Register] ❌ Đăng ký thất bại: {message}")
            return False
    else:
        print(f"[Register] ❌ Không thể kết nối đến tracker server.")
        print(f"[Register] Hãy đảm bảo tracker server đang chạy tại {tracker_ip}:{tracker_port}")
        return False


def is_valid_port(port_str):
    """Kiểm tra xem string có phải là port hợp lệ không"""
    try:
        port = int(port_str)
        return 1 <= port <= 65535
    except ValueError:
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python register_user.py <username> <password> [tracker_ip] [tracker_port]")
        print("\nVí dụ:")
        print("  python register_user.py alice 123")
        print("  python register_user.py bob 456 127.0.0.1 8000")
        print("\nLưu ý:")
        print("  - Tracker server mặc định: 127.0.0.1:8000")
        print("  - Nếu chỉ có 3 tham số và tham số thứ 3 là số, sẽ hiểu đó là port")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    if not username or not password:
        print("❌ Username và password không được để trống!")
        sys.exit(1)
    
    # Xử lý tham số tracker_ip và tracker_port
    tracker_ip = DEFAULT_TRACKER_IP
    tracker_port = DEFAULT_TRACKER_PORT
    
    if len(sys.argv) > 3:
        arg3 = sys.argv[3]
        # Nếu tham số thứ 3 là số, đó là port
        if is_valid_port(arg3):
            tracker_port = int(arg3)
            print(f"[Register] Nhận diện tham số thứ 3 là port: {tracker_port}")
            print(f"[Register] Sử dụng tracker IP mặc định: {tracker_ip}")
        else:
            # Nếu không phải số, đó là IP
            tracker_ip = arg3
            if len(sys.argv) > 4:
                # Có tham số thứ 4, đó là port
                if is_valid_port(sys.argv[4]):
                    tracker_port = int(sys.argv[4])
                else:
                    print(f"❌ Port không hợp lệ: {sys.argv[4]}")
                    print("Port phải là số từ 1 đến 65535")
                    sys.exit(1)
    
    success = register_user(username, password, tracker_ip, tracker_port)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

