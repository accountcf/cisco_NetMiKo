from netmiko import ConnectHandler
import getpass

ip_switch = input("Nháº­p IP switch: ")
username = input("Nháº­p username: ")
password = getpass.getpass('Nháº­p password: ')
vlan = input("Nháº­p VLAN: ")
port = input("Nháº­p port (vd: GigabitEthernet0/1): ")

device = {
    "device_type": "cisco_ios",
    "ip": ip_switch,
    "username": username,
    "password": password
}

with ConnectHandler(**device) as net_connect:
    print(f"Chuyá»ƒn port {port} sang VLAN {vlan} vÃ  lÆ°u cáº¥u hÃ¬nh...")

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