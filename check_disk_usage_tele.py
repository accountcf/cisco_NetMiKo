import paramiko
import getpass
from time import sleep
import asyncio
from telegram import Bot

# Äá»c danh sÃ¡ch IP tá»« file
def read_ip_list(file_path):
    with open(file_path, 'r') as file:
        ip_list = file.readlines()
    return [ip.strip() for ip in ip_list]

# Gá»­i cáº£nh bÃ¡o Ä‘áº¿n Telegram
async def send_telegram_message(bot_token, chat_id, message):
    try:
        telegram_notify = Bot(token=bot_token)
        await telegram_notify.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        print(f"Sent message to Telegram: {message}")
    except Exception as ex:
        print(f"Error sending message to Telegram: {ex}")

# Kiá»ƒm tra dung lÆ°á»£ng Ä‘Ä©a
async def check_disk_usage(ip, username, password, bot_token, chat_id):
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
                        warning_message = f"Warning: High disk usage on {ip}: {line}"
                        print(warning_message)
                        await send_telegram_message(bot_token, chat_id, warning_message)
                except ValueError:
                    # Skip the header or any line that doesn't contain a valid percentage
                    continue

        ssh.close()
    except Exception as e:
        print(f"Failed to connect to {ip}: {e}")

async def main():
    ip_list = read_ip_list("G:\scripts\python\ip_list.txt")
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    bot_token = "7212490708:AAG_mkQxkkcXfxPYqMRhV_Tp5J2a8RiBSeA"
    chat_id = "-4281047122"

    for ip in ip_list:
        await check_disk_usage(ip, username, password, bot_token, chat_id)
        await asyncio.sleep(20)

if __name__ == "__main__":
    asyncio.run(main())