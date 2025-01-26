import json
import base64

def str_to_base64(input_str):
    # Chuyển chuỗi thành dữ liệu Base64
    byte_data = input_str.encode('utf-8')
    base64_bytes = base64.b64encode(byte_data)
    base64_str = base64_bytes.decode('utf-8')
    return base64_str

def base64_to_str(base64_str):
    # Chuyển dữ liệu Base64 thành chuỗi
    base64_bytes = base64_str.encode('utf-8')
    byte_data = base64.b64decode(base64_bytes)
    input_str = byte_data.decode('utf-8')
    return input_str

def cookies_to_string(cookies):
    """
    Converts a list of cookies to a string format suitable for HTTP headers.
    """
    pass