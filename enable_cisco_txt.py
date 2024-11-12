from netmiko import ConnectHandler
import time
import getpass
import os

def read_ip_list(filename):
    while True:
        try:
            with open(filename, 'r') as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            print(f"File '{filename}' not found.")
            filename = input("Please enter the correct file path: ")

def connect_and_configure(ip, username, password):
    print(f"Connecting to {ip}...")
    device = {
        'device_type': 'cisco_ios',
        'ip': ip,
        'username': username,
        'password': password,
    }
    try:
        with ConnectHandler(**device) as net_connect:
            # Thực hiện lệnh "clear port-security all"
            net_connect.send_command("clear port-security all")
            print("Executed 'clear port-security all'")
            
            # Tìm kiếm các cổng bị disable
            output = net_connect.send_command("show int status")
            for line in output.splitlines():
                if "disabled" in line:
                    port = line.split()[0]
                    print(f"Checking port {port}")
                    
                    # Kiểm tra xem có loop không
                    port_output = net_connect.send_command(f"show interface {port}")
                    if "loop" in port_output.lower():
                        print(f"Skipping port {port} due to loop detection")
                    else:
                        print(f"Enabling port {port}")
                        commands = [
                            f"interface {port}",
                            "shutdown",
                            "no shutdown"
                        ]
                        net_connect.send_config_set(commands)
        
        print(f"Finished with {ip}. Moving to the next switch after 20 seconds...")
        time.sleep(20)  # Delay 20 giây trước khi chuyển sang switch tiếp theo
    except Exception as e:
        print(f"An error occurred while connecting to {ip}: {e}")

def main():
    # Nhập thông tin người dùng
    username = input("Enter your username: ")
    password = getpass.getpass('Password: ')

    # Đọc danh sách IP từ file
    while True:
        ip_file = input("Enter the name of the file containing IP addresses: ")
        if os.path.exists(ip_file):
            ip_list = read_ip_list(ip_file)
            break
        else:
            print(f"File '{ip_file}' not found. Please try again.")

    # Lặp qua mỗi IP trong danh sách
    for ip in ip_list:
        connect_and_configure(ip, username, password)

    print("Script completed.")

if __name__ == "__main__":
    main()