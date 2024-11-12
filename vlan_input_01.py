from netmiko import ConnectHandler
import getpass

ip_switch = input("Nhập IP switch: ")
username = input("Nhập  username: ")
password = getpass.getpass('Nháº­p password: ')
vlan = input("Nhập  VLAN: ")
port = input("Nhập  port (vd: GigabitEthernet0/1): ")

device = {
    "device_type": "cisco_ios",
    "ip": ip_switch,
    "username": username,
    "password": password
}

with ConnectHandler(**device) as net_connect:
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
    output += net_connect.send_command("write memory")
    print(output)

print("Write with anhln1.")
time.sleep(60.5)