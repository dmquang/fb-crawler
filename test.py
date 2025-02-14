# from core.api import *


# url = 'https://www.facebook.com/hatsanhphuongnguyen/videos/788106643076090/#'
# proxy = '42.96.5.233:15949:tuanlee15949:aqofw'
# fb = FacebookCrawler(url=url, proxy=proxy)

# print(fb.getComments())

from utils import DatabaseManager
from config import *

db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
print(db.fetch_data('proxies'))