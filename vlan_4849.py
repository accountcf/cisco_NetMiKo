from netmiko import ConnectHandler, NetmikoAuthenticationException
import getpass
import logging

# Bật logging cho Netmiko
logging.basicConfig(filename='netmiko_log.txt', level=logging.DEBUG)
logger = logging.getLogger("netmiko")

def connect_to_switch(ip, username, password, device_type='cisco_ios_telnet'):
    try:
        connection = ConnectHandler(
            device_type=device_type,
            host=ip,
            username=username,
            password=password,
        )
        print(f"Kết nối thành công tới {ip}")
        return connection
    except NetmikoAuthenticationException as e:
        print(f"Lỗi xác thực khi kết nối tới {ip}: {e}")
        raise
    except Exception as e:
        print(f"Lỗi khi kết nối tới {ip}: {e}")
        raise

def get_connected_switches(connection):
    output = connection.send_command("show cdp neighbors detail")
    switches = []
    for line in output.splitlines():
        if "Device ID" in line:
            switch_ip = line.split()[-1]
            switches.append(switch_ip)
    return switches

def find_ip_on_switch(connection, target_ip):
    output = connection.send_command("show ip arp")
    for line in output.splitlines():
        if target_ip in line:
            port = line.split()[-1]
            return port
    return None

def change_vlan_on_port(connection, port, vlan):
    commands = [
        f"interface {port}",
        f"switchport access vlan {vlan}",
        "end"
    ]
    connection.send_config_set(commands)

def main():
    # Nhập thông tin kết nối
    switch_ip = input("Nhập địa chỉ IP của switch 4849: ")
    username = input("Nhập username: ")
    password = getpass.getpass('Password: ')
    vlan = input("Nhập VLAN mới: ")
    target_ip = input("Nhập địa chỉ IP cần tìm: ")

    # Kết nối tới switch 4849
    print(f"Kết nối tới switch 4849 ({switch_ip})...")
    try:
        switch_conn = connect_to_switch(switch_ip, username, password)
    except Exception as e:
        print(f"Không thể kết nối tới switch 4849. Lỗi: {e}")
        return

    # Lấy danh sách các switch kết nối với switch 4849
    print("Lấy danh sách các switch kết nối với switch 4849...")
    connected_switches = get_connected_switches(switch_conn)
    print(f"Các switch kết nối: {connected_switches}")

    # Tìm địa chỉ IP trên các switch kết nối
    for switch in connected_switches:
        print(f"Kết nối tới switch {switch}...")
        try:
            switch_conn_2960 = connect_to_switch(switch, username, password)
            port = find_ip_on_switch(switch_conn_2960, target_ip)
            if port:
                print(f"Tìm thấy địa chỉ IP {target_ip} trên port {port} của switch {switch}")
                print(f"Chuyển VLAN của port {port} sang VLAN {vlan}...")
                change_vlan_on_port(switch_conn_2960, port, vlan)
                print(f"Đã chuyển VLAN của port {port} sang VLAN {vlan}")
                break
            else:
                print(f"Không tìm thấy địa chỉ IP {target_ip} trên switch {switch}")
        except Exception as e:
            print(f"Không thể kết nối tới switch {switch}. Lỗi: {e}")

if __name__ == "__main__":
    main()
