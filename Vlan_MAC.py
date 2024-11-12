from netmiko import ConnectHandler
import re

def get_input():
    switch_ip = input("Nhập địa chỉ IP của switch: ")
    username = input("Nhập tên đăng nhập: ")
    password = input("Nhập mật khẩu: ")
    vlan = input("Nhập VLAN mới: ")
    mac_address = input("Nhập địa chỉ MAC (định dạng xxxx.xxxx.xxxx): ")
    return switch_ip, username, password, vlan, mac_address

def connect_to_switch(ip, username, password):
    device = {
        'device_type': 'cisco_ios',
        'ip': ip,
        'username': username,
        'password': password,
    }
    return ConnectHandler(**device)

def find_port(connection, mac_address):
    output = connection.send_command(f"show mac address-table | in {mac_address}")
    match = re.search(r'(Gi\d+/\d+/\d+)', output)
    if match:
        return match.group(1)
    return None

def change_vlan(connection, port, vlan):
    config_commands = [
        f'interface {port}',
        f'switchport access vlan {vlan}',
        'exit'
    ]
    connection.send_config_set(config_commands)

def save_config(connection):
    connection.send_command("write memory")

def main():
    switch_ip, username, password, vlan, mac_address = get_input()
    
    try:
        connection = connect_to_switch(switch_ip, username, password)
        print("Đã kết nối thành công đến switch.")
        
        port = find_port(connection, mac_address)
        if port:
            print(f"Đã tìm thấy địa chỉ MAC trên cổng {port}")
            change_vlan(connection, port, vlan)
            print(f"Đã chuyển cổng {port} sang VLAN {vlan}")
            save_config(connection)
            print("Đã lưu cấu hình.")
        else:
            print("Không tìm thấy địa chỉ MAC trên switch.")
        
        connection.disconnect()
        print("Đã ngắt kết nối từ switch.")
    
    except Exception as e:
        print(f"Đã xảy ra lỗi: {str(e)}")

if __name__ == "__main__":
    main()
print("Write with anhln1.")
time.sleep(120.5)