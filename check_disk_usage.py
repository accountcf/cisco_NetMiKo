import paramiko
import getpass
from time import sleep

def read_ip_list(file_path):
    with open(file_path, 'r') as file:
        ip_list = file.readlines()
    return [ip.strip() for ip in ip_list]

def check_disk_usage(ip, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        stdin, stdout, stderr = ssh.exec_command("df -h")
        output = stdout.read().decode()

        for line in output.split("\n"):
            if '%' in line:
                try:
                    usage = int(line.split()[-2].replace('%', ''))
                    if usage > 10:
                        print(f"Warning: High disk usage on {ip}: {line}")
                except ValueError:
                    # Skip the header or any line that doesn't contain a valid percentage
                    continue

        ssh.close()
    except Exception as e:
        print(f"Failed to connect to {ip}: {e}")

def main():
    ip_list = read_ip_list("G:\\scripts\\python\\ip_list.txt")
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")

    for ip in ip_list:
        check_disk_usage(ip, username, password)
        sleep(20)

if __name__ == "__main__":
    main()