import getpass
from netmiko import ConnectHandler

def main():
    # Nhập thông tin từ người dùng
    ip_address = input("Nhập địa chỉ IP của switch: ")
    username = input("Nhập tên người dùng: ")
    password = getpass.getpass("Nhập mật khẩu: ")
    vlan = input("Nhập VLAN mới: ")
    mac_address = input("Nhập địa chỉ MAC cần tìm: ")

    # Cấu hình thiết bị
    device = {
        'device_type': 'cisco_ios',
        'ip': ip_address,
        'username': username,
        'password': password,
    }

    try:
        # Kết nối đến switch
        with ConnectHandler(**device) as conn:
            print("Đã kết nối thành công đến switch.")

            # Tìm kiếm địa chỉ MAC
            output = conn.send_command(f"show mac address-table | in {mac_address}")
            
            if output:
                # Tách thông tin từ output
                parts = output.split()
                if len(parts) >= 4:
                    port = parts[-1]
                    if port.startswith("Gi"):
                        print(f"Đã tìm thấy địa chỉ MAC trên cổng {port}")
                        
                        # Thay đổi VLAN của cổng
                        config_commands = [
                            f"interface {port}",
                            f"switchport access vlan {vlan}",
                            "exit"
                        ]
                        conn.send_config_set(config_commands)
                        print(f"Đã chuyển cổng {port} sang VLAN {vlan}")
                        
                        # Lưu cấu hình
                        conn.save_config()
                        print("Đã lưu cấu hình.")
                    else:
                        print(f"Cổng tìm thấy ({port}) không phải dạng Gi1/0/x.")
                else:
                    print("Không thể xác định cổng từ kết quả tìm kiếm.")
            else:
                print("Không tìm thấy địa chỉ MAC trên switch.")

    except Exception as e:
        print(f"Có lỗi xảy ra: {e}")

if __name__ == "__main__":
    main()

print("Write with anhln1.")
time.sleep(120.5)


