from netmiko import ConnectHandler
import getpass
import pandas as pd
import time

# Yêu cầu người dùng nhập tên file Excel
excel_file = input("Nhập đường dẫn file Excel (ví dụ: switch_config.xlsx): ")

# Đọc dữ liệu từ file Excel
try:
    df = pd.read_excel(excel_file)
except FileNotFoundError:
    print(f"Không tìm thấy file '{excel_file}'. Vui lòng kiểm tra lại tên file và đường dẫn.")
    exit()
except Exception as e:
    print(f"Có lỗi khi đọc file Excel: {e}")
    exit()

ip_switch = input("Nhập IP switch: ")
username = input("Nhập username: ")
password = getpass.getpass('Nhập password: ')

device = {
    "device_type": "cisco_ios",
    "ip": ip_switch,
    "username": username,
    "password": password
}

try:
    with ConnectHandler(**device) as net_connect:
        for index, row in df.iterrows():
            port = row['Port']
            vlan = row['VLAN']
            
            print(f"Chuyển port {port} sang VLAN {vlan} và save config...")
            config_commands = [
                f"interface {port}",
                f"switchport mode access",
                f"switchport access vlan {vlan}"
            ]
            
            output = net_connect.send_config_set(config_commands)
            print(output)
        
        # Thoát khỏi chế độ config
        net_connect.exit_config_mode()
        
        # Lưu cấu hình
        output = net_connect.send_command("write memory")
        print(output)

except Exception as e:
    print(f"Có lỗi khi kết nối hoặc cấu hình switch: {e}")

print("Write with anhln1.")
time.sleep(60.5)