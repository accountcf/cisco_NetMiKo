import pandas as pd
import pyodbc

# Thông tin kết nối SQL Server
server = '10.38.38.100'
database = 'SQLLinh'
username = 'sa'
password = 'Sql@2022'
cnxn_string = f'DRIVER={{SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

# Đường dẫn đến tệp Excel
excel_file_path = 'D:\ADMember.xlsx'
# Tên bảng mà bạn muốn tạo trong SQL Server
table_name = 'dbo.DD'

# Đọc dữ liệu từ tệp Excel
df = pd.read_excel(excel_file_path)

# Kết nối đến SQL Server
cnxn = pyodbc.connect(cnxn_string)
cursor = cnxn.cursor()

# Tạo câu lệnh SQL để tạo bảng mới
# Bạn cần thay thế 'Column1', 'Column2', v.v. bằng tên cột thực tế và kiểu dữ liệu phù hợp
create_table_query = f"""
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = N'{table_name}')
BEGIN
CREATE TABLE {table_name} (
    Column1 INT,
    Column2 NVARCHAR(255),
    -- thêm các định nghĩa cột ở đây
)
END
"""

# Thực thi câu lệnh tạo bảng
cursor.execute(create_table_query)
cursor.commit()

# Chèn dữ liệu từ DataFrame vào bảng SQL
# Bạn cần thay đổi phần này tùy theo cấu trúc của bảng và DataFrame của bạn
for index, row in df.iterrows():
    insert_query = f"INSERT INTO {table_name} (Column1, Column2) VALUES (?, ?)"
    cursor.execute(insert_query, row['Column1'], row['Column2'])

# Commit các thay đổi
cnxn.commit()

# Đóng kết nối
cursor.close()
cnxn.close()

print("Dữ liệu đã được nhập thành công vào SQL Server.")