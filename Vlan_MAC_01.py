from netmiko import ConnectHandler
import re
import traceback

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
    print(f"MAC Address Table output: {output}")
    match = re.search(r'(Gi\d+/\d+/\d+|Fa\d+/\d+)', output)
    if match:
        return match.group(1)
    return None

def change_vlan(connection, port, vlan):
    config_commands = [
        'configure terminal',
        f'interface {port}',
        'switchport mode access',
        f'switchport access vlan {vlan}',
        'end'
    ]
    output = connection.send_config_set(config_commands)
    print(f"Configuration output: {output}")
    
    # Verify the change
    verify_output = connection.send_command(f"show interface {port} switchport | include Access Mode VLAN")
    print(f"Verification output: {verify_output}")
    if f"Access Mode VLAN: {vlan}" in verify_output:
        return True
    return False

def save_config(connection):
    output = connection.send_command("write memory")
    print(f"Save configuration output: {output}")
    return "OK" in output

def main():
    switch_ip, username, password, vlan, mac_address = get_input()
    
    try:
        connection = connect_to_switch(switch_ip, username, password)
        print("Đã kết nối thành công đến switch.")
        
        port = find_port(connection, mac_address)
        if port:
            print(f"Đã tìm thấy địa chỉ MAC trên cổng {port}")
            if change_vlan(connection, port, vlan):
                print(f"Đã chuyển cổng {port} sang VLAN {vlan}")
                if save_config(connection):
                    print("Đã lưu cấu hình thành công.")
                else:
                    print("Không thể lưu cấu hình. Vui lòng kiểm tra quyền hạn.")
            else:
                print(f"Không thể chuyển cổng {port} sang VLAN {vlan}. Vui lòng kiểm tra lại.")
        else:
            print("Không tìm thấy địa chỉ MAC trên switch.")
        
        connection.disconnect()
        print("Đã ngắt kết nối từ switch.")
    
    except Exception as e:
        print(f"Đã xảy ra lỗi: {str(e)}")
        print(f"Chi tiết lỗi:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()
print("Write with anhln1.")
time.sleep(120.5)