from netmiko import ConnectHandler
import getpass

def connect_to_switch(ip, username, password):
    return ConnectHandler(
        device_type='cisco_ios',
        host=ip,
        username=username,
        password=password,
    )

def clear_port_security(connection):
    connection.send_command("clear port-security all")

def get_disabled_ports(connection):
    output = connection.send_command("show int status")
    disabled_ports = []
    for line in output.splitlines():
        if "disabled" in line:
            port = line.split()[0]
            disabled_ports.append(port)
    return disabled_ports

def enable_ports(connection, ports):
    for port in ports:
        print(f"Enabling port {port}")
        commands = [
            f"interface {port}",
            "shutdown",
            "no shutdown"
        ]
        connection.send_config_set(commands)

def main():
    # Nhập thông tin switch
    switch1_ip = input("Nhập địa chỉ IP của switch 1 (xx.xx.xx.248): ")
    switch2_ip = input("Nhập địa chỉ IP của switch 2 (xx.xx.xx.249): ")
    
    # Nhập thông tin đăng nhập
    username = input("Nhập username: ")
    password = getpass.getpass('Password: ')

    # Kết nối và xử lý switch 1
    print(f"Kết nối đến switch 1 ({switch1_ip})...")
    switch1_conn = connect_to_switch(switch1_ip, username, password)
    
    print("Gửi lệnh 'clear port-security all'...")
    clear_port_security(switch1_conn)

    print("Lấy danh sách cổng bị disabled...")
    disabled_ports_switch1 = get_disabled_ports(switch1_conn)
    print(f"Các cổng bị disabled trên switch 1: {disabled_ports_switch1}")

    print("Mở các cổng bị disabled...")
    enable_ports(switch1_conn, disabled_ports_switch1)
    
    switch1_conn.disconnect()

    # Kết nối và xử lý switch 2
    print(f"Kết nối đến switch 2 ({switch2_ip})...")
    switch2_conn = connect_to_switch(switch2_ip, username, password)

    print("Gửi lệnh 'clear port-security all'...")
    clear_port_security(switch2_conn)

    print("Lấy danh sách cổng bị disabled...")
    disabled_ports_switch2 = get_disabled_ports(switch2_conn)
    print(f"Các cổng bị disabled trên switch 2: {disabled_ports_switch2}")

    print("Mở các cổng bị disabled...")
    enable_ports(switch2_conn, disabled_ports_switch2)
    
    switch2_conn.disconnect()

if __name__ == "__main__":
    main()