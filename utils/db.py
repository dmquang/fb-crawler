import mysql.connector
from typing import List
from datetime import datetime
import os

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
            'connection_timeout': 60,
            'autocommit': True
        }

    def _connect(self) -> mysql.connector.connect:
        """Thiết lập kết nối cơ sở dữ liệu"""
        try:
            conn = mysql.connector.connect(**self.config)
            cursor = conn.cursor(buffered=True)  # Sử dụng buffered cursor
            return conn, cursor
        except mysql.connector.Error as err:
            print(f"Error while connecting to database: {err}")
            raise

    def add_data(self, table: str, columns: List[str], values_list: List[tuple]) -> None:
        conn, cursor = self._connect()
        columns_str = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        sql = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
        try:
            cursor.executemany(sql, values_list)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"Error while adding data: {err}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def bulk_update(self, table, data_list, condition_key):
        conn, cursor = self._connect()
        try:
            for data in data_list:
                condition_value = data.pop(condition_key)
                updates = ', '.join([f"{key} = %s" for key in data.keys()])
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['%s'] * len(data))
                
                # MySQL query to insert or update
                sql = f"""
                    INSERT INTO {table} ({condition_key}, {columns})
                    VALUES (%s, {placeholders})
                    ON DUPLICATE KEY UPDATE {updates}
                """
                
                # Prepare values for INSERT ... ON DUPLICATE KEY UPDATE
                values = (condition_value, *data.values(), *data.values())
                
                # Execute the query
                cursor.execute(sql, values)
            
            conn.commit()
        except mysql.connector.Error as err:
            print(f"Error while bulk updating or inserting data: {err}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def delete_data(self, table, condition):
        conn, cursor = self._connect()
        try:
            sql = f"DELETE FROM {table} WHERE {condition}"
            cursor.execute(sql)
            conn.commit()
        except mysql.connector.Error as err:
            print(f"Error while deleting data: {err}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

    def fetch_data(self, table, columns='*', condition=None):
        conn, cursor = self._connect()
        try:
            sql = f"SELECT {columns} FROM {table}"
            if condition:
                sql += f" WHERE {condition}"
            cursor.execute(sql)
            return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error while fetching data: {err}")
            return []
        finally:
            cursor.close()
            conn.close()

    def execute_query(self, query: str, params: tuple = None):
        conn, cursor = self._connect()
        try:
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            return cursor.fetchall()
        except mysql.connector.Error as err:
            print(f"Error while executing query: {err}")
            return []
        finally:
            cursor.close()
            conn.close()

    def close(self):
        """Close the database connection"""
        if hasattr(self, 'conn') and self.conn.is_connected():
            self.cursor.close()
            self.conn.close()
            print("Database connection closed.")
        else:
            print("Database connection is already closed or was not initialized.")
