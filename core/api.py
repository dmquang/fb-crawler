import requests, time, base64, threading, re
from bs4 import BeautifulSoup
from utils import *

class FacebookCrawler:
    def __init__(self, url: str, cookie: str = None):
        # Khởi tạo Session
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'vi-VN,vi;q=0.9',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }
        self.session = requests.session()
        self.session.headers = self.headers.copy()

        # Khởi tạo thông tin post
        self.url = url
        if not cookie:
            self.cookies = self.getCookies()
        else:
            self.cookies = cookie
        self.id = self.getId()


    def getComments(self) -> list:
        self.getCount()
        # lấy comments
        temp_comments = []
        b64_id = str_to_base64(f'feedback:{self.id}')

        headers = {
            'accept': '*/*',
            'accept-language': 'vi',
            'content-type': 'application/x-www-form-urlencoded',
            'priority': 'u=1, i',
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-full-version-list': '"Google Chrome";v="131.0.6778.266", "Chromium";v="131.0.6778.266", "Not_A Brand";v="24.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"15.0.0"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'x-asbd-id': '129477',
            'x-fb-friendly-name': 'CommentListComponentsRootQuery',
            'x-fb-lsd': 'AVrsTDFZQco',
        }

        data = {
            'av': '0',
            '__aaid': '0',
            '__user': '0',
            '__a': '1',
            '__req': 'n',
            '__hs': '20112.HYP:comet_loggedout_pkg.2.1.0.0.0',
            'dpr': '1',
            '__ccg': 'EXCELLENT',
            '__rev': '1019545371',
            'lsd': 'AVrsTDFZQco',
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'CommentListComponentsRootQuery',
            'variables': '{"commentsIntentToken":"RECENT_ACTIVITY_INTENT_V1","feedLocation":"PERMALINK","feedbackSource":2,"focusCommentID":null,"scale":1,"useDefaultActor":false,"id":"'+b64_id+'","__relay_internal__pv__IsWorkUserrelayprovider":false}',
            'server_timestamps': 'true',
            'doc_id': '8894656107282580',
        }

        response = requests.post('https://www.facebook.com/api/graphql/', cookies=self.cookies, headers=headers, data=data).json() 
        edges = response['data']['node']['comment_rendering_instance_for_feed_location']['comments']['edges']

        for node in edges:
            parent_uid = node['node']['legacy_token'].split('_')[1]
            comment_uid = node['node']['legacy_fbid']
            try:
                comment = node['node']['body']['text']
            except:
                comment = 'Bình luận không có nội dung!'
                
            author_name = node['node']['author']['name']
            author_id = node['node']['author']['id']
            author_url = node['node']['author']['url']
            author_avatar = node['node']['author']['profile_picture_depth_0']['uri']

            created_time = node['node']['created_time']

            comment_data = {
                'comment_id': comment_uid,
                'post_id': parent_uid,
                'author_name': author_name,
                'author_id': author_id,
                'author_url': author_url,
                'author_avatar': author_avatar,
                'content': comment,
                'created_time': int(created_time),
            }

            temp_comments.append(comment_data)
        
        return sorted(temp_comments, key=lambda x: x['created_time'], reverse=True)

    def getId(self) -> str:
        # Lấy id của post
        post = self.session.get(self.url, cookies=self.cookies).text
        id = post.split('"post_id":"')[1].split('"')[0]
        return id

    def getCookies(self) -> dict:
        # Lấy cookies từ url
        response = requests.get(self.url, headers=self.headers)
        cookies = response.cookies.get_dict()
        if self.url != response.url:
            self.url = response.url
            response = requests.get(self.url, headers=self.headers, cookies=cookies)
            cookies = response.cookies.get_dict()

        self.reaction_count = int(response.text.split('"reaction_count":{"count":')[1].split(',')[0].replace('}', ''))
        

        self.comment_count = int(response.text.split('"comments":{"total_count":')[1].split('}')[0])

        return cookies
    
    def getCount(self) -> tuple:
        response = requests.get(self.url, headers=self.headers, cookies=self.cookies)
        self.reaction_count = int(response.text.split('"reaction_count":{"count":')[1].split(',')[0].replace('}', ''))
        self.comment_count = int(response.text.split('"comments":{"total_count":')[1].split('}')[0])
        return (self.reaction_count, self.comment_count)
    


