import sqlite3

# Kết nối database
conn = sqlite3.connect('ml_service.db')
cursor = conn.cursor()

# Kiểm tra danh sách hợp đồng
print('=== DANH SÁCH CÁC HỢP ĐỒNG HIỆN CÓ ===')
cursor.execute('SELECT contractNumber, customerName, loanAmount, status FROM loan_contracts')
rows = cursor.fetchall()
for row in rows:
    print(f'Hợp đồng: {row[0]}, Khách hàng: {row[1]}, Số tiền: {row[2]}, Trạng thái: {row[3]}')

print(f'\nTổng cộng: {len(rows)} hợp đồng')

# Xóa HĐ002 và HĐ003 (với ký tự Đ đặc biệt)
print('\n=== ĐANG XÓA HĐ002 và HĐ003 ===')
cursor.execute('DELETE FROM loan_contracts WHERE contractNumber IN ("HĐ002", "HĐ003")')
conn.commit()
deleted_count = cursor.rowcount
print(f'Đã xóa {deleted_count} hợp đồng')

# Kiểm tra lại
print('\n=== DANH SÁCH HỢP ĐỒNG SAU KHI XÓA ===')
cursor.execute('SELECT contractNumber, customerName, loanAmount, status FROM loan_contracts')
rows = cursor.fetchall()
for row in rows:
    print(f'Hợp đồng: {row[0]}, Khách hàng: {row[1]}, Số tiền: {row[2]}, Trạng thái: {row[3]}')

print(f'\nTổng cộng: {len(rows)} hợp đồng')

conn.close()
print('\n✓ Hoàn thành')
