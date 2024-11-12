from netmiko import ConnectHandler
from getpass import getpass
import time

# Nhập thông tin từ người dùng
ip = input("Nhập IP của switch: ")
username = input("Nhập username: ")
password = getpass("Nhập password: ")

# Tạo một dictionary chứa thông tin thiết bị
cisco_device = {
    'device_type': 'cisco_ios',
    'ip':   ip,
    'username': username,
    'password': password,
}

# Kết nối đến switch
connection = ConnectHandler(**cisco_device)

# Danh sách các cổng
ports = ['gi1/0/{}'.format(i) for i in range(1, 25)]  # Thay đổi số lượng cổng tùy theo switch của bạn

# Gửi lệnh đến từng cổng
for port in ports:
    print(f"Đang gửi lệnh đến cổng {port}")
    command = input("Nhập lệnh bạn muốn gửi: ")
    connection.config_mode()  # Chuyển sang chế độ config terminal
    output = connection.send_command_timing(f"interface {port}\n{command}\nexit")  # Gửi lệnh người dùng nhập vào
    print(output)
    time.sleep(10)  # Dừng 10 giây trước khi gửi lệnh đến cổng tiếp theo

# Đóng kết nối
connection.disconnect()
