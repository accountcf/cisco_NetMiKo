from netmiko import ConnectHandler
import getpass

device = {
    "device_type": "cisco_ios",
    "ip": input("Nhập ip switch: "),
    "username": input("Nhập username: "),
    "password": getpass.getpass('Password: ')
}

with ConnectHandler(**device) as net_connect:
    # Gửi lệnh "clear port-security all"
    net_connect.send_command("clear port-security all")
    
    # Lấy thông tin trạng thái các interface
    output = net_connect.send_command("show int status")
    
    for line in output.splitlines():
        if "disabled" in line:
            port = line.split()[0]
            print(f"Enabling port {port}")
            
            commands = [
                f"interface {port}",
                "shutdown",
                "no shutdown"
            ]
            net_connect.send_config_set(commands)

print("Hoàn thành việc bật các cổng bị vô hiệu hóa.")