from netmiko import ConnectHandler
from getpass import getpass

# Yêu cầu người dùng nhập thông tin
username = input("Enter your SSH username: ")
password = getpass("Enter your SSH password: ")

# Danh sách IP của các switch
switch_ips = [
    input("Enter the IP address of the first Cisco switch: "),
    input("Enter the IP address of the second Cisco switch: ")
]

# Lệnh cần thực thi
command = "sh interface status"

for ip in switch_ips:
    # Định nghĩa thông tin kết nối cho mỗi switch
    cisco_switch = {
        'device_type': 'cisco_ios',
        'ip': ip,
        'username': username,
        'password': password,
    }

    # Kết nối đến switch
    print(f"Connecting to {ip}")
    net_connect = ConnectHandler(**cisco_switch)

    # Đăng nhập vào chế độ config terminal
    net_connect.enable()
    net_connect.config_mode()

    # Gửi lệnh shut (hoặc bất kỳ lệnh config nào khác bạn muốn)
    output = net_connect.send_command(command)
    print(output)

    # Thoát khỏi chế độ config
    net_connect.exit_config_mode()

    # Đóng kết nối
    net_connect.disconnect()

print("Commands have been sent to all switches.")