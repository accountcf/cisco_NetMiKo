import logging
from bitcoinlib.keys import Key
import secrets
import time
import requests

# Thiết lập logging cơ bản
logging.basicConfig(level=logging.INFO)

# Hàm tạo private key ngẫu nhiên (hex format)
def generate_private_key():
    return secrets.token_hex(32)

# Hàm kiểm tra số dư của địa chỉ Bitcoin
def check_btc_balance(address):
    url = f"https://blockchain.info/balance?active={address}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get(address, {}).get("final_balance", 0)
    return 0

# Hàm ghi kết quả vào file
def write_to_file(filename, data):
    with open(filename, "a") as file:
        file.write(data + "\n")

# Hàm chính
def main():
    output_file = 'btc.txt'
    num_keys_to_check = 9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999  # Số lượng khóa muốn kiểm tra

    for _ in range(num_keys_to_check):
        try:
            # Tạo khóa riêng tư ngẫu nhiên
            private_key = generate_private_key()
            
            # Tạo đối tượng Key từ khóa riêng tư dạng hex
            key = Key(private_key, is_private=True)
            address = key.address()

            # Kiểm tra số dư
            balance_satoshi = check_btc_balance(address)
            btc_balance = balance_satoshi / 100000000  # Chuyển sang BTC

            # Ghi log chỉ với khóa và kết quả số dư
            if btc_balance > 0:
                logging.info(f"Key: {private_key} - Found balance: {format(btc_balance, '.8f')} BTC")
                result = f"Private Key: {private_key}, Address: {address}, Balance: {format(btc_balance, '.8f')} BTC\n"
                write_to_file(output_file, result)
            else:
                logging.info(f"Key: {private_key} - No balance found")

            # Thêm độ trễ 1 giây để tuân thủ giới hạn API
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error with key {private_key[:8]}...: {e}")

if __name__ == "__main__":
    main()