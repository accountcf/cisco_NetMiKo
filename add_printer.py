import tkinter as tk
from tkinter import messagebox, filedialog
import subprocess

def install_printer():
    ip = ip_entry.get()
    inf_path = inf_entry.get()

    if not ip or not inf_path:
        messagebox.showerror("Lỗi", "Vui lòng nhập IP và đường dẫn đến file driver .inf.")
        return

    # Kiểm tra xem máy in đã tồn tại chưa
    printer_name = f"printer_{ip}"
    existing_printers = subprocess.check_output("wmic printer get name", shell=True).decode().splitlines()
    
    count = 1
    while printer_name in existing_printers:
        count += 1
        printer_name = f"printer_{ip}_{count}"

    # Cài đặt máy in
    try:
        # Lệnh cài đặt máy in
        command = f"rundll32 printui.dll,PrintUIEntry /if /b \"{printer_name}\" /f \"{inf_path}\" /r \"\\{ip}\" /m \"Generic / Text Only\""
        subprocess.run(command, shell=True, check=True)
        messagebox.showinfo("Thành công", f"Cài đặt máy in {printer_name} thành công.")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Lỗi", f"Cài đặt máy in thất bại: {e}")

def browse_driver():
    # Mở hộp thoại chọn file
    file_path = filedialog.askopenfilename(title="Chọn file driver (.inf)", filetypes=[("Driver Files", "*.inf")])
    if file_path:
        inf_entry.delete(0, tk.END)  # Xóa nội dung cũ
        inf_entry.insert(0, file_path)  # Thêm đường dẫn mới vào Entry

# Tạo GUI
root = tk.Tk()
root.title("Cài đặt máy in(viết bởi anhln1)")

# Nhập IP
tk.Label(root, text="Nhập IP máy in:").pack(pady=5)
ip_entry = tk.Entry(root)
ip_entry.pack(pady=5)

# Nhập đường dẫn driver
tk.Label(root, text="Nhập đường dẫn đến file driver (.inf):").pack(pady=5)
inf_entry = tk.Entry(root)
inf_entry.pack(pady=5)

# Nút Browse
browse_button = tk.Button(root, text="Browse", command=browse_driver)
browse_button.pack(pady=5)

# Nút cài đặt
install_button = tk.Button(root, text="Cài đặt máy in", command=install_printer)
install_button.pack(pady=20)

# Chạy GUI
root.mainloop()