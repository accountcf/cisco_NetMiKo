from netmiko import ConnectHandler
from getpass import getpass
import time

ip = input("Nhập IP của switch: ")
username = input("Nhập username: ")
password = getpass("Nhập password: ")

cisco_device = {
    'device_type': 'cisco_ios',
    'ip': ip,
    'username': username,
    'password': password,
}

# Kết nối tới switch
connection = ConnectHandler(**cisco_device)

# Lệnh cần gửi
command = "no switchport port-security mac-address sticky 00a8.59fa.90fd"

# Gửi lệnh tới từng cổng
for i in range(1, 49):
    config_commands = [
        f'interface GigabitEthernet0/{i}',
        command,
        'exit'
    ]
    output = connection.send_config_set(config_commands)
    print(output)  # In kết quả ra màn hình hoặc ghi vào file log
    time.sleep(10)  # Đợi 10 giây trước khi gửi lệnh cho cổng tiếp theo

# Đóng kết nối
connection.disconnect()