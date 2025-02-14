DB_HOST = 'localhost'  # Địa chỉ host (localhost hoặc IP)
DB_PORT = 3306         # Cổng mặc định của MySQL
DB_USER = 'root'       # Tên người dùng
DB_PASSWORD = '123456' # Mật khẩu

SCAN_DELAY = 10000 #delay quét, đơn vị (ms)

# TRƯỜNG HỢP KẾT NỐI DATABASE Bị lỗi
MAX_RETRIES = 3 # số lần thử kết nối lại
RETRY_DELAY = 2 # delay giữa các lần thử, đơn vị (s)

# Add admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'  # Should be a strong password in production

# JWT config
JWT_SECRET_KEY = 'Hoàng Chương'  # Change this to a secure secret key
JWT_EXPIRE_HOURS = 48
