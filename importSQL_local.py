import pyodbc
import os
from dotenv import load_dotenv

# Bước 0: Tải biến môi trường
load_dotenv()

# Bước 1: Kết nối
try:
    cnxn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 18 for SQL Server}};'
        f'SERVER={os.getenv("DB_SERVER")};'
        f'DATABASE={os.getenv("DB_NAME")};'
        f'UID={os.getenv("DB_USER")};'
        f'PWD={os.getenv("DB_PASSWORD")}'
    )
    print("Kết nối thành công đến SQL Server.")
except pyodbc.Error as e:
    print(f"Lỗi kết nối: {e}")
    exit(1)

cursor = cnxn.cursor()

# Bước 2: Chèn một dòng
try:
    cursor.execute("INSERT INTO EMP (EMPNO, ENAME, JOB, MGR) VALUES (?, ?, ?, ?)", 
                   (535, 'Scott', 'Manager', 545))
    cnxn.commit()
    print("Đã chèn dữ liệu thành công.")
except pyodbc.Error as e:
    print(f"Lỗi khi chèn dữ liệu: {e}")
    cnxn.rollback()

# Bước 3: Thực thi truy vấn và hiển thị kết quả
try:
    cursor.execute("SELECT * FROM EMP")
    rows = cursor.fetchall()
    
    if not rows:
        print("Không có dữ liệu trong bảng EMP.")
    else:
        print("Dữ liệu trong bảng EMP:")
        for row in rows:
            print(row)
except pyodbc.Error as e:
    print(f"Lỗi khi truy vấn dữ liệu: {e}")

finally:
    cursor.close()
    cnxn.close()
    print("Đã đóng kết nối.")