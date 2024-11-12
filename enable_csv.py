import csv
from netmiko import ConnectHandler
import getpass

def enable_port(net_connect, port):
    print(f"Enabling port {port}")
    commands = [f"interface {port}", "shutdown", "no shutdown"]
    net_connect.send_config_set(commands)

# Định nghĩa hàm để kết nối và thực hiện các lệnh trên một switch
def handle_switch(ip, username, password):
    device = {
        "device_type": "cisco_ios",
        "ip": ip,
        "username": username,
        "password": password
    }

    with ConnectHandler(**device) as net_connect:
        net_connect.send_command("clear port-security all")
        output = net_connect.send_command("show int status")
        
        for line in output.splitlines():
            if "disabled" in line:
                port = line.split()[0]
                enable_port(net_connect, port)

# Đọc csv và thực hiện các lệnh trên mỗi switch
username = input("Nhập username:")
password = getpass.getpass('Password:')
with open('switches.csv') as file:
    reader = csv.reader(file)
    for row in reader:
        ip = row[0]  # Giả định rằng IP là dữ liệu trong cột đầu tiên
        handle_switch(ip, username, password)
