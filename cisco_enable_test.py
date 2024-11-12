from netmiko import ConnectHandler
import time
import getpass

# Tạo danh sách IP từ 10.33.69.248 đến 10.38.1.40
ip_list = [f"10.33.69.{i}" for i in range(248, 250)]

# Nhập thông tin người dùng
username = input("Enter your username: ")
password = getpass.getpass('Password:')

# Lặp qua mỗi IP trong danh sách
for ip in ip_list:
    print(f"Connecting to {ip}...")
    device = {
        'device_type': 'cisco_ios',  # Thay đổi nếu dùng loại switch khác
        'ip': ip,
        'username': username,
        'password': password,
    }

    try:
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
        print(f"Finished with {ip}. Moving to the next switch after 20 seconds...")
        time.sleep(10)  # Delay 20 giây trước khi chuyển sang switch tiếp theo

    except Exception as e:
        print(f"An error occurred while connecting to {ip}: {e}")

print("Script completed.")