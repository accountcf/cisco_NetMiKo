import telnetlib
import time
import getpass
import re
import sys

def get_mac_address(ip, user, password, target_ip):
    try:
        # Kết nối telnet đến switch
        tn = telnetlib.Telnet(ip, timeout=5)
        
        # Đăng nhập
        tn.read_until(b"Username: ")
        tn.write(user.encode('ascii') + b"\n")
        tn.read_until(b"Password: ")
        tn.write(password.encode('ascii') + b"\n")
        
        # Gửi lệnh và đọc kết quả
        tn.write(f"show ip arp | include {target_ip}\n".encode('ascii'))
        tn.write(b"exit\n")
        
        output = tn.read_all().decode('ascii')
        
        # Tìm địa chỉ MAC trong output
        mac_match = re.search(r'([0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4}\.[0-9A-Fa-f]{4})', output)
        if mac_match:
            return mac_match.group(1)
        else:
            return None
    except Exception as e:
        print(f"Lỗi: {str(e)}")
        return None

# Input từ người dùng
target_ip = input("Nhập IP máy tính cần tìm MAC: ")
user = input("Nhập tên đăng nhập switch: ")
password = getpass.getpass("Nhập mật khẩu switch: ")

# IP của switch
switch_ip = "10.38.1.1"

# Tìm địa chỉ MAC
mac_address = get_mac_address(switch_ip, user, password, target_ip)

if mac_address:
    print(f"Địa chỉ MAC tương ứng với IP {target_ip} là: {mac_address}")
else:
    print(f"Không tìm thấy địa chỉ MAC cho IP {target_ip}")

# Giữ màn hình trong 1 phút
print("Đang giữ màn hình trong 1 phút...")
time.sleep(60)