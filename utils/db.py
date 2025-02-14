import pymysql
from typing import List
from datetime import datetime

class DatabaseManager:
    def __init__(self, host, port, user, password, database):
        """
        Khởi tạo DatabaseManager và thiết lập kết nối với cơ sở dữ liệu.
        
        :param host: Địa chỉ host của cơ sở dữ liệu.
        :param port: Cổng kết nối đến cơ sở dữ liệu.
        :param user: Tên người dùng cơ sở dữ liệu.
        :param password: Mật khẩu của người dùng.
        :param database: Tên cơ sở dữ liệu.
        """
        self.config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database,
            'cursorclass': pymysql.cursors.Cursor,
            'autocommit': True
        }

    def _connect(self):
        """Thiết lập kết nối cơ sở dữ liệu"""
        try:
            conn = pymysql.connect(**self.config)
            cursor = conn.cursor()
            return conn, cursor
        except pymysql.MySQLError as err:
            print(f"Error while connecting to database: {err}")
            return None, None

    def add_data(self, table: str, columns: List[str], values_list: List[tuple]) -> None:
        conn, cursor = self._connect()
        if not conn:
            return
        
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        sql = f"INSERT IGNORE INTO {table} ({columns_str}) VALUES ({placeholders})"
        
        try:
            cursor.executemany(sql, values_list)
            conn.commit()
            print(f"[{datetime.now()}] \U0001F4BE Đã chèn {cursor.rowcount} bản ghi vào {table}")
        except pymysql.MySQLError as err:
            print(f"[{datetime.now()}] ❌ Lỗi khi thêm dữ liệu vào {table}: {err}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def bulk_update(self, table, data_list, condition_key):
        conn, cursor = self._connect()
        if not conn:
            return
        
        try:
            for data in data_list:
                condition_value = data.pop(condition_key)
                updates = ', '.join([f"{key} = %s" for key in data.keys()])
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['%s'] * len(data))
                
                sql = f"""
                    INSERT INTO {table} ({condition_key}, {columns})
                    VALUES (%s, {placeholders})
                    ON DUPLICATE KEY UPDATE {updates}
                """
                
                values = (condition_value, *data.values(), *data.values())
                cursor.execute(sql, values)
            
            conn.commit()
        except pymysql.MySQLError as err:
            print(f"Error while bulk updating or inserting data: {err}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def delete_data(self, table, condition):
        conn, cursor = self._connect()
        if not conn:
            return
        
        try:
            sql = f"DELETE FROM {table} WHERE {condition}"
            cursor.execute(sql)
            conn.commit()
        except pymysql.MySQLError as err:
            print(f"Error while deleting data: {err}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def fetch_data(self, table, columns='*', condition=None):
        conn, cursor = self._connect()
        if not conn:
            return []
        
        try:
            sql = f"SELECT {columns} FROM {table}"
            if condition:
                sql += f" WHERE {condition}"
            cursor.execute(sql)
            return cursor.fetchall()
        except pymysql.MySQLError as err:
            print(f"Error while fetching data: {err}")
            return []
        finally:
            cursor.close()
            conn.close()

    def execute_query(self, query: str, params: tuple = None):
        conn, cursor = self._connect()
        if not conn:
            return []
        
        try:
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            return cursor.fetchall()
        except pymysql.MySQLError as err:
            print(f"Error while executing query: {err}")
            return []
        finally:
            cursor.close()
            conn.close()

    def close(self):
        """Placeholder để tránh lỗi khi gọi close nhưng không có kết nối từ trước"""
        print("DatabaseManager không duy trì kết nối lâu dài, mỗi phương thức đã tự đóng kết nối.")
