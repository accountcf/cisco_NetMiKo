import tkinter as tk
from tkinter import filedialog, messagebox
import os
import subprocess

class PrinterInstallerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Printer Installer")
        
        self.setup_gui()
    
    def setup_gui(self):
        # IP Address Label and Entry
        self.ip_label = tk.Label(self.root, text="Printer IP Address:")
        self.ip_label.grid(row=0, column=0, padx=10, pady=10)
        
        self.ip_entry = tk.Entry(self.root)
        self.ip_entry.grid(row=0, column=1, padx=10, pady=10)
        
        # Driver File Label and Button
        self.driver_label = tk.Label(self.root, text="Printer Driver (.inf):")
        self.driver_label.grid(row=1, column=0, padx=10, pady=10)
        
        self.driver_path = tk.StringVar()
        self.driver_entry = tk.Entry(self.root, textvariable=self.driver_path, state='readonly')
        self.driver_entry.grid(row=1, column=1, padx=10, pady=10)
        
        self.browse_button = tk.Button(self.root, text="Browse", command=self.browse_driver)
        self.browse_button.grid(row=1, column=2, padx=10, pady=10)
        
        # Install Button
        self.install_button = tk.Button(self.root, text="Install Printer", command=self.install_printer)
        self.install_button.grid(row=2, column=0, columnspan=3, pady=20)
    
    def browse_driver(self):
        file_path = filedialog.askopenfilename(filetypes=[("INF files", "*.inf")])
        if file_path:
            self.driver_path.set(file_path)
    
    def install_printer(self):
        ip_address = self.ip_entry.get()
        driver_path = self.driver_path.get()
        
        if not ip_address or not driver_path:
            messagebox.showerror("Error", "Please provide both the IP address and driver file.")
            return
        
        printer_name = f"printer_{ip_address}"
        
        try:
            # Command to install the printer driver using pnputil
            install_driver_cmd = f'pnputil /add-driver "{driver_path}" /install'
            subprocess.run(install_driver_cmd, check=True, shell=True)
            
            # Command to add the printer port using PowerShell
            add_port_cmd = f'powershell Add-PrinterPort -Name "IP_{ip_address}" -PrinterHostAddress "{ip_address}"'
            subprocess.run(add_port_cmd, check=True, shell=True)
            
            # Command to add the printer using PowerShell
            add_printer_cmd = f'powershell Add-Printer -Name "{printer_name}" -DriverName "HP Printer" -PortName "IP_{ip_address}"'
            subprocess.run(add_printer_cmd, check=True, shell=True)
            
            messagebox.showinfo("Success", f"Printer {printer_name} installed successfully.")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to install printer: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PrinterInstallerApp(root)
    root.mainloop()