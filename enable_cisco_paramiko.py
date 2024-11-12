import paramiko
import getpass

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Khởi tạo kết nối đến switch Cisco
ip = input("Nhập ip switch:")
username = input("Nhập username:")
password = getpass.getpass('Password:')

# Kết nối đến switch
ssh.connect(ip, username=username, password=password)
conn = ssh.invoke_shell()

# Thực hiện lệnh "clear port-security all"
conn.send('clear port-security alln')
conn.send('n')

# Tìm kiếm các cổng bị disable
conn.send('show int statusn')
output = conn.recv(65535).decode("utf-8")

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
        for command in commands:
            conn.send(command)
            conn.send('n')

ssh.close()
