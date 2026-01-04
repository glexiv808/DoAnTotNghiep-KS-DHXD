# Hướng dẫn Tạo Tài khoản Admin

## Giới thiệu
Hệ thống yêu cầu ít nhất một tài khoản admin để quản lý các người dùng khác. Dưới đây là các cách tạo admin:


## **Cách 3: Sử dụng API cURL/Postman**

**Endpoint:** `POST http://127.0.0.1:5000/create-first-admin`

**Headers:**
```
Content-Type: application/json
```

**Body (JSON):**
```json
{
    "username": "admin",
    "email": "admin@example.com",
    "password": "Admin@123456",
    "full_name": "Administrator"
}
```

**Ví dụ cURL:**
```bash
curl -X POST http://127.0.0.1:5000/create-first-admin \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "email": "admin@example.com",
    "password": "Admin@123456",
    "full_name": "Administrator"
  }'
```

**Response Thành công (201):**
```json
{
    "status": "success",
    "message": "Admin account \"admin\" created successfully",
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
}
```

---

## Lưu ý Quan trọng

- Endpoint `/create-first-admin` **CHỈ hoạt động khi chưa có admin nào** trong hệ thống
- Sau khi tạo admin đầu tiên, endpoint này sẽ bị khóa
- Admin có thể tạo admin khác thông qua endpoint `/admin/users`
- Luôn dùng mật khẩu mạnh (ít nhất 8 ký tự)

---

## Quản lý Người dùng Sau Khi Tạo Admin

**Sau khi tạo admin, bạn có thể:**

1. **Đăng nhập:**
   ```
   http://127.0.0.1:5500/UI/index.html
   ```
   Dùng tài khoản admin vừa tạo

2. **Quản lý tài khoản:**
   - Truy cập: `http://127.0.0.1:5500/UI/user_management.html`
   - Tạo user mới
   - Chỉnh sửa thông tin user
   - Xóa user
   - Xem hợp đồng của từng user

3. **Endpoints Admin:**
   - `GET /admin/users` - Danh sách người dùng
   - `GET /admin/users/{id}` - Chi tiết người dùng
   - `POST /admin/users` - Tạo user mới
   - `PUT /admin/users/{id}` - Cập nhật user
   - `DELETE /admin/users/{id}` - Xóa user
   - `GET /admin/stats` - Thống kê hệ thống

---

## Troubleshooting

**Q: Lỗi "Server not running"**
- A: Hãy khởi động server trước: `python -m uvicorn ML-app:app --reload --host 0.0.0.0 --port 5000`

**Q: Lỗi "Admin account already exists"**
- A: Admin đã tồn tại. Hãy đăng nhập hoặc sử dụng `/admin/users` endpoint để quản lý

**Q: Quên mật khẩu admin**
- A: Xóa file `ml_service.db` và chạy lại cách 1 hoặc 2 để tạo admin mới

---

## Ví dụ Đầu Tiên

**Bước 1:** Tạo admin
```bash
python create_admin.py
# Hoặc truy cập: http://127.0.0.1:5500/UI/create_admin.html
```

**Bước 2:** Đăng nhập với admin
```
URL: http://127.0.0.1:5500/UI/index.html
Username: admin
Password: Admin@123456
```

**Bước 3:** Quản lý người dùng
```
URL: http://127.0.0.1:5500/UI/user_management.html
```

