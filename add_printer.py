import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import os
import threading
import re # For IP validation
import glob # For finding .inf files

# --- Global variables to store paths ---
driver_folder_path = ""
inf_file_path = "" # Sẽ được tự động tìm

# Hàm is_admin() đã được loại bỏ

def validate_ip(ip_string):
    """Rudimentary IP address validation."""
    pattern = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")
    if pattern.match(ip_string):
        parts = ip_string.split(".")
        if all(0 <= int(part) <= 255 for part in parts):
            return True
    return False

def browse_driver_folder():
    global driver_folder_path, inf_file_path
    folder_selected = filedialog.askdirectory(title="Chọn thư mục chứa Driver")
    if folder_selected:
        driver_folder_path = folder_selected
        driver_folder_label.config(text=f"Thư mục Driver: {driver_folder_path}")
        log_message(f"Đã chọn thư mục driver: {driver_folder_path}")

        inf_files_found = glob.glob(os.path.join(driver_folder_path, "*.inf"))

        if not inf_files_found:
            inf_file_path = ""
            auto_inf_file_label.config(text="File .INF: Không tìm thấy file .inf nào!", fg="red")
            log_message("Lỗi: Không tìm thấy file .inf nào trong thư mục đã chọn.")
            messagebox.showerror("Lỗi File INF", "Không tìm thấy file .inf nào trong thư mục đã chọn.")
        else:
            inf_file_path = inf_files_found[0]
            auto_inf_file_label.config(text=f"File .INF tự động chọn: {os.path.basename(inf_file_path)}", fg="green")
            log_message(f"Đã tự động chọn file INF: {inf_file_path}")
            if len(inf_files_found) > 1:
                log_message(f"Cảnh báo: Tìm thấy {len(inf_files_found)} files .inf. Đã chọn file đầu tiên: {os.path.basename(inf_file_path)}")
                messagebox.showwarning("Nhiều file .INF",
                                       f"Tìm thấy {len(inf_files_found)} file .inf trong thư mục.\n"
                                       f"Đã tự động chọn file: {os.path.basename(inf_file_path)}\n"
                                       "Nếu đây không phải file .inf chính, vui lòng đảm bảo thư mục chỉ chứa file .inf cần thiết.")
    else:
        driver_folder_path = ""
        inf_file_path = ""
        driver_folder_label.config(text="Thư mục Driver: Chưa chọn")
        auto_inf_file_label.config(text="File .INF: Chưa xác định", fg="black")


def log_message(message):
    log_area.config(state=tk.NORMAL)
    log_area.insert(tk.END, message + "\n")
    log_area.see(tk.END)
    log_area.config(state=tk.DISABLED)
    print(message)

def install_printer_thread():
    ip_address = ip_entry.get().strip()

    if not validate_ip(ip_address):
        messagebox.showerror("Lỗi", "Địa chỉ IP không hợp lệ. Vui lòng nhập định dạng X.X.X.X.")
        log_message("Lỗi: Địa chỉ IP không hợp lệ.")
        install_button.config(state=tk.NORMAL)
        return

    if not driver_folder_path:
        messagebox.showerror("Lỗi", "Vui lòng chọn thư mục chứa driver.")
        log_message("Lỗi: Chưa chọn thư mục driver.")
        install_button.config(state=tk.NORMAL)
        return

    if not inf_file_path:
        messagebox.showerror("Lỗi", "Không có file .INF nào được chọn hoặc tìm thấy. Vui lòng chọn lại thư mục driver.")
        log_message("Lỗi: Không có file .INF nào để sử dụng.")
        install_button.config(state=tk.NORMAL)
        return

    if not os.path.exists(inf_file_path):
        messagebox.showerror("Lỗi", f"File .INF được tự động chọn không tồn tại: {inf_file_path}")
        log_message(f"Lỗi: File .INF được tự động chọn không tồn tại: {inf_file_path}")
        install_button.config(state=tk.NORMAL)
        return

    printer_name = f"printer_{ip_address}"
    log_message(f"Bắt đầu cài đặt máy in: {printer_name} với IP: {ip_address}")
    log_message(f"Sử dụng file INF tự động tìm thấy: {inf_file_path}")

    # Bước 1: Thêm gói driver vào hệ thống
    # Lệnh này có thể vẫn cần quyền admin trên nhiều hệ thống.
    # Nếu người dùng không có quyền, bước này sẽ thất bại.
    log_message("Bước 1: Thêm gói driver vào hệ thống...")
    pnputil_cmd = f'pnputil /add-driver "{inf_file_path}" /install'
    try:
        # CREATE_NO_WINDOW để không hiện cửa sổ cmd của PnPUtil
        process_pnputil = subprocess.run(pnputil_cmd, shell=True, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        log_message("Kết quả PnPUtil:\n" + process_pnputil.stdout)
        if process_pnputil.stderr:
            log_message("Lỗi PnPUtil (stderr):\n" + process_pnputil.stderr)
        log_message("Gói driver đã được thêm/cập nhật (hoặc đã tồn tại).")
    except subprocess.CalledProcessError as e:
        log_message(f"Lỗi khi thêm gói driver bằng PnPUtil: {e}")
        log_message(f"Output: {e.stdout}")
        log_message(f"Error: {e.stderr}")
        messagebox.showerror("Lỗi PnPUtil", f"Không thể thêm gói driver. Điều này có thể do thiếu quyền hoặc file INF không hợp lệ.\nChi tiết: {e.stderr}")
        install_button.config(state=tk.NORMAL)
        return
    except Exception as e: # Bắt các lỗi khác, ví dụ như PnPUtil không tìm thấy
        log_message(f"Lỗi không xác định với PnPUtil: {e}")
        messagebox.showerror("Lỗi PnPUtil", f"Lỗi không xác định khi thêm gói driver: {e}")
        install_button.config(state=tk.NORMAL)
        return

    # Bước 2: Cài đặt máy in
    # Lệnh này cũng có thể cần quyền admin.
    log_message(f"Bước 2: Cài đặt máy in '{printer_name}'...")
    cmd = f'rundll32 printui.dll,PrintUIEntry /if /b "{printer_name}" /f "{inf_file_path}" /r "IP_{ip_address}" /q'
    # Gợi ý: Nếu cài đặt thất bại, bạn có thể cần phải tìm "Model Name" chính xác từ file .INF
    # và thêm vào lệnh: /m "Exact Driver Model Name from INF"
    # Ví dụ: model_name_from_inf = "HP Universal Printing PCL 6"
    # cmd = f'rundll32 printui.dll,PrintUIEntry /if /b "{printer_name}" /f "{inf_file_path}" /r "IP_{ip_address}" /m "{model_name_from_inf}" /q'

    log_message(f"Thực thi lệnh: {cmd}")

    try:
        process = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        log_message("Cài đặt máy in có vẻ đã thành công (lệnh thực thi không báo lỗi).")
        log_message("Output (stdout):\n" + process.stdout)
        if process.stderr:
             log_message("Output (stderr):\n" + process.stderr) # printui có thể xuất thông tin ra stderr ngay cả khi thành công
        messagebox.showinfo("Thành công", f"Máy in '{printer_name}' có thể đã được cài đặt.\nVui lòng kiểm tra trong Control Panel > Devices and Printers.")
    except subprocess.CalledProcessError as e:
        log_message(f"Lỗi khi cài đặt máy in: {e}")
        log_message(f"Return code: {e.returncode}")
        log_message(f"Output (stdout): {e.stdout}")
        log_message(f"Error (stderr): {e.stderr}")
        error_detail = e.stderr if e.stderr else e.stdout
        messagebox.showerror("Lỗi cài đặt", f"Không thể cài đặt máy in '{printer_name}'.\nLỗi: {error_detail}\nĐiều này có thể do thiếu quyền, file INF không hợp lệ, hoặc không tìm thấy model driver phù hợp. Kiểm tra log để biết thêm chi tiết.")
    except Exception as e:
        log_message(f"Lỗi không xác định: {e}")
        messagebox.showerror("Lỗi không xác định", f"Đã xảy ra lỗi không xác định: {e}")
    finally:
        install_button.config(state=tk.NORMAL)

def start_install_thread():
    install_button.config(state=tk.DISABLED)
    thread = threading.Thread(target=install_printer_thread)
    thread.daemon = True
    thread.start()

# --- GUI Setup ---
root = tk.Tk()
root.title("Công cụ Cài đặt Máy In (Tự động tìm .inf)")
root.geometry("650x570")

# IP Address
ip_frame = tk.Frame(root)
ip_frame.pack(pady=10, padx=10, fill=tk.X)
tk.Label(ip_frame, text="IP Máy In:", width=15, anchor="w").pack(side=tk.LEFT)
ip_entry = tk.Entry(ip_frame, width=40)
ip_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
ip_entry.insert(0, "10.0.0.1") # Default IP

# Driver Folder
driver_folder_frame = tk.Frame(root)
driver_folder_frame.pack(pady=5, padx=10, fill=tk.X)
browse_driver_button = tk.Button(driver_folder_frame, text="1. Chọn thư mục Driver...", command=browse_driver_folder, width=22)
browse_driver_button.pack(side=tk.LEFT)
driver_folder_label = tk.Label(driver_folder_frame, text="Thư mục Driver: Chưa chọn", wraplength=380, anchor="w", justify="left")
driver_folder_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

# Label for auto-detected INF file
auto_inf_frame = tk.Frame(root)
auto_inf_frame.pack(pady=(0,5), padx=10, fill=tk.X)
auto_inf_file_label = tk.Label(auto_inf_frame, text="File .INF: Chưa xác định (Sẽ tự động tìm sau khi chọn thư mục)", wraplength=600, anchor="w", justify="left")
auto_inf_file_label.pack(side=tk.LEFT, padx=(22 + 8), pady=(0,5))

# Install Button
install_button = tk.Button(root, text="2. Cài đặt Máy In", command=start_install_thread, font=("Arial", 12, "bold"), bg="lightblue")
install_button.pack(pady=20)

# Log Area
log_label = tk.Label(root, text="Log hoạt động:")
log_label.pack(pady=(10,0), padx=10, anchor="w")
log_area = scrolledtext.ScrolledText(root, height=15, width=80, state=tk.DISABLED, wrap=tk.WORD)
log_area.pack(pady=5, padx=10, expand=True, fill=tk.BOTH)

log_message("Khởi động Công cụ Cài đặt Máy In.")
# Không còn kiểm tra quyền admin ở đây
# install_button sẽ mặc định là enabled (trừ khi bị disable bởi logic khác)

root.mainloop()