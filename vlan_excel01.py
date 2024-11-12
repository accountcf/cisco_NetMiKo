from netmiko import ConnectHandler
import getpass
import pandas as pd
import time

# Read Excel file
excel_file = input("Nhập tên file Excel (vd: config.xlsx): ")
df = pd.read_excel(excel_file)

ip_switch = input("Nhập IP switch: ")
username = input("Nhập username: ")
password = getpass.getpass('Nhập password: ')

device = {
    "device_type": "cisco_ios",
    "ip": ip_switch,
    "username": username,
    "password": password
}

with ConnectHandler(**device) as net_connect:
    for index, row in df.iterrows():
        port = row['port']
        vlan = row['vlan']
        print(f"Chuyển port {port} sang VLAN {vlan} và save config...")
        config_commands = [
            f"interface {port}",
            f"switchport mode access",
            f"switchport access vlan {vlan}"
        ]
        
        output = net_connect.send_config_set(config_commands)
        print(output)
    
    # Exiting out of config mode
    net_connect.exit_config_mode()
    
    # Saving the configuration
    output = net_connect.send_command("write memory")
    print(output)

print("Write with anhln1.")
time.sleep(60.5)