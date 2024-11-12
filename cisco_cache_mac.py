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
