import tkinter as tk
from tkinter import filedialog, messagebox
import subprocess
import os
import sys
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

def install_printer():
    ip = ip_entry.get()
    driver_path = driver_path_entry.get()
    printer_name = f"printer_{ip}"

    if not ip or not driver_path:
        result_label.config(text="Vui lòng nhập IP và chọn driver")
        return

    try:
        # Sử dụng PowerShell để cài đặt máy in
        command = f'Add-PrinterPort -Name "IP_{ip}" -PrinterHostAddress "{ip}"; Add-PrinterDriver -Name "HP Network Printer" -InfPath "{driver_path}"; Add-Printer -Name "{printer_name}" -DriverName "HP Network Printer" -PortName "IP_{ip}"'
        
        result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, check=True)
        
        if result.returncode == 0:
            result_label.config(text="Máy in đã được cài đặt thành công")
        else:
            result_label.config(text=f"Lỗi: {result.stderr}")
    except subprocess.CalledProcessError as e:
        result_label.config(text=f"Có lỗi xảy ra khi cài đặt máy in: {e.output}")

def browse_driver():
    filename = filedialog.askopenfilename(filetypes=[("INF files", "*.inf")])
    driver_path_entry.delete(0, tk.END)
    driver_path_entry.insert(0, filename)

# Kiểm tra quyền admin
if not is_admin():
    messagebox.showwarning("Cảnh báo", "Chương trình cần quyền admin để cài đặt máy in. Vui lòng chạy lại với quyền admin.")
    run_as_admin()
    sys.exit()

# Tạo cửa sổ chính
root = tk.Tk()
root.title("Cài đặt máy in HP")

# IP máy in
tk.Label(root, text="IP máy in:").grid(row=0, column=0, sticky="e")
ip_entry = tk.Entry(root)
ip_entry.grid(row=0, column=1)

# Đường dẫn driver
tk.Label(root, text="Driver máy in:").grid(row=1, column=0, sticky="e")
driver_path_entry = tk.Entry(root)
driver_path_entry.grid(row=1, column=1)
browse_button = tk.Button(root, text="Chọn", command=browse_driver)
browse_button.grid(row=1, column=2)

# Nút cài đặt
install_button = tk.Button(root, text="Cài đặt máy in", command=install_printer)
install_button.grid(row=2, column=1)

# Nhãn kết quả
result_label = tk.Label(root, text="")
result_label.grid(row=3, column=0, columnspan=3)

# Thêm dòng bản quyền
copyright_label = tk.Label(root, text="Bản Quyền với anhln1", font=("Arial", 8, "italic"))
copyright_label.grid(row=4, column=0, columnspan=3, pady=(10, 0))

root.mainloop()