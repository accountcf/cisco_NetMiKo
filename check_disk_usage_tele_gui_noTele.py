import tkinter as tk
from tkinter import filedialog, scrolledtext
import paramiko
import asyncio
import threading

class DiskMonitorGUI:
    def __init__(self, master):
        self.master = master
        master.title("Disk Usage Monitor")
        master.geometry("600x500")

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
        self.output_area = scrolledtext.ScrolledText(master, width=70, height=20)
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

    async def check_disk_usage(self, ip, username, password):
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
                            self.output_area.insert(tk.END, warning_message + "\n")
                    except ValueError:
                        continue
            ssh.close()
        except Exception as e:
            self.output_area.insert(tk.END, f"Failed to connect to {ip}: {e}\n")

    async def main(self):
        ip_list = self.read_ip_list(self.ip_file_entry.get())
        username = self.username_entry.get()
        password = self.password_entry.get()

        for ip in ip_list:
            await self.check_disk_usage(ip, username, password)
            await asyncio.sleep(20)

        self.output_area.insert(tk.END, "Monitoring completed.\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = DiskMonitorGUI(root)
    root.mainloop()