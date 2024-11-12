import getpass
import pandas as pd
import pyodbc
import os
from sqlalchemy import create_engine

# Nhập thông tin cần thiết
instance = input('Nhập tên SQL Server instance: ')
dbName = input('Nhập tên database: ')
excelFilePath = input('Nhập đường dẫn đến file Excel: ')
tableName = input('Nhập tên bảng mới để import dữ liệu: ')
username = input('Nhập tên đăng nhập SQL Server: ')
password = getpass.getpass('Nhập mật khẩu SQL Server: ')

# Kiểm tra file Excel
if not os.path.exists(excelFilePath):
    print("Không tìm thấy file: ", excelFilePath)
    exit(1)

# Chuỗi kết nối SQL
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={instance};"
    f"DATABASE={dbName};"
    f"UID={username};"
    f"PWD={password};"
)

try:
    # Mở kết nối SQL
    cnxn = pyodbc.connect(conn_str)
    cursor = cnxn.cursor()
    print("Kết nối SQL Server thành công.")

    # Đọc dữ liệu từ file Excel
    df = pd.read_excel(excelFilePath)
    print(f"Đã đọc {len(df)} dòng từ file Excel.")

    # Tạo bảng mới trong SQL Server (nếu chưa tồn tại)
    columns = ", ".join([f"[{col}] NVARCHAR(MAX)" for col in df.columns])
    create_table_query = f"IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{tableName}') CREATE TABLE {tableName} ({columns})"
    cursor.execute(create_table_query)
    print(f"Đã tạo bảng {tableName} (nếu chưa tồn tại).")

    # Import dữ liệu vào SQL Server
    for index, row in df.iterrows():
        placeholders = ", ".join(["?" for _ in row])
        query = f"INSERT INTO {tableName} VALUES ({placeholders})"
        cursor.execute(query, tuple(row))
        
        if index % 1000 == 0:
            print(f"Đã import {index + 1} dòng...")
    
    cnxn.commit()
    print(f"Đã import thành công {len(df)} dòng vào bảng {tableName}.")

    # Tối ưu hóa bảng sau khi import
    print("Đang tối ưu hóa bảng...")
    cursor.execute(f'ALTER INDEX ALL ON {tableName} REBUILD')
    cursor.execute(f'UPDATE STATISTICS {tableName} WITH FULLSCAN')
    print("Đã tối ưu hóa bảng.")

except pyodbc.Error as e:
    print(f"Lỗi kết nối hoặc thực thi SQL: {e}")
except pd.errors.EmptyDataError:
    print("File Excel trống hoặc không có dữ liệu.")
except Exception as e:
    print(f"Lỗi không xác định: {e}")
finally:
    if 'cursor' in locals():
        cursor.close()
    if 'cnxn' in locals():
        cnxn.close()
    print("Đã đóng kết nối.")

print("Quá trình hoàn tất.")