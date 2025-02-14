# from core.api import *


# url = 'https://www.facebook.com/61567797016338/videos/1266382624553329/#'
# proxy = '42.96.5.233:15949:tuanlee15949:aqofw'
# token = 'EAAAAAYsX7TsBO4J6XKWJDAZA6CqXZAYTHJJZABBr63CP4F4Qdfaoko4Ojs8JJnxUnWnh5zn5W5EYSRthAEWJ85h7TLv2z9rNCm7ZCZAtWMEg7y0oO8O0Ne9ZBB0DqcyavwAf3n1jv1cy5xLXysayNOUpyDG7hnq8BvT0Yo2ZAEBAaujWUbiJzLPYJnuzgZDZD'


# fb = FacebookToken(token, proxy)

# print(fb.getComments('1266382624553329'))


from utils import DatabaseManager
from config import *

db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

vl = ('122107355690593233', '1266382624553329', 'https://www.facebook.com/61567797016338/videos/1266382624553329/#', 'admin', 2019, 655, 1739453556, 1739445883, 'private', 10000)

db.add_data(
            'posts',
            columns=['post_id', 'post_name', 'post_url', 'username', 'reaction_count', 'comment_count', 'time_created', 'last_comment', 'status', 'delay'],
            values_list=[vl]
        )