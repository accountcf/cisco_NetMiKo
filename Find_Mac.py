from __future__ import print_function
import sys
import openpyxl
import netmiko

# Kiểm tra phiên bản Python và import getpass phù hợp
if sys.version_info[0] >= 3:
    from getpass import getpass
    input_func = input
else:
    from getpass import getpass
    input_func = raw_input

def read_excel(file_path, sheet_name):
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook[sheet_name]
    return [row[0].value for row in sheet.iter_rows(min_row=2, max_col=1)]

def connect_to_switch(ip, username, password):
    return netmiko.ConnectHandler(
        device_type='cisco_ios',
        ip=ip,
        username=username,
        password=password
    )

def find_mac_on_switch(connection, mac_address):
    output = connection.send_command(f"show mac address-table | include {mac_address}")
    if output:
        port = output.split()[-1]
        if port.startswith('Gi') or port.startswith('Fa'):
            port_number = int(port.split('/')[-1])
            return port if port_number < 40 else None
    return None

def change_port_vlan(connection, port, vlan):
    config_commands = [
        f'interface {port}',
        f'switchport access vlan {vlan}',
        'switchport mode access'
    ]
    connection.send_config_set(config_commands)

def main():
    switch_file = input_func("Enter the path to the switch list Excel file: ")
    mac_file = input_func("Enter the path to the MAC address list Excel file: ")
    username = input_func("Enter your username: ")
    password = getpass("Enter your password: ")
    target_vlan = input_func("Enter the target VLAN: ")

    switches = read_excel(switch_file, 'Sheet1')
    mac_addresses = read_excel(mac_file, 'Sheet1')

    for mac in mac_addresses:
        for switch_ip in switches:
            try:
                connection = connect_to_switch(switch_ip, username, password)
                port = find_mac_on_switch(connection, mac)
                
                if port:
                    print(f"MAC {mac} found on switch {switch_ip}, port {port}")
                    change_port_vlan(connection, port, target_vlan)
                    print(f"Changed port {port} to VLAN {target_vlan}")
                    break
                else:
                    print(f"MAC {mac} not found on switch {switch_ip} or port number >= 40")
                
                connection.disconnect()
            except Exception as e:
                print(f"Error connecting to switch {switch_ip}: {str(e)}")

if __name__ == "__main__":
    main()