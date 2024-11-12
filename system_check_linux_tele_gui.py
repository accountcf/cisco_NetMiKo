import tkinter as tk
from tkinter import filedialog, scrolledtext
import paramiko
import asyncio
from telegram import Bot
import threading

class SystemMonitorGUI:
    def __init__(self, master):
        self.master = master
        master.title("System Monitor")
        master.geometry("700x600")

        # IP List File
        tk.Label(master, text="IP List File:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ip_file_entry = tk.Entry(master, width=50)
        self.ip_file_entry.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(master, text="Browse", command=self.browse_file).grid(row=0, column=2, padx=5, pady=5)

        # Username
        tk.Label(master, text="Username:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.username_entry = tk.Entry(master, width=50)
        self.username_entry.grid(row=1, column=1, padx=5, pady=5)

        # Password
        tk.Label(master, text="Password:").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.password_entry = tk.Entry(master, width=50, show="*")
        self.password_entry.grid(row=2, column=1, padx=5, pady=5)

        # Start Button
        self.start_button = tk.Button(master, text="Start Monitoring", command=self.start_monitoring)
        self.start_button.grid(row=3, column=1, pady=10)

        # Output Area
        self.output_area = scrolledtext.ScrolledText(master, width=80, height=30)
        self.output_area.grid(row=4, column=0, columnspan=3, padx=5, pady=5)

        # Copyright
        tk.Label(master, text="Bản quyền bởi Anhln1", fg="gray").grid(row=5, column=0, columnspan=3, pady=5)

    def browse_file(self):
        filename = filedialog.askopenfilename()
        self.ip_file_entry.delete(0, tk.END)
        self.ip_file_entry.insert(0, filename)

    def start_monitoring(self):
        self.output_area.delete(1.0, tk.END)
        self.start_button.config(state=tk.DISABLED)
        threading.Thread(target=self.run_monitoring, daemon=True).start()

    def run_monitoring(self):
        asyncio.run(self.main())
        self.start_button.config(state=tk.NORMAL)

    def read_ip_list(self, file_path):
        with open(file_path, 'r') as file:
            ip_list = file.readlines()
        return [ip.strip() for ip in ip_list]

    async def send_telegram_message(self, bot_token, chat_id, message):
        try:
            telegram_notify = Bot(token=bot_token)
            await telegram_notify.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            self.output_area.insert(tk.END, f"Sent message to Telegram: {message}\n")
        except Exception as ex:
            self.output_area.insert(tk.END, f"Error sending message to Telegram: {ex}\n")

    async def check_system(self, ip, username, password, bot_token, chat_id):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password)

            # Check Disk Usage
            stdin, stdout, stderr = ssh.exec_command("df -h")
            disk_output = stdout.read().decode()
            
            # Check CPU Usage
            stdin, stdout, stderr = ssh.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
            cpu_output = stdout.read().decode().strip()
            
            # Check RAM Usage
            stdin, stdout, stderr = ssh.exec_command("free -m | awk 'NR==2{printf \"%.2f%%\", $3*100/$2 }'")
            ram_output = stdout.read().decode().strip()

            self.output_area.insert(tk.END, f"\nSystem check for {ip}:\n")
            self.output_area.insert(tk.END, f"CPU Usage: {cpu_output}%\n")
            self.output_area.insert(tk.END, f"RAM Usage: {ram_output}\n")
            self.output_area.insert(tk.END, "Disk Usage:\n")
            
            for line in disk_output.split("\n"):
                if '%' in line:
                    try:
                        usage = int(line.split()[-2].replace('%', ''))
                        if usage > 10:
                            warning_message = f"Warning: High disk usage on {ip}: {line}"
                            self.output_area.insert(tk.END, warning_message + "\n")
                            await self.send_telegram_message(bot_token, chat_id, warning_message)
                        else:
                            self.output_area.insert(tk.END, f"{line}\n")
                    except ValueError:
                        continue

            ssh.close()
        except Exception as e:
            self.output_area.insert(tk.END, f"Failed to connect to {ip}: {e}\n")

    async def main(self):
        ip_list = self.read_ip_list(self.ip_file_entry.get())
        username = self.username_entry.get()
        password = self.password_entry.get()
        bot_token = "7212490708:AAG_mkQxkkcXfxPYqMRhV_Tp5J2a8RiBSeA"
        chat_id = "-4281047122"

        for ip in ip_list:
            await self.check_system(ip, username, password, bot_token, chat_id)
            await asyncio.sleep(20)

root = tk.Tk()
app = SystemMonitorGUI(root)
root.mainloop()