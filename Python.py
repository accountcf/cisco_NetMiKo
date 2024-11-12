import os




def script_1():
    print("Đang thực thi script 1")
    from netmiko import ConnectHandler
import getpass

# Khởi tạo kết nối đến switch Cisco
device = {
    "device_type": "cisco_ios",
    "ip": input("Nhập ip switch:"),
    "username": input("Nhập username:"),
    "password": getpass.getpass('Password:')
}

# Kết nối đến switch
with ConnectHandler(**device) as net_connect:
    # Thực hiện lệnh "clear port-security all"
    net_connect.send_command("clear port-security all")

    # Tìm kiếm các cổng bị disable
    output = net_connect.send_command("show int status")
    for line in output.splitlines():
        if "disabled" in line:
            port = line.split()[0]
            print(f"Enabling port {port}")
            # Thực hiện lệnh enable trên cổng
            commands = [
                f"interface {port}",
                "shutdown",
                "no shutdown"
            ]
            net_connect.send_config_set(commands)
    os.system('python script1.py')

def script_2():
    print("Đang thực thi script 2")
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
    os.system('python script2.py')

def script_3():
    print("Đang thực thi script 3")
    from netmiko import ConnectHandler
import getpass

def enable_disabled_ports(switch_ip, username, password):
    device = {
        "device_type": "cisco_ios",
        "ip": switch_ip,
        "username": username,
        "password": password
    }
commands = [
                    f"interface {port}",
                    "no shutdown"
                ]
    with ConnectHandler(**device) as net_connect:
        # Find disabled ports
        output = net_connect.send_command("show int status")
        disabled_ports = []
        for line in output.splitlines():
            if "disabled" in line:
                port = line.split()[0]
                disabled_ports.append(port)
                print(f"Found disabled port: {port}")

        # Enable disabled ports (confirmation prompt optional)
        if disabled_ports:
            for port in disabled_ports:
                # Optional confirmation:
                # confirm = input(f"Enable port {port}? (y/n): ")
                # if confirm.lower() == 'y':
               
                net_connect.send_config_set(commands)
                print(f"Enabled port {port}")

if __name__ == "__main__":
    switch_ip = input("Nhập ip switch: ")
    username = input("Nhập username: ")
    password = getpass.getpass("Password: ")
    enable_disabled_ports(switch_ip, username, password)

    os.system('python script3.py')

def main():
    while True:
        print("\n--- Menu ---")
        print("1. Thực thi script 1")
        print("2. Thực thi script 2")
        print("3. Thực thi script 3")
        print("4. Thoát")

        choice = input("Chọn một tùy chọn: ")

        if choice == '1':
            script_1()
        elif choice == '2':
            script_2()
        elif choice == '3':
            script_3()
        elif choice == '4':
            print("Thoát chương trình.")
            break
        else:
            print("Lựa chọn không hợp lệ. Vui lòng chọn lại.")

if __name__ == "__main__":
    main()