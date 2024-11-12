from netmiko import ConnectHandler
import getpass


ip_switch = input("Nhập IP switch: ")
username = input("Nhập username: ")
password = getpass.getpass('Nhập password: ')
vlan = input("Nhập VLAN: ")
port = input("Nhập port (vd: GigabitEthernet0/1): ")


device = {
    "device_type": "cisco_ios",
    "ip": ip_switch,
    "username": username,
    "password": password
}


with ConnectHandler(**device) as net_connect:
    print(f"Chuyển port {port} sang VLAN {vlan}...")
    
    commands = [
        f"interface {port}",
        f"switchport mode access",
        f"switchport access vlan {vlan}"
    ]
    
    output = net_connect.send_config_set(commands)
    print(output)

print("done.")