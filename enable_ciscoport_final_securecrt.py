# $language = "Python"

# $interface = "1.0"

 

def main():

  # Display SecureCRT's version

  crt.Dialog.MessageBox("SecureCRT version is: " + crt.Version)

main()

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
