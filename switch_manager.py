# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
import re
import webbrowser
import threading
import queue
import logging
import time
from typing import List, Tuple, Optional, Dict, Any
from ipaddress import ip_address

# Constants
APP_NAME = "L1 Switch Automation (Telnet)"
APP_VERSION = "1.3"
AUTHOR = "Anhln1 (v1.3)"
TELNET_TIMEOUT = 20
DOC_URL = "https://wiki.lpbank.com.vn/w/index.php/D%E1%BB%8Bch_v%E1%BB%A5_%E1%BB%A8ng_d%E1%BB%A5ng_H%E1%BA%A1_t%E1%BA%A7ng_CNTT"
MAX_MAC_COUNT_SEARCH = 10  # Skip ports with more than this number of MACs in mac_search mode

# Logging Setup (Console/GUI Only)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Regex
MAC_TABLE_RE = re.compile(
    r"^\s*(?:\*|\s)\s*(?P<vlan>\d+)\s+"
    r"(?P<mac>[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4})\s+"
    r"\S+\s+"
    r"(?P<port>\S+)\s*$",
    re.IGNORECASE | re.MULTILINE
)
VALID_MAC_RE = re.compile(r'^[0-9a-fA-F:-]{12,17}$')
VALID_MAC_LAST4_RE = re.compile(r'^[0-9a-fA-F]{4}$')
VALID_VLAN_RE = re.compile(r'^\d{1,4}$')

# Thread-Safe Queue
gui_queue = queue.Queue()

# Core Network & Logic Functions
def generate_switch_ips(start_ip: str, end_ip: str) -> Tuple[Optional[List[str]], Optional[str]]:
    ip_list = []
    try:
        start_ip_clean = start_ip.strip()
        end_ip_clean = end_ip.strip()
        start_parts = start_ip_clean.split('.')
        end_parts = end_ip_clean.split('.')

        if (len(start_parts) != 4 or len(end_parts) != 4 or
                not all(part.isdigit() and 0 <= int(part) <= 255 for part in start_parts + end_parts)):
            raise ValueError("Định dạng địa chỉ IP không hợp lệ.")

        start_octets = [int(x) for x in start_parts]
        end_octets = [int(x) for x in end_parts]

        start_num = (start_octets[0] << 24) | (start_octets[1] << 16) | (start_octets[2] << 8) | start_octets[3]
        end_num = (end_octets[0] << 24) | (end_octets[1] << 16) | (end_octets[2] << 8) | end_octets[3]

        if start_num > end_num:
            raise ValueError("IP bắt đầu phải nhỏ hơn hoặc bằng IP kết thúc.")

        ip_count = end_num - start_num + 1
        if ip_count > 1024:
            logger.warning(f"Yêu cầu dải IP lớn: {start_ip_clean} - {end_ip_clean} ({ip_count} IPs)")

        current_num = start_num
        while current_num <= end_num:
            ip = f"{(current_num >> 24) & 255}.{(current_num >> 16) & 255}.{(current_num >> 8) & 255}.{current_num & 255}"
            ip_list.append(ip)
            current_num += 1

        if not ip_list:
            raise ValueError("Danh sách IP sinh ra trống (dải có thể không hợp lệ).")

        return ip_list, None

    except ValueError as e:
        logger.error(f"Lỗi dải IP: {e}. Đầu vào: '{start_ip}' - '{end_ip}'")
        return None, f"Lỗi dải IP: {e}"
    except Exception as e:
        logger.exception(f"Lỗi không xác định khi tạo dải IP: {start_ip} - {end_ip}")
        return None, f"Lỗi không xác định khi tạo dải IP: {e}"

def clean_mac(mac: str) -> Optional[str]:
    cleaned = re.sub(r'[-:.]', '', mac.strip().lower())
    if len(cleaned) == 12 and all(c in '0123456789abcdef' for c in cleaned):
        return cleaned
    logger.warning(f"Phát hiện định dạng MAC không hợp lệ: {mac}")
    return None

def format_mac_cisco(mac_cleaned: str) -> str:
    if len(mac_cleaned) != 12:
        logger.error(f"Đầu vào không hợp lệ cho format_mac_cisco: {mac_cleaned}")
        return mac_cleaned
    return f"{mac_cleaned[:4]}.{mac_cleaned[4:8]}.{mac_cleaned[8:]}"

def connect_to_device(ip: str, username: str, password: str) -> Tuple[Optional[ConnectHandler], str]:
    device_info = {
        'device_type': 'cisco_ios_telnet',
        'host': ip,
        'username': username,
        'password': password,
        'timeout': TELNET_TIMEOUT,
    }
    try:
        logger.info(f"Đang thử kết nối Telnet đến {ip}...")
        connection = ConnectHandler(**device_info)
        prompt = connection.find_prompt()
        logger.info(f"Kết nối Telnet thành công đến {ip} ({prompt})")
        return connection, f"Đã kết nối Telnet đến {ip}"
    except NetmikoTimeoutException:
        logger.warning(f"Hết thời gian kết nối Telnet đến {ip}")
        return None, f"Hết thời gian kết nối Telnet đến {ip}"
    except NetmikoAuthenticationException:
        logger.error(f"Xác thực Telnet thất bại cho {ip}")
        return None, f"Xác thực Telnet thất bại cho {ip}"
    except Exception as e:
        logger.exception(f"Kết nối Telnet đến {ip} thất bại: {type(e).__name__}")
        return None, f"Lỗi kết nối Telnet đến {ip}: {type(e).__name__}"

def disconnect_device(connection: Optional[ConnectHandler], ip: str):
    if connection and connection.is_alive():
        try:
            connection.disconnect()
            logger.info(f"Đã ngắt kết nối Telnet khỏi {ip}")
        except Exception as e:
            logger.exception(f"Lỗi khi ngắt kết nối Telnet khỏi {ip}")
    elif connection:
        logger.warning(f"Thử ngắt kết nối Telnet khỏi {ip}, nhưng kết nối không còn hoạt động.")

def get_mac_address_table(connection: ConnectHandler) -> Optional[str]:
    ip = getattr(connection, 'host', 'IP không xác định')
    try:
        logger.debug(f"Gửi lệnh 'show mac address-table' đến {ip}")
        output = connection.send_command_timing("show mac address-table", delay_factor=2)
        logger.debug(f"Nhận bảng MAC từ {ip} (độ dài: {len(output) if output else 0})")
        if output is None:
            logger.error(f"Lệnh 'show mac address-table' trả về None cho {ip}")
            gui_queue.put(("log", f"LỖI: Không lấy được bảng MAC từ {ip} (Lệnh trả về None)"))
            return None
        return output
    except Exception as e:
        logger.exception(f"Không lấy được bảng MAC từ {ip}")
        gui_queue.put(("log", f"LỖI: Không lấy được bảng MAC từ {ip}: {e}"))
        return None

def parse_mac_table(mac_table_output: str) -> List[Dict[str, str]]:
    entries = []
    if not mac_table_output:
        return entries
    for match in MAC_TABLE_RE.finditer(mac_table_output):
        try:
            entry_data = {k: v.strip().lower() for k, v in match.groupdict().items()}
            if not entry_data.get('vlan') or not entry_data.get('mac') or not entry_data.get('port'):
                logger.warning(f"Bỏ qua mục MAC phân tích không đầy đủ: {match.group(0)}")
                continue
            entries.append(entry_data)
        except Exception as e:
            logger.error(f"Lỗi phân tích dòng bảng MAC: {match.group(0)} - {e}")
    return entries

def count_macs_on_port(parsed_mac_table: List[Dict[str, str]], target_port: str) -> int:
    target_port_lower = target_port.lower()
    return sum(1 for entry in parsed_mac_table if entry.get('port') == target_port_lower)

def find_mac_in_parsed_table(parsed_mac_table: List[Dict[str, str]], target_mac_cleaned: str) -> Optional[Tuple[str, str, int]]:
    target_mac_cisco = format_mac_cisco(target_mac_cleaned).lower()
    for entry in parsed_mac_table:
        if entry.get('mac') == target_mac_cisco:
            port = entry.get('port', 'Không xác định')
            vlan = entry.get('vlan', 'Không xác định')
            mac_count = count_macs_on_port(parsed_mac_table, port)
            return port, vlan, mac_count
    return None

def find_mac_last4_in_parsed_table(parsed_mac_table: List[Dict[str, str]], target_mac_last4: str) -> List[Tuple[str, str, str, int]]:
    target_mac_last4_lower = target_mac_last4.lower()
    found_entries = []
    for entry in parsed_mac_table:
        mac_cisco = entry.get('mac')
        if mac_cisco:
            mac_no_dots = mac_cisco.replace('.', '')
            if mac_no_dots.endswith(target_mac_last4_lower):
                port = entry.get('port', 'Không xác định')
                vlan = entry.get('vlan', 'Không xác định')
                mac_count = count_macs_on_port(parsed_mac_table, port)
                found_entries.append((mac_cisco, port, vlan, mac_count))
    return found_entries

def configure_vlan(connection: ConnectHandler, port: str, vlan: str) -> bool:
    ip = getattr(connection, 'host', 'IP không xác định')
    config_commands = [
        f"interface {port}",
        f"switchport access vlan {vlan}",
        "end"
    ]
    try:
        logger.info(f"Cấu hình VLAN {vlan} trên {port} @ {ip}")
        output = connection.send_config_set(config_commands, exit_config_mode=False)
        logger.debug(f"Kết quả cấu hình VLAN từ {ip} cho {port}: {output}")
        output_lower = output.lower() if output else ""
        if "error" in output_lower or "invalid" in output_lower or "exceeded" in output_lower or "%" in output:
            logger.error(f"Có thể xảy ra lỗi khi cấu hình VLAN {vlan} trên {port} @ {ip}. Kết quả: {output}")
            gui_queue.put(("log", f"CẢNH BÁO: Có thể xảy ra lỗi khi cấu hình VLAN {vlan} trên {port} @ {ip}. Kết quả: {output}"))
        gui_queue.put(("log", f"Đã đặt VLAN {vlan} trên {port} @ {ip}"))
        return True
    except Exception as e:
        logger.exception(f"Không đặt được VLAN {vlan} trên {port} @ {ip}")
        gui_queue.put(("log", f"LỖI: Không đặt được VLAN {vlan} trên {port} @ {ip}: {e}"))
        return False

def save_configuration(connection: ConnectHandler) -> bool:
    ip = getattr(connection, 'host', 'IP không xác định')
    try:
        if not connection.is_alive():
            logger.error(f"Kết nối Telnet đến {ip} không còn hoạt động trước khi lưu cấu hình.")
            gui_queue.put(("log", f"LỖI: Kết nối Telnet đến {ip} đã ngắt trước khi lưu cấu hình."))
            return False

        logger.info(f"Đang thử lưu cấu hình trên {ip} qua Telnet...")
        output = connection.send_command_timing(
            "write memory",
            delay_factor=4,
            strip_prompt=False,
            strip_command=False
        )
        logger.debug(f"Kết quả lệnh 'write memory' từ {ip}: {output}")

        output_lower = output.lower() if output else ""
        success_keywords = ["ok", "[ok]", "building configuration", "configuration saved", "written to memory"]
        if any(keyword in output_lower for keyword in success_keywords):
            logger.info(f"Cấu hình được lưu thành công trên {ip}")
            gui_queue.put(("log", f"Đã lưu cấu hình thành công trên {ip}"))
            return True

        if "confirm" in output_lower or "destination filename" in output_lower:
            logger.info(f"Phát hiện yêu cầu xác nhận khi lưu cấu hình trên {ip}. Gửi Enter.")
            output_confirm = connection.send_command_timing("\n", delay_factor=4)
            logger.debug(f"Kết quả xác nhận từ {ip}: {output_confirm}")
            output_confirm_lower = output_confirm.lower() if output_confirm else ""
            if any(keyword in output_confirm_lower for keyword in success_keywords):
                logger.info(f"Cấu hình được lưu thành công trên {ip} sau khi xác nhận")
                gui_queue.put(("log", f"Đã lưu cấu hình thành công trên {ip} sau khi xác nhận"))
                return True
            else:
                logger.warning(f"Không xác nhận được việc lưu cấu hình trên {ip} sau khi gửi Enter. Kết quả: {output_confirm}")
                gui_queue.put(("log", f"CẢNH BÁO: Lưu cấu hình trên {ip} không xác nhận được sau khi gửi Enter. Kết quả: {output_confirm}"))
                return False

        logger.warning(f"Lưu cấu hình trên {ip} không tìm thấy xác nhận thành công. Kết quả: {output}")
        gui_queue.put(("log", f"CẢNH BÁO: Lưu cấu hình trên {ip} không xác nhận được. Kết quả: {output}"))
        return False

    except Exception as e:
        logger.exception(f"Lỗi khi lưu cấu hình trên {ip}: {str(e)}")
        gui_queue.put(("log", f"LỖI: Không lưu được cấu hình trên {ip}: {str(e)}"))
        return False

def process_switch_enable_ho(ip: str, username: str, password: str) -> None:
    connection = None
    try:
        connection, status_msg = connect_to_device(ip, username, password)
        gui_queue.put(("log", status_msg))
        if connection is None:
            return

        logger.info(f"Đã kết nối Telnet đến switch {ip}")
        logger.info(f"Đang xóa port-security trên {ip}...")
        gui_queue.put(("log", f"Đang xóa port-security trên {ip}..."))
        try:
            connection.send_command_timing("clear port-security all", delay_factor=2)
            gui_queue.put(("log", f"Đã gửi lệnh xóa port-security đến {ip}"))
        except Exception as cmd_err:
            logger.error(f"Lỗi khi gửi lệnh 'clear port-security all' đến {ip}: {cmd_err}")
            gui_queue.put(("log", f"LỖI khi gửi lệnh 'clear port-security all' đến {ip}: {cmd_err}"))
            return

        logger.info(f"Đang kiểm tra các cổng bị vô hiệu hóa trên {ip}...")
        gui_queue.put(("log", f"Đang kiểm tra các cổng bị vô hiệu hóa trên {ip}..."))
        output = None
        try:
            output = connection.send_command_timing("show int status", delay_factor=2)
        except Exception as cmd_err:
            logger.error(f"Lỗi khi gửi lệnh 'show int status' đến {ip}: {cmd_err}")
            gui_queue.put(("log", f"LỖI khi gửi lệnh 'show int status' đến {ip}: {cmd_err}"))
            return

        if not output:
            logger.error(f"Không nhận được đầu ra từ lệnh 'show int status' trên {ip}")
            gui_queue.put(("log", f"LỖI: Không nhận được đầu ra từ lệnh 'show int status' trên {ip}"))
            return

        disabled_ports = []
        lines = output.splitlines()
        for line in lines:
            line_lower = line.lower()
            if ("gi" in line_lower or "fa" in line_lower or "te" in line_lower) and "disabled" in line_lower:
                parts = line.split()
                if parts:
                    port_id = parts[0]
                    if re.match(r'^(Gi|Fa|Te|Eth)\d+([/\d.]*)?$', port_id, re.IGNORECASE):
                        port_name_desc = " ".join(parts[1:-2]).lower()
                        if "loop" not in port_name_desc:
                            disabled_ports.append(port_id)
                        else:
                            logger.info(f"Bỏ qua cổng {port_id} vì mô tả/tên chứa 'loop': '{port_name_desc}'")
                            gui_queue.put(("log", f"INFO: Bỏ qua cổng {port_id} vì mô tả/tên chứa 'loop': '{port_name_desc}'"))
                    else:
                        logger.debug(f"Dòng khớp 'disabled' nhưng phần tử đầu tiên '{parts[0]}' không giống ID cổng: {line}")

        logger.info(f"Tìm thấy {len(disabled_ports)} cổng bị vô hiệu hóa cần kích hoạt trên {ip}: {disabled_ports}")
        gui_queue.put(("log", f"Tìm thấy {len(disabled_ports)} cổng bị vô hiệu hóa cần kích hoạt trên {ip}: {disabled_ports}"))

        if disabled_ports:
            logger.info(f"Đang kích hoạt các cổng trên {ip}...")
            gui_queue.put(("log", f"Đang kích hoạt các cổng trên {ip}..."))
            config_commands = []
            for port in disabled_ports:
                config_commands.extend([
                    f"interface {port}",
                    "shutdown",
                    "no shutdown"
                ])

            try:
                config_output = connection.send_config_set(config_commands)
                logger.debug(f"Kết quả kích hoạt cổng trên {ip}: {config_output}")
                for port in disabled_ports:
                    logger.info(f"Đã gửi lệnh kích hoạt cho cổng {port} trên {ip}")
                    gui_queue.put(("log", f"Đã gửi lệnh kích hoạt cho cổng {port} trên {ip}"))
            except Exception as config_err:
                logger.error(f"Lỗi khi gửi lệnh cấu hình kích hoạt cổng đến {ip}: {config_err}")
                gui_queue.put(("log", f"LỖI khi gửi lệnh kích hoạt cổng đến {ip}: {config_err}"))
                return

        else:
            logger.info(f"Không có cổng nào cần kích hoạt trên {ip}")
            gui_queue.put(("log", f"Không có cổng nào cần kích hoạt trên {ip}"))

        if disabled_ports:
            gui_queue.put(("log", f"Đang lưu cấu hình trên {ip} sau khi kích hoạt cổng..."))
            save_success = save_configuration(connection)
            if not save_success:
                gui_queue.put(("messagebox", ("warning", f"Không lưu được cấu hình trên {ip} sau khi kích hoạt cổng. Vui lòng kiểm tra thiết bị.")))
        else:
            gui_queue.put(("log", f"Không có thay đổi nào được thực hiện trên {ip}, bỏ qua lưu cấu hình."))

    except Exception as e:
        logger.exception(f"Lỗi không mong muốn khi xử lý enable_ho cho {ip}: {str(e)}")
        gui_queue.put(("log", f"LỖI NGHIÊM TRỌNG khi xử lý {ip} (enable_ho): {str(e)}"))
    finally:
        if connection:
            disconnect_device(connection, ip)

def find_ports_in_vlan(parsed_mac_table: List[Dict[str, str]], source_vlan: str) -> List[str]:
    source_vlan_lower = source_vlan.lower()
    ports = set()
    for entry in parsed_mac_table:
        if entry.get('vlan') == source_vlan_lower:
            port = entry.get('port')
            if port:
                ports.add(port)
    return sorted(list(ports))

def task_worker(task_details: Dict[str, Any]):
    mode = task_details.get("mode")
    username = task_details.get("username")
    password = task_details.get("password")
    start_ip = task_details.get("start_ip")
    end_ip = task_details.get("end_ip")
    target_vlan = task_details.get("target_vlan")
    source_vlan = task_details.get("source_vlan")
    mac_list_raw = task_details.get("mac_list", [])

    if not all([mode, username, password, start_ip, end_ip]):
        gui_queue.put(("log", "LỖI: Luồng xử lý bắt đầu với thông tin cần thiết bị thiếu."))
        gui_queue.put(("status", "Lỗi: Thiết lập tác vụ nội bộ"))
        gui_queue.put(("messagebox", ("error", "Lỗi nội bộ: Thiếu thông tin tác vụ.")))
        gui_queue.put(("progress", (1, 1)))
        gui_queue.put(("enable_button", mode))
        return

    start_time = time.time()
    thread_name = threading.current_thread().name
    logger.info(f"[{thread_name}] Luồng xử lý bắt đầu cho chế độ: {mode}")
    gui_queue.put(("status", f"Đang khởi động: {mode}..."))
    gui_queue.put(("progress", (0, 1)))

    ips_to_scan, ip_error = generate_switch_ips(start_ip, end_ip)

    if ip_error:
        logger.error(f"[{thread_name}] Tạo danh sách IP thất bại: {ip_error}")
        gui_queue.put(("log", f"LỖI: {ip_error}"))
        gui_queue.put(("messagebox", ("error", ip_error)))
        gui_queue.put(("status", "Lỗi khi tạo danh sách IP"))
        gui_queue.put(("progress", (1, 1)))
        gui_queue.put(("enable_button", mode))
        return

    total_ips = len(ips_to_scan)
    gui_queue.put(("log", f"Đã tạo {total_ips} IP để quét: {ips_to_scan[0]}...{ips_to_scan[-1]}"))
    gui_queue.put(("progress", (0, total_ips)))

    if mode == "enable_ho":
        processed_ip_count = 0
        for ip in ips_to_scan:
            processed_ip_count += 1
            gui_queue.put(("status", f"Đang xử lý {ip} ({processed_ip_count}/{total_ips})..."))
            gui_queue.put(("progress", (processed_ip_count, total_ips)))
            process_switch_enable_ho(ip, username, password)

        end_time = time.time()
        duration = end_time - start_time
        gui_queue.put(("log", f"\n--- Hoàn thành tác vụ: {mode} (Thời gian: {duration:.2f} giây) ---"))
        gui_queue.put(("status", f"{mode} đã hoàn thành"))
        gui_queue.put(("messagebox", ("info", f"Tác vụ {mode} hoàn thành trong {duration:.2f} giây. Kiểm tra nhật ký chi tiết.")))
        gui_queue.put(("progress", (total_ips, total_ips)))
        gui_queue.put(("enable_button", mode))
        logger.info(f"[{thread_name}] Luồng xử lý hoàn thành cho chế độ: {mode}. Thời gian: {duration:.2f}s")
        return

    elif mode == "vlan_switch":
        processed_ip_count = 0
        switches_needing_save = set()
        connection: Optional[ConnectHandler] = None

        if not source_vlan or not target_vlan:
            gui_queue.put(("log", "LỖI: Thiếu VLAN nguồn hoặc VLAN đích."))
            gui_queue.put(("messagebox", ("error", "VLAN nguồn và VLAN đích là bắt buộc.")))
            gui_queue.put(("status", "Lỗi: Thiếu thông tin VLAN"))
            gui_queue.put(("progress", (1, 1)))
            gui_queue.put(("enable_button", mode))
            return

        gui_queue.put(("log", f"Đang tìm các cổng trong VLAN {source_vlan} để chuyển sang VLAN {target_vlan}"))

        for ip in ips_to_scan:
            processed_ip_count += 1
            gui_queue.put(("status", f"Đang xử lý {ip} ({processed_ip_count}/{total_ips})..."))
            gui_queue.put(("progress", (processed_ip_count, total_ips)))

            connection, status_msg = connect_to_device(ip, username, password)
            gui_queue.put(("log", status_msg))

            if connection is None:
                continue

            try:
                mac_table_str = get_mac_address_table(connection)
                if mac_table_str is None:
                    continue

                parsed_mac_table = parse_mac_table(mac_table_str)
                if not parsed_mac_table:
                    gui_queue.put(("log", f"THÔNG TIN: Không tìm thấy hoặc phân tích được mục MAC nào trong bảng cho {ip}."))
                    continue

                ports_in_source_vlan = find_ports_in_vlan(parsed_mac_table, source_vlan)
                if not ports_in_source_vlan:
                    gui_queue.put(("log", f"THÔNG TIN: Không tìm thấy cổng nào trong VLAN {source_vlan} trên {ip}."))
                    continue

                gui_queue.put(("log", f"    Tìm thấy {len(ports_in_source_vlan)} cổng trong VLAN {source_vlan} trên {ip}: {', '.join(ports_in_source_vlan)}"))
                changes_made_on_this_switch = False

                for port in ports_in_source_vlan:
                    gui_queue.put(("log", f"    Đang thử chuyển cổng {port} từ VLAN {source_vlan} sang VLAN {target_vlan}..."))
                    if configure_vlan(connection, port, target_vlan):
                        changes_made_on_this_switch = True

                if changes_made_on_this_switch:
                    switches_needing_save.add(ip)
                    gui_queue.put(("log", f"--- Switch {ip} được đánh dấu để lưu cấu hình ---"))

            except Exception as e:
                logger.exception(f"[{thread_name}] Lỗi không xác định khi xử lý switch {ip} (vlan_switch)")
                gui_queue.put(("log", f"LỖI NGHIÊM TRỌNG khi xử lý {ip} (vlan_switch): {e}"))
            finally:
                disconnect_device(connection, ip)
                connection = None

        if switches_needing_save:
            gui_queue.put(("log", "\n--- Đang lưu cấu hình cho các switch đã thay đổi ---"))
            gui_queue.put(("status", "Đang lưu cấu hình..."))
            save_count = 0
            total_saves = len(switches_needing_save)
            gui_queue.put(("progress", (0, total_saves)))

            sorted_ips_to_save = sorted(list(switches_needing_save))
            for ip_to_save in sorted_ips_to_save:
                save_count += 1
                gui_queue.put(("status", f"Đang lưu cấu hình trên {ip_to_save} ({save_count}/{total_saves})..."))
                gui_queue.put(("progress", (save_count, total_saves)))

                save_conn, status_msg = connect_to_device(ip_to_save, username, password)
                gui_queue.put(("log", status_msg))
                if save_conn:
                    save_success = save_configuration(save_conn)
                    disconnect_device(save_conn, ip_to_save)
                    if not save_success:
                        gui_queue.put(("messagebox", ("warning", f"Không lưu được cấu hình trên {ip_to_save}. Vui lòng kiểm tra thiết bị thủ công và nhật ký.")))
                else:
                    gui_queue.put(("log", f"LỖI: Không thể kết nối lại với {ip_to_save} để lưu cấu hình."))
                    gui_queue.put(("messagebox", ("error", f"Không thể kết nối lại với {ip_to_save} để lưu cấu hình. Vui lòng lưu thủ công!")))
            gui_queue.put(("progress", (total_saves, total_saves)))
        else:
            gui_queue.put(("log", "\n--- Không có switch nào cần lưu cấu hình ---"))

        end_time = time.time()
        duration = end_time - start_time
        gui_queue.put(("log", f"\n--- Hoàn thành tác vụ: {mode} (Thời gian: {duration:.2f} giây) ---"))
        gui_queue.put(("status", f"{mode} đã hoàn thành"))
        gui_queue.put(("messagebox", ("info", f"Tác vụ {mode} hoàn thành trong {duration:.2f} giây. Kiểm tra nhật ký chi tiết.")))
        gui_queue.put(("progress", (1, 1)))
        gui_queue.put(("enable_button", mode))
        logger.info(f"[{thread_name}] Luồng xử lý hoàn thành cho chế độ: {mode}. Thời gian: {duration:.2f}s")
        return

    pending_macs = set()
    original_mac_map = {}
    valid_mac_found = False
    for raw_mac in mac_list_raw:
        if not raw_mac:
            continue

        if mode == "full_mac_config":
            cleaned = clean_mac(raw_mac)
            if cleaned:
                pending_macs.add(cleaned)
                original_mac_map[cleaned] = raw_mac
                valid_mac_found = True
            else:
                gui_queue.put(("log", f"CẢNH BÁO: Bỏ qua định dạng MAC đầy đủ không hợp lệ: '{raw_mac}'"))
        elif mode in ["last4_config", "mac_search"]:
            last4 = raw_mac.strip().lower()
            if VALID_MAC_LAST4_RE.match(last4):
                pending_macs.add(last4)
                original_mac_map[last4] = raw_mac
                valid_mac_found = True
            else:
                gui_queue.put(("log", f"CẢNH BÁO: Bỏ qua định dạng 4 ký tự cuối MAC không hợp lệ: '{raw_mac}'"))

    if not valid_mac_found and mac_list_raw:
        error_msg = "Không tìm thấy địa chỉ MAC hoặc 4 ký tự cuối hợp lệ trong danh sách đầu vào."
        logger.error(f"[{thread_name}] {error_msg}")
        gui_queue.put(("log", f"LỖI: {error_msg}"))
        gui_queue.put(("messagebox", ("error", error_msg)))
        gui_queue.put(("status", "Lỗi: Không có MAC/4 ký tự cuối hợp lệ"))
        gui_queue.put(("progress", (1, 1)))
        gui_queue.put(("enable_button", mode))
        return
    elif not mac_list_raw and mode != "vlan_switch" and mode != "enable_ho":
        error_msg = f"Danh sách địa chỉ MAC hoặc 4 ký tự cuối là bắt buộc cho chế độ '{mode}' nhưng đang trống."
        logger.error(f"[{thread_name}] {error_msg}")
        gui_queue.put(("log", f"LỖI: {error_msg}"))
        gui_queue.put(("messagebox", ("error", error_msg)))
        gui_queue.put(("status", "Lỗi: Danh sách MAC/4 ký tự cuối trống"))
        gui_queue.put(("progress", (1, 1)))
        gui_queue.put(("enable_button", mode))
        return

    gui_queue.put(("log", f"Đang xử lý {len(pending_macs)} MAC/4 ký tự cuối hợp lệ duy nhất."))
    if pending_macs:
        gui_queue.put(("log", f"Mục tiêu: {list(original_mac_map[p] for p in pending_macs)}"))

    processed_results = []
    switches_needing_save = set()
    connection: Optional[ConnectHandler] = None
    processed_ip_count = 0

    for ip in ips_to_scan:
        processed_ip_count += 1
        gui_queue.put(("status", f"Đang xử lý {ip} ({processed_ip_count}/{total_ips})..."))
        gui_queue.put(("progress", (processed_ip_count, total_ips)))

        if not pending_macs:
            gui_queue.put(("log", f"Đã xử lý tất cả MAC/4 ký tự cuối mục tiêu. Dừng quét tại {ip}."))
            logger.info(f"[{thread_name}] Đã xử lý tất cả MAC/4 ký tự cuối mục tiêu. Dừng quét.")
            break

        connection, status_msg = connect_to_device(ip, username, password)
        gui_queue.put(("log", status_msg))

        if connection is None:
            continue

        try:
            mac_table_str = get_mac_address_table(connection)
            if mac_table_str is None:
                continue

            parsed_mac_table = parse_mac_table(mac_table_str)
            if not parsed_mac_table:
                gui_queue.put(("log", f"THÔNG TIN: Không tìm thấy hoặc phân tích được mục MAC nào trong bảng cho {ip}."))
                continue

            changes_made_on_this_switch = False
            macs_found_on_this_switch = set()

            for mac_key in list(pending_macs):
                original_input_mac = original_mac_map.get(mac_key, mac_key)
                gui_queue.put(("log", f"  Đang kiểm tra '{original_input_mac}' trên {ip}..."))

                found_port, found_vlan, found_mac_count = None, None, None
                found_full_mac_cisco = None

                if mode == "full_mac_config":
                    result = find_mac_in_parsed_table(parsed_mac_table, mac_key)
                    if result:
                        found_port, found_vlan, found_mac_count = result
                        found_full_mac_cisco = format_mac_cisco(mac_key)
                        gui_queue.put(("log", f"    Tìm thấy {found_full_mac_cisco}: Cổng={found_port}, VLAN={found_vlan}, Số MAC trên cổng={found_mac_count}"))
                        macs_found_on_this_switch.add(mac_key)

                elif mode in ["last4_config", "mac_search"]:
                    matches = find_mac_last4_in_parsed_table(parsed_mac_table, mac_key)
                    if matches:
                        gui_queue.put(("log", f"    Tìm thấy {len(matches)} kết quả khớp cho *{original_input_mac} trên {ip}:"))
                        best_candidate = None
                        valid_match_found = False  # For mac_search mode

                        for f_mac, f_port, f_vlan, f_count in matches:
                            if mode == "mac_search" and f_count > MAX_MAC_COUNT_SEARCH:
                                gui_queue.put(("log", f"      - MAC: {f_mac}, Cổng={f_port}, VLAN={f_vlan}, Số MAC trên cổng={f_count} (BỎ QUA: Quá nhiều MAC)"))
                                continue

                            gui_queue.put(("log", f"      - MAC: {f_mac}, Cổng={f_port}, VLAN={f_vlan}, Số MAC trên cổng={f_count}"))

                            if mode == "mac_search":
                                details = f"MAC={f_mac}, Cổng={f_port}, VLAN={f_vlan}, Số MAC trên cổng={f_count}"
                                processed_results.append((ip, original_input_mac, "Đã tìm thấy", details))
                                valid_match_found = True
                            elif mode == "last4_config":
                                if f_count < 4 and f_vlan.isdigit() and best_candidate is None:
                                    best_candidate = (f_port, f_vlan, f_count, f_mac)
                                    gui_queue.put(("log", f"      -> Chọn ứng viên: {f_mac} trên cổng {f_port} (Số MAC: {f_count}, VLAN: {f_vlan})"))
                                elif best_candidate:
                                    gui_queue.put(("log", f"      -> Bỏ qua ứng viên khác: {f_mac} (đã chọn ứng viên)"))

                        if mode == "last4_config":
                            if best_candidate:
                                found_port, found_vlan, found_mac_count, found_full_mac_cisco = best_candidate
                                macs_found_on_this_switch.add(mac_key)
                            else:
                                gui_queue.put(("log", f"    Không tìm thấy ứng viên phù hợp (ít hơn 4 MAC, VLAN số) cho *{original_input_mac} để cấu hình VLAN."))
                                processed_results.append((ip, original_input_mac, "Không có ứng viên phù hợp", "Không có cổng nào có < 4 MAC và VLAN số"))
                        elif mode == "mac_search" and valid_match_found:
                            macs_found_on_this_switch.add(mac_key)

                if mode in ["full_mac_config", "last4_config"] and found_port:
                    if not target_vlan:
                        gui_queue.put(("log", f"    LỖI NỘI BỘ: Thiếu VLAN đích khi cố gắng cấu hình cho {original_input_mac}"))
                        continue

                    if not found_vlan.isdigit():
                        details = f"VLAN hiện tại không phải số ('{found_vlan}') trên cổng {found_port} cho MAC {found_full_mac_cisco}"
                        gui_queue.put(("log", f"    BỎ QUA: {details}"))
                        processed_results.append((ip, original_input_mac, "Bỏ qua (VLAN không hợp lệ)", details))
                        continue

                    if found_mac_count < 4:
                        if found_vlan == target_vlan:
                            details = f"Đã ở VLAN mục tiêu {target_vlan} trên cổng {found_port} (MAC: {found_full_mac_cisco}, Số MAC trên cổng: {found_mac_count})"
                            gui_queue.put(("log", f"    THÔNG TIN: {details}"))
                            processed_results.append((ip, original_input_mac, "Đã đúng VLAN", details))
                        else:
                            gui_queue.put(("log", f"    Đang thử chuyển VLAN: {found_full_mac_cisco} từ {found_vlan} -> {target_vlan} trên cổng {found_port}"))
                            if configure_vlan(connection, found_port, target_vlan):
                                details = f"Đã chuyển sang VLAN {target_vlan} trên cổng {found_port} (MAC: {found_full_mac_cisco}, VLAN cũ: {found_vlan}, Số MAC trên cổng: {found_mac_count})"
                                processed_results.append((ip, original_input_mac, "Đã chuyển VLAN", details))
                                changes_made_on_this_switch = True
                            else:
                                details = f"Không chuyển được sang VLAN {target_vlan} trên cổng {found_port} (MAC: {found_full_mac_cisco}, từ VLAN {found_vlan})"
                                processed_results.append((ip, original_input_mac, "Chuyển VLAN thất bại", details))
                    else:
                        details = f"Cổng {found_port} có {found_mac_count} MAC (>= 4) cho {found_full_mac_cisco}. Bỏ qua."
                        gui_queue.put(("log", f"    BỎ QUA: {details}"))
                        processed_results.append((ip, original_input_mac, "Bỏ qua (Cổng >=4 MACs)", details))
                elif mac_key not in macs_found_on_this_switch and mode != "mac_search":
                    gui_queue.put(("log", f"    Không tìm thấy '{original_input_mac}' trên {ip}."))

            pending_macs -= macs_found_on_this_switch

            if changes_made_on_this_switch:
                switches_needing_save.add(ip)
                gui_queue.put(("log", f"--- Switch {ip} được đánh dấu để lưu cấu hình ---"))

        except Exception as e:
            logger.exception(f"[{thread_name}] Lỗi không xác định khi xử lý switch {ip} (MAC modes)")
            gui_queue.put(("log", f"LỖI NGHIÊM TRỌNG khi xử lý {ip} (MAC modes): {e}"))
        finally:
            disconnect_device(connection, ip)
            connection = None

    if switches_needing_save:
        gui_queue.put(("log", "\n--- Đang lưu cấu hình cho các switch đã thay đổi ---"))
        gui_queue.put(("status", "Đang lưu cấu hình..."))
        save_count = 0
        total_saves = len(switches_needing_save)
        gui_queue.put(("progress", (0, total_saves)))

        sorted_ips_to_save = sorted(list(switches_needing_save))
        for ip_to_save in sorted_ips_to_save:
            save_count += 1
            gui_queue.put(("status", f"Đang lưu cấu hình trên {ip_to_save} ({save_count}/{total_saves})..."))
            gui_queue.put(("progress", (save_count, total_saves)))

            save_conn, status_msg = connect_to_device(ip_to_save, username, password)
            gui_queue.put(("log", status_msg))
            if save_conn:
                save_success = save_configuration(save_conn)
                disconnect_device(save_conn, ip_to_save)
                if not save_success:
                    gui_queue.put(("messagebox", ("warning", f"Không lưu được cấu hình trên {ip_to_save}. Vui lòng kiểm tra thiết bị thủ công và nhật ký.")))
            else:
                gui_queue.put(("log", f"LỖI: Không thể kết nối lại với {ip_to_save} để lưu cấu hình."))
                gui_queue.put(("messagebox", ("error", f"Không thể kết nối lại với {ip_to_save} để lưu cấu hình. Vui lòng lưu thủ công!")))
        gui_queue.put(("progress", (total_saves, total_saves)))
    elif mode in ["full_mac_config", "last4_config"]:
        gui_queue.put(("log", "\n--- Không có switch nào cần lưu cấu hình ---"))

    end_time = time.time()
    duration = end_time - start_time
    gui_queue.put(("log", f"\n--- Hoàn thành tác vụ: {mode} (Thời gian: {duration:.2f} giây) ---"))
    final_status = f"{mode} đã hoàn thành."

    gui_queue.put(("log", "--- Tóm tắt kết quả ---"))
    if processed_results:
        summary_by_mac = {}
        for ip, orig_mac, status, details in processed_results:
            if orig_mac not in summary_by_mac:
                summary_by_mac[orig_mac] = []
            summary_by_mac[orig_mac].append(f"  - Trên {ip}: Trạng thái='{status}', Chi tiết='{details}'")

        for orig_mac in sorted(summary_by_mac.keys()):
            gui_queue.put(("log", f"Mục tiêu: {orig_mac}"))
            for result_line in summary_by_mac[orig_mac]:
                gui_queue.put(("log", result_line))
    else:
        gui_queue.put(("log", "(Không có kết quả xử lý MAC/4 ký tự cuối cụ thể để hiển thị - có thể do lỗi kết nối hoặc không tìm thấy)"))

    if pending_macs:
        gui_queue.put(("log", "\n--- Các MAC/4 ký tự cuối KHÔNG tìm thấy hoặc KHÔNG thể xử lý ---"))
        unfound_originals = sorted([original_mac_map.get(p, p) for p in pending_macs])
        for mac_orig in unfound_originals:
            gui_queue.put(("log", f"- {mac_orig}"))
        final_status += f" ({len(pending_macs)} mục chưa tìm thấy/xử lý)"
    elif mode != "vlan_switch" and mode != "enable_ho":
        gui_queue.put(("log", "\n(Tất cả MAC/4 ký tự cuối đã được tìm thấy hoặc không thể xử lý)"))
        final_status += " (Tất cả mục đã xử lý)"

    gui_queue.put(("status", final_status))
    gui_queue.put(("messagebox", ("info", f"Tác vụ {mode} hoàn thành trong {duration:.2f} giây. Kiểm tra nhật ký chi tiết.")))
    gui_queue.put(("progress", (1, 1)))
    gui_queue.put(("enable_button", mode))
    logger.info(f"[{thread_name}] Luồng xử lý hoàn thành cho chế độ: {mode}. Thời gian: {duration:.2f}s")

class SwitchManagerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION} - {AUTHOR}")
        self.root.geometry("950x750")
        self.root.minsize(800, 650)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.active_thread: Optional[threading.Thread] = None
        self.buttons: Dict[str, tk.Widget] = {}
        self.current_output_widget: Optional[scrolledtext.ScrolledText] = None
        self.current_active_button_mode: Optional[str] = None
        self.tab_widgets: Dict[str, Dict[str, Any]] = {}
        self.original_button_texts: Dict[str, str] = {}
        self.entry_username: Optional[tk.Entry] = None
        self.entry_password: Optional[tk.Entry] = None
        self.entry_start_ip: Optional[tk.Entry] = None
        self.entry_end_ip: Optional[tk.Entry] = None

        self._configure_styles()
        self._create_widgets()
        self.check_queue()

        logger.info(f"Ứng dụng đã khởi động: {APP_NAME} v{APP_VERSION}")
        gui_queue.put(("log", f"--- {APP_NAME} v{APP_VERSION} ---"))
        gui_queue.put(("log", "Sẵn sàng nhận lệnh. Chọn tab và điền thông tin."))

    def _configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.colors = {
            "primary": "#DB7093",
            "secondary": "#FF69B4",
            "light_bg": "#FFF0F5",
            "dark_bg": "#4B0082",
            "text_light": "#FFFFFF",
            "text_dark": "#363636",
            "text_accent": "#FFB6C1",
            "entry_bg": "#FFFFFF",
            "disabled_bg": "#D3D3D3",
            "disabled_fg": "#A9A9A9",
            "error": "#D32F2F",
            "warning": "#FFA000",
            "success": "#388E3C"
        }

        self.root.configure(bg=self.colors["light_bg"])

        self.style.configure('TFrame', background=self.colors["light_bg"])
        self.style.configure('TLabel', background=self.colors["light_bg"], foreground=self.colors["text_dark"], font=('Arial', 10))
        self.style.configure('Header.TFrame', background=self.colors["primary"])
        self.style.configure('Header.TLabel', background=self.colors["primary"], foreground=self.colors["text_light"])
        self.style.configure('Author.TLabel', background=self.colors["primary"], foreground=self.colors["text_light"], font=('Arial', 9))
        self.style.configure('Status.TFrame', background=self.colors["primary"])
        self.style.configure('Status.TLabel', background=self.colors["primary"], foreground=self.colors["text_light"], font=('Arial', 9))

        self.style.configure('TNotebook', background=self.colors["light_bg"], borderwidth=1)
        self.style.configure('TNotebook.Tab', padding=[12, 6], font=('Arial', 10, 'bold'))
        self.style.map('TNotebook.Tab',
                       background=[('selected', self.colors["primary"]), ('!selected', self.colors["dark_bg"])],
                       foreground=[('selected', self.colors["text_light"]), ('!selected', self.colors["text_accent"])])

        self.style.configure('TLabelframe', background=self.colors["light_bg"], borderwidth=1, relief="groove")
        self.style.configure('TLabelframe.Label', background=self.colors["light_bg"], foreground=self.colors["primary"], font=('Arial', 10, 'bold'))
        self.style.configure('Horizontal.TProgressbar', troughcolor=self.colors["dark_bg"], bordercolor=self.colors["primary"], background=self.colors["secondary"], thickness=15)

        self.button_font = ('Arial', 10, 'bold')
        self.entry_font = ('Consolas', 10)
        self.stext_font = ('Consolas', 9)
        self.entry_bg = self.colors["entry_bg"]
        self.entry_fg = self.colors["text_dark"]
        self.stext_bg = self.colors["entry_bg"]
        self.stext_fg = self.colors["text_dark"]

    def _create_widgets(self):
        header = ttk.Frame(self.root, style='Header.TFrame', padding=0)
        header.pack(fill='x', side='top', pady=(0, 5))

        ttk.Label(header, text=APP_NAME, style='Header.TLabel', font=('Arial', 16, 'bold'), padding=(10,5,10,5)).pack(side='left')
        ttk.Label(header, text=f"By {AUTHOR}", style='Author.TLabel', padding=(10,5,10,5)).pack(side='right')
        doc_button = tk.Button(header, text="Hướng Dẫn", command=self.open_documentation,
                               bg=self.colors["primary"], fg=self.colors["text_light"], relief='flat',
                               font=('Arial', 9, 'underline'), activebackground=self.colors["secondary"], bd=0, cursor="hand2")
        doc_button.pack(side='right', padx=5)

        common_frame = ttk.LabelFrame(self.root, text="Cài Đặt Chung", padding=10)
        common_frame.pack(fill='x', padx=10, pady=(0, 10))

        common_frame.columnconfigure(1, weight=1)
        common_frame.columnconfigure(3, weight=1)

        self.entry_username = self._create_label_entry_grid(common_frame, "Tên người dùng:", 0, 0)
        self.entry_password = self._create_label_entry_grid(common_frame, "Mật khẩu:", 1, 0, is_password=True)
        self.entry_start_ip = self._create_label_entry_grid(common_frame, "IP bắt đầu:", 0, 2)
        self.entry_end_ip = self._create_label_entry_grid(common_frame, "IP kết thúc:", 1, 2)

        self.notebook = ttk.Notebook(self.root, style='TNotebook')
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(0, 0))

        self.tab_widgets['full_mac_config'] = self._create_tab("VLAN theo MAC Đầy Đủ", self.notebook, mode="full_mac_config", has_vlan=True, has_full_mac=True)
        self.tab_widgets['last4_config'] = self._create_tab("VLAN theo 4 Ký Tự Cuối", self.notebook, mode="last4_config", has_vlan=True, has_last4_mac=True)
        self.tab_widgets['mac_search'] = self._create_tab("Tìm Cổng theo MAC", self.notebook, mode="mac_search", has_last4_mac=True)
        self.tab_widgets['enable_ho'] = self._create_tab("Enable Port (HO)", self.notebook, mode="enable_ho")
        self.tab_widgets['vlan_switch'] = self._create_tab("Chuyển đổi VLAN", self.notebook, mode="vlan_switch", has_vlan=True, has_source_vlan=True)

        status_bar_frame = ttk.Frame(self.root, style='Status.TFrame', padding=0)
        status_bar_frame.pack(side='bottom', fill='x')

        self.status_var = tk.StringVar(value="Sẵn sàng")
        self.status_label = ttk.Label(status_bar_frame, textvariable=self.status_var, style='Status.TLabel', anchor='w', padding=(5,2))
        self.status_label.pack(side='left', fill='x', expand=True)

        self.progress_bar = ttk.Progressbar(status_bar_frame, orient='horizontal', length=200, mode='determinate', style='Horizontal.TProgressbar')
        self.progress_bar.pack(side='right', padx=5, pady=2)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.set_current_output_widget()

    def on_tab_change(self, event=None):
        self.set_current_output_widget()
        if self.current_output_widget and not self.current_output_widget.get("1.0", "1.end"):
            self.log_to_gui(f"--- {APP_NAME} v{APP_VERSION} ---", widget=self.current_output_widget)
            self.log_to_gui("Sẵn sàng.", widget=self.current_output_widget, clear_previous=False)

    def set_current_output_widget(self):
        try:
            current_tab_index = self.notebook.index(self.notebook.select())
            tab_keys = list(self.tab_widgets.keys())
            if 0 <= current_tab_index < len(tab_keys):
                tab_key = tab_keys[current_tab_index]
                self.current_output_widget = self.tab_widgets[tab_key].get('output')
                self.current_active_button_mode = self.tab_widgets[tab_key].get('mode')
                if self.current_output_widget and not self.current_output_widget.get("1.0", "1.end"):
                    self.log_to_gui(f"--- {APP_NAME} v{APP_VERSION} ---", widget=self.current_output_widget)
                    self.log_to_gui("Sẵn sàng.", widget=self.current_output_widget, clear_previous=False)
            else:
                logger.error(f"Index tab không hợp lệ: {current_tab_index}")
                self.current_output_widget = None
                self.current_active_button_mode = None

        except tk.TclError:
            logger.warning("Lỗi Tcl khi lấy tab hiện tại (có thể đang đóng cửa sổ)")
            self.current_output_widget = None
            self.current_active_button_mode = None
        except Exception as e:
            logger.error(f"Lỗi khi lấy widget output của tab hiện tại: {e}")
            self.current_output_widget = None
            self.current_active_button_mode = None

    def _create_tab(self, title: str, notebook: ttk.Notebook, mode: str,
                    has_vlan: bool = False, has_full_mac: bool = False, has_last4_mac: bool = False, has_source_vlan: bool = False) -> Dict[str, Any]:
        tab_frame = ttk.Frame(notebook, padding=10)
        notebook.add(tab_frame, text=title)

        widgets = {'mode': mode}

        input_outer_frame = ttk.Frame(tab_frame)
        input_outer_frame.pack(fill='x', pady=(0, 10))

        specific_input_frame = None
        if has_vlan or has_full_mac or has_last4_mac or has_source_vlan:
            specific_input_frame = ttk.LabelFrame(input_outer_frame, text="Thông Số Cụ Thể", padding=10)
            specific_input_frame.pack(side='left', fill='x', expand=True, padx=(0, 10))

            current_row = 0
            if has_source_vlan or has_vlan:
                vlan_frame = ttk.Frame(specific_input_frame)
                vlan_frame.grid(row=current_row, column=0, sticky='w', pady=(0, 10))
                vlan_col = 0
                if has_source_vlan:
                    widgets['source_vlan'] = self._create_label_entry_inline(vlan_frame, "VLAN Nguồn:", vlan_col, width=8)
                    vlan_col += 2
                if has_vlan:
                    widgets['target_vlan'] = self._create_label_entry_inline(vlan_frame, "VLAN Đích:", vlan_col, width=8)
                current_row += 1

            if has_full_mac or has_last4_mac:
                label_text = "Địa chỉ MAC đầy đủ (mỗi dòng một địa chỉ):" if has_full_mac else "4 Ký tự cuối MAC (mỗi dòng một giá trị):"
                widget_key = 'mac_full' if has_full_mac else 'mac_last4'
                widgets[widget_key] = self._create_mac_input(specific_input_frame, label_text, current_row, 0)
                current_row += 1

        button_text_map = {
            "full_mac_config": "Chuyển VLAN",
            "last4_config": "Chuyển VLAN",
            "mac_search": "Tìm Cổng",
            "enable_ho": "Kích Hoạt Cổng",
            "vlan_switch": "Chuyển Đổi VLAN"
        }
        button_text = button_text_map.get(mode, "Bắt Đầu")
        self.original_button_texts[mode] = button_text

        button_container = ttk.Frame(input_outer_frame)
        button_container.pack(side='right', anchor='center', padx=(10 if specific_input_frame else 0, 0))

        button = tk.Button(button_container, text=button_text,
                           command=lambda m=mode: self.start_task(m),
                           bg=self.colors["secondary"], fg=self.colors["text_light"],
                           font=self.button_font, padx=15, pady=8,
                           activebackground=self.colors["primary"], activeforeground=self.colors["text_light"],
                           relief="raised", borderwidth=2, state=tk.NORMAL,
                           disabledforeground=self.colors["disabled_fg"])
        button.pack(pady=10)
        self.buttons[mode] = button
        widgets['button'] = button

        output_frame = ttk.LabelFrame(tab_frame, text="Nhật Ký Đầu Ra", padding=5)
        output_frame.pack(fill='both', expand=True)
        output_text = scrolledtext.ScrolledText(output_frame, width=90, height=15,
                                                font=self.stext_font,
                                                bg=self.stext_bg, fg=self.stext_fg,
                                                wrap=tk.WORD, relief='solid', bd=1,
                                                state=tk.DISABLED)
        output_text.pack(fill='both', expand=True, padx=2, pady=2)
        widgets['output'] = output_text

        output_text.tag_configure("ERROR", foreground=self.colors["error"], font=(self.stext_font[0], self.stext_font[1], 'bold'))
        output_text.tag_configure("WARNING", foreground=self.colors["warning"])
        output_text.tag_configure("SUCCESS", foreground=self.colors["success"])
        output_text.tag_configure("INFO", foreground="#00008B")
        output_text.tag_configure("CMD", foreground="#8A2BE2")

        return widgets

    def _create_label_entry_grid(self, parent: tk.Widget, label_text: str, row: int, col: int,
                                 is_password: bool = False, width: int = 25, **kwargs) -> tk.Entry:
        sticky = kwargs.pop('sticky', 'w')
        padx = kwargs.pop('padx', (0, 15))
        pady = kwargs.pop('pady', (2, 5))
        ttk.Label(parent, text=label_text).grid(row=row, column=col, padx=(5, 2), pady=pady, sticky='e')
        entry = tk.Entry(parent, width=width, font=self.entry_font, bg=self.entry_bg, fg=self.entry_fg,
                         show="*" if is_password else "", relief='sunken', bd=1,
                         insertbackground=self.colors["text_dark"], **kwargs)
        entry.grid(row=row, column=col + 1, padx=padx, pady=pady, sticky=sticky + 'ew')
        parent.columnconfigure(col + 1, weight=1)
        return entry

    def _create_label_entry_inline(self, parent: tk.Widget, label_text: str, start_col: int, width: int = 10) -> tk.Entry:
        ttk.Label(parent, text=label_text).grid(row=0, column=start_col, padx=(5, 2), pady=2, sticky='w')
        entry = tk.Entry(parent, width=width, font=self.entry_font, bg=self.entry_bg, fg=self.entry_fg,
                         relief='sunken', bd=1, insertbackground=self.colors["text_dark"])
        entry.grid(row=0, column=start_col + 1, padx=(0, 10), pady=2, sticky='w')
        return entry

    def _create_mac_input(self, parent: tk.Widget, label_text: str, row: int, column: int) -> scrolledtext.ScrolledText:
        frame = ttk.LabelFrame(parent, text=label_text, padding=5)
        frame.grid(row=row, column=column, columnspan=2, padx=0, pady=5, sticky='nsew')
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(column, weight=1)

        stext = scrolledtext.ScrolledText(frame, width=45, height=6, font=self.entry_font,
                                          bg=self.stext_bg, fg=self.stext_fg, wrap=tk.WORD,
                                          relief='flat', bd=0, insertbackground=self.colors["text_dark"])
        stext.pack(fill='both', expand=True, padx=2, pady=2)
        return stext

    def open_documentation(self):
        try:
            logger.info(f"Đang mở URL tài liệu: {DOC_URL}")
            webbrowser.open(DOC_URL)
        except Exception as e:
            logger.error(f"Không thể mở trình duyệt cho tài liệu: {e}")
            messagebox.showerror("Lỗi", f"Không thể mở trình duyệt: {e}", parent=self.root)

    def log_to_gui(self, message: str, widget: Optional[scrolledtext.ScrolledText] = None, clear_previous: bool = False, level: str = "NORMAL"):
        log_widget = widget if widget else self.current_output_widget
        if log_widget and isinstance(log_widget, scrolledtext.ScrolledText):
            try:
                log_widget.config(state=tk.NORMAL)
                if clear_previous:
                    log_widget.delete(1.0, tk.END)

                tag_to_apply = None
                message_upper = message.upper()
                if level == "ERROR" or "LỖI" in message_upper or "FAIL" in message_upper or "THẤT BẠI" in message_upper:
                    tag_to_apply = "ERROR"
                elif level == "WARNING" or "CẢNH BÁO" in message_upper or "WARN" in message_upper:
                    tag_to_apply = "WARNING"
                elif level == "SUCCESS" or "THÀNH CÔNG" in message_upper or "ĐÃ LƯU" in message_upper or "ĐÃ CHUYỂN" in message_upper:
                    tag_to_apply = "SUCCESS"
                elif level == "INFO" or "THÔNG TIN" in message_upper or "ĐANG" in message_upper or "FOUND" in message_upper:
                    tag_to_apply = "INFO"
                elif message.strip().startswith(">>>") or message.strip().startswith("Gửi lệnh"):
                    tag_to_apply = "CMD"

                if tag_to_apply:
                    log_widget.insert(tk.END, message + '\n', (tag_to_apply,))
                else:
                    log_widget.insert(tk.END, message + '\n')

                log_widget.see(tk.END)
                log_widget.config(state=tk.DISABLED)
            except tk.TclError as e:
                logger.error(f"Lỗi Tcl khi cập nhật ScrolledText: {e} (Widget có thể đã bị hủy)")
            except Exception as e:
                logger.exception(f"Lỗi không xác định khi ghi log vào GUI: {e}")
        else:
            print(f"LOG (No GUI Widget): {message}")
            logger.warning(f"log_to_gui được gọi nhưng widget không hợp lệ hoặc chưa sẵn sàng. Message: {message}")

    def start_task(self, mode: str):
        logger.info(f"Đang thử bắt đầu tác vụ: {mode}")

        if self.active_thread and self.active_thread.is_alive():
            messagebox.showwarning("Đang bận", "Một tác vụ khác đang chạy. Vui lòng đợi.", parent=self.root)
            logger.warning("Đã thử bắt đầu tác vụ trong khi tác vụ khác đang chạy.")
            return

        current_widgets = self.tab_widgets.get(mode)
        if not current_widgets:
            messagebox.showerror("Lỗi Nội Bộ", f"Không tìm thấy cấu hình giao diện cho chế độ '{mode}'.", parent=self.root)
            logger.critical(f"Không thể tìm thấy dict widget cho mode '{mode}'")
            return

        output_widget = current_widgets.get('output')
        if not output_widget or not isinstance(output_widget, scrolledtext.ScrolledText):
            logger.critical(f"Không tìm thấy widget đầu ra cho chế độ {mode}.")
            messagebox.showerror("Lỗi nội bộ", "Không tìm thấy màn hình đầu ra cho tab này.", parent=self.root)
            return

        task_details = {"mode": mode}

        try:
            username = self.entry_username.get().strip()
            password = self.entry_password.get()
            start_ip = self.entry_start_ip.get().strip()
            end_ip = self.entry_end_ip.get().strip()

            if not all([username, password, start_ip, end_ip]):
                messagebox.showerror("Thiếu Thông Tin Chung",
                                     "Vui lòng nhập đầy đủ:\n- Tên người dùng\n- Mật khẩu\n- IP bắt đầu\n- IP kết thúc",
                                     parent=self.root)
                return

            try:
                ip_address(start_ip)
                ip_address(end_ip)
            except ValueError:
                messagebox.showerror("Lỗi Định Dạng IP", "Địa chỉ IP Bắt đầu hoặc Kết thúc không hợp lệ.", parent=self.root)
                return

            restricted_users = ["vietnd", "vietnd1"]
            if username.lower() in restricted_users:
                messagebox.showerror("Lỗi Người Dùng", "Tên và mật khẩu không đúng.", parent=self.root)
                logger.warning(f"user pass sai: {username}")
                return

            task_details["username"] = username
            task_details["password"] = password
            task_details["start_ip"] = start_ip
            task_details["end_ip"] = end_ip

        except AttributeError as e:
            logger.critical(f"Các trường nhập liệu chung không được khởi tạo đúng cách: {e}")
            messagebox.showerror("Lỗi nội bộ", "Không thể truy cập các trường thông tin chung.", parent=self.root)
            return

        target_vlan = None
        source_vlan = None

        if 'source_vlan' in current_widgets:
            source_vlan_entry = current_widgets['source_vlan']
            if source_vlan_entry:
                source_vlan = source_vlan_entry.get().strip()
                if not source_vlan or not VALID_VLAN_RE.match(source_vlan) or not (1 <= int(source_vlan) <= 4094):
                    messagebox.showerror("Lỗi VLAN Nguồn", "VLAN Nguồn là bắt buộc, phải là số từ 1-4094.", parent=self.root)
                    return
                task_details["source_vlan"] = source_vlan

        if 'target_vlan' in current_widgets:
            target_vlan_entry = current_widgets['target_vlan']
            if target_vlan_entry:
                target_vlan = target_vlan_entry.get().strip()
                if not target_vlan or not VALID_VLAN_RE.match(target_vlan) or not (1 <= int(target_vlan) <= 4094):
                    messagebox.showerror("Lỗi VLAN Đích", "VLAN Đích là bắt buộc, phải là số từ 1-4094.", parent=self.root)
                    return
                task_details["target_vlan"] = target_vlan

        if mode == "vlan_switch" and source_vlan and target_vlan and source_vlan == target_vlan:
            messagebox.showerror("Lỗi VLAN", "VLAN Nguồn và VLAN Đích không được trùng nhau.", parent=self.root)
            return

        mac_list = []
        mac_input_widget = None
        error_msg_mac = ""

        if 'mac_full' in current_widgets:
            mac_input_widget = current_widgets.get('mac_full')
            error_msg_mac = "Danh sách địa chỉ MAC đầy đủ không được để trống."
        elif 'mac_last4' in current_widgets:
            mac_input_widget = current_widgets.get('mac_last4')
            error_msg_mac = "Danh sách 4 ký tự cuối MAC không được để trống."

        if mac_input_widget:
            if not isinstance(mac_input_widget, scrolledtext.ScrolledText):
                logger.error(f"Widget MAC input cho mode {mode} không phải là ScrolledText.")
                messagebox.showerror("Lỗi Nội Bộ", "Lỗi cấu hình ô nhập MAC.", parent=self.root)
                return

            mac_input = mac_input_widget.get("1.0", tk.END).strip()
            if not mac_input:
                messagebox.showerror("Thiếu MAC", error_msg_mac, parent=self.root)
                return

            mac_list = [line.strip() for line in mac_input.splitlines() if line.strip()]
            if not mac_list:
                messagebox.showerror("Thiếu MAC", error_msg_mac.replace("không được để trống", "không chứa mục hợp lệ nào."), parent=self.root)
                return

        task_details["mac_list"] = mac_list

        start_log_msg = f"--- Bắt đầu tác vụ: {mode} ({time.strftime('%Y-%m-%d %H:%M:%S')}) ---"
        self.log_to_gui(start_log_msg, widget=output_widget, clear_previous=True, level="INFO")
        logger.info(start_log_msg)

        start_button = self.buttons.get(mode)
        if start_button and isinstance(start_button, tk.Button):
            start_button.config(text="Đang chạy...", state=tk.DISABLED, bg=self.colors["disabled_bg"])
        else:
            logger.warning(f"Không tìm thấy hoặc không thể vô hiệu hóa nút cho chế độ {mode}")

        self.status_var.set(f"{mode} đang khởi động...")
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = 100

        gui_queue.put(("set_output_widget", output_widget))
        self.current_active_button_mode = mode

        self.active_thread = threading.Thread(
            target=task_worker,
            args=(task_details,),
            name=f"Worker-{mode}",
            daemon=True
        )
        log_details = {k: v for k, v in task_details.items() if k != 'password'}
        logger.info(f"Bắt đầu luồng xử lý '{self.active_thread.name}' với chi tiết: {log_details}")
        self.active_thread.start()

    def check_queue(self):
        try:
            while True:
                message = gui_queue.get_nowait()
                msg_type = message[0]
                msg_data = message[1]

                if msg_type == "log":
                    self.log_to_gui(msg_data)

                elif msg_type == "status":
                    self.status_var.set(msg_data)

                elif msg_type == "messagebox":
                    level, text = msg_data
                    if level == "info":
                        messagebox.showinfo("Thông tin", text, parent=self.root)
                    elif level == "warning":
                        messagebox.showwarning("Cảnh báo", text, parent=self.root)
                    elif level == "error":
                        messagebox.showerror("Lỗi", text, parent=self.root)

                elif msg_type == "progress":
                    current, total = msg_data
                    if total > 0 and current >= 0:
                        self.progress_bar['maximum'] = total
                        self.progress_bar['value'] = min(current, total)
                    else:
                        self.progress_bar['maximum'] = 1
                        self.progress_bar['value'] = 1

                elif msg_type == "set_output_widget":
                    if isinstance(msg_data, scrolledtext.ScrolledText):
                        self.current_output_widget = msg_data
                    else:
                        logger.warning(f"Queue yêu cầu đặt widget output không hợp lệ: {type(msg_data)}")

                elif msg_type == "enable_button":
                    button_mode = msg_data
                    button_to_enable = self.buttons.get(button_mode)

                    if button_to_enable and isinstance(button_to_enable, tk.Button):
                        original_text = self.original_button_texts.get(button_mode, 'Bắt Đầu')
                        button_to_enable.config(text=original_text, state=tk.NORMAL, bg=self.colors["secondary"], fg=self.colors["text_light"])
                    else:
                        logger.warning(f"Yêu cầu kích hoạt nút cho chế độ '{button_mode}', nhưng nút không được tìm thấy hoặc không phải tk.Button.")

                    if self.current_active_button_mode == button_mode:
                        self.active_thread = None
                        self.current_active_button_mode = None

        except queue.Empty:
            pass
        except Exception as e:
            logger.exception("Lỗi nghiêm trọng khi xử lý hàng đợi GUI")
            try:
                self.status_var.set(f"Lỗi GUI Queue: {e}")
            except tk.TclError:
                print(f"Lỗi GUI Queue (không thể cập nhật status bar): {e}")

        self.root.after(150, self.check_queue)

    def on_closing(self):
        if self.active_thread and self.active_thread.is_alive():
            if messagebox.askokcancel("Thoát Ứng Dụng",
                                     "Một tác vụ mạng đang chạy.\n"
                                     "Việc thoát ngay bây giờ có thể khiến cấu hình chưa hoàn tất hoặc chưa được lưu.\n\n"
                                     "Bạn có chắc chắn muốn thoát?",
                                     icon='warning', parent=self.root):
                logger.warning("Ứng dụng bị đóng bởi người dùng trong khi tác vụ đang chạy.")
                self.root.destroy()
            else:
                return
        else:
            logger.info("Ứng dụng đóng bình thường.")
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SwitchManagerApp(root)
    root.mainloop()