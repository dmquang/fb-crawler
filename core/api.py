import requests, time, base64, threading, re
import json
from bs4 import BeautifulSoup
from utils import *
import uuid
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime

def iso_to_timestamp(iso_time):
    dt = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%S%z")  # Chuyển ISO 8601 sang datetime
    return int(dt.timestamp())

class CheckProxies:
    @staticmethod
    def check(proxy: str):
        try:
            proxys = proxy.split(':')
            proxies = {'https': f'http://{proxys[-2]}:{proxys[-1]}@{proxys[0]}:{proxys[1]}'}
            response = requests.get('https://api64.ipify.org?format=json', proxies=proxies).json()
            return True
        except:
            return False

class FacebookCrawler:
    def __init__(self, url: str, cookie: str = None, proxy: str = None):
        self.ok = True

        self.proxy = proxy
        if proxy:
            proxy_parts = proxy.split(":")
            if len(proxy_parts) == 2:
                self.proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
            elif len(proxy_parts) == 4:
                ip, port, user, password = proxy_parts
                self.proxies = {"http": f"http://{user}:{password}@{ip}:{port}", "https": f"https://{user}:{password}@{ip}:{port}"}
        else:
            self.proxies = None

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
            self.fb_dtsg = None
            self.jazoest = None
            self.lsd = None
            self.user_id = None
        else:
            self.cookies = {}
            cks = cookie.replace(' ','').split(';')
            for ck in cks:
                try:
                    key, value = ck.split('=')
                    self.cookies[key] = value
                except:
                    break

            auth = FacebookAuthencation(cookie, proxy)
            self.user_id = auth.user_id
            self.fb_dtsg = auth.fb_dtsg
            self.jazoest = auth.jazoest
            self.lsd = auth.lsd
            self.get_url()
            
        self.id = self.getId()

    def get_url(self):
        self.url = self.session.get(self.url, cookies=self.cookies, proxies=self.proxies).url

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

        }

        data = {
            'av': '0' if not self.user_id else self.user_id,
            '__aaid': '0',
            '__user': '0' if not self.user_id else self.user_id,
            '__a': '1',
            '__req': 'n',
            '__hs': '20112.HYP:comet_loggedout_pkg.2.1.0.0.0',
            'dpr': '1',
            '__ccg': 'EXCELLENT',
            'lsd': 'AVrsTDFZQco' if not self.lsd else self.lsd,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'CommentListComponentsRootQuery',
            'variables': '{"commentsIntentToken":"RECENT_ACTIVITY_INTENT_V1","feedLocation":"PERMALINK","feedbackSource":110,"focusCommentID":null,"scale":1,"useDefaultActor":false,"id":"'+b64_id+'","__relay_internal__pv__IsWorkUserrelayprovider":false}',
            'server_timestamps': 'true',
            'doc_id': '8894656107282580' if not self.fb_dtsg else '8983884358327685',
        }

        if self.fb_dtsg:
            data['fb_dtsg'] = self.fb_dtsg
            data['jazoest'] = self.jazoest

        response = requests.post('https://www.facebook.com/api/graphql/', cookies=self.cookies, headers=headers, data=data, proxies=self.proxies).text
        if '\n' in response:
            response = response.split('\n')[0]
        response_data = json.loads(response)
        edges = response_data['data']['node']['comment_rendering_instance_for_feed_location']['comments']['edges']


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
        post = self.session.get(self.url, cookies=self.cookies, proxies=self.proxies).text
        self.owner_id = post.split('[{"__typename":"User","id":"')[1].split('"')[0]

        if 'reel' in self.url:
            self.id_reel = post.split(',"initial_node_id":')[1].split(',')[0]
        try:
            id = post.split('"post_id":"')[1].split('"')[0]
            return id
        except:
            self.ok = False

    def getCookies(self) -> dict:
        # Lấy cookies từ url
        response = requests.get(self.url, headers=self.headers)
        cookies = response.cookies.get_dict()
        if self.url != response.url:
            self.url = response.url
            response = requests.get(self.url, headers=self.headers, cookies=cookies, proxies=self.proxies)
            cookies = response.cookies.get_dict()
        return cookies
    
    def getCount(self) -> tuple:
        if 'reel' in self.url:
            b64_id = str_to_base64(f'S:_I{self.owner_id}:VK:{self.id_reel}')
            headers = {
                'accept': '*/*',
                'accept-language': 'vi,en;q=0.9,vi-VN;q=0.8,fr-FR;q=0.7,fr;q=0.6,en-US;q=0.5',
                'content-type': 'application/x-www-form-urlencoded',
                'priority': 'u=1, i',
                'sec-ch-prefers-color-scheme': 'dark',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
                'sec-ch-ua-full-version-list': '"Not A(Brand";v="8.0.0.0", "Chromium";v="132.0.6834.111", "Google Chrome";v="132.0.6834.111"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-model': '""',
                'sec-ch-ua-platform': '"Windows"',
                'sec-ch-ua-platform-version': '"15.0.0"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                'x-asbd-id': '129477',
                'x-fb-friendly-name': 'FBReelsFeedbackLikeQuery',
            }

            data = {
                'av': '0' if not self.user_id else self.user_id,
                '__aaid': '0',
                '__user': '0' if not self.user_id else self.user_id,
                '__a': '1',
                '__req': 'n',
                '__hs': '20112.HYP:comet_loggedout_pkg.2.1.0.0.0',
                'dpr': '1',
                '__ccg': 'EXCELLENT',
                'lsd': 'AVrsTDFZQco' if not self.lsd else self.lsd,
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'FBReelsFeedbackLikeQuery',
                'variables': '{"id":"'+b64_id+'"}',
                'server_timestamps': 'true',
                'doc_id': '7356228301113273',
            }

            if self.fb_dtsg:
                data['fb_dtsg'] = self.fb_dtsg
                data['jazoest'] = self.jazoest

            response = requests.post('https://www.facebook.com/api/graphql/', cookies=self.cookies, headers=headers, data=data, proxies=self.proxies).json()
            self.reaction_count = response['data']['node']['feedback']['likers']['count']

            response = requests.get(self.url, headers=self.headers, cookies=self.cookies, proxies=self.proxies)
            self.comment_count = int(response.text.split('"comments":{"total_count":')[1].split('}')[0])

        else:
            response = requests.get(self.url, headers=self.headers, cookies=self.cookies, proxies=self.proxies)
            self.reaction_count = int(response.text.split('"reaction_count":{"count":')[1].replace('}', '').split(',')[0])
            self.comment_count = int(response.text.split('"comments":{"total_count":')[1].split('}')[0])

        return (self.reaction_count, self.comment_count)

class FacebookAuthencation:
    def __init__(self, cookie: str, proxy: str = None):
        self.cookie = cookie
        self.proxy = proxy
        if proxy:
            proxys = proxy.split(':')
            self.proxies = {'https': f'http://{proxys[-2]}:{proxys[-1]}@{proxys[0]}:{proxys[1]}'}
        else:
            self.proxies = None

        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'vi,en;q=0.9,vi-VN;q=0.8,fr-FR;q=0.7,fr;q=0.6,en-US;q=0.5',
            'cache-control': 'max-age=0',
            'cookie': cookie,
            'dpr': '1',
            'priority': 'u=0, i',
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-full-version-list': '"Google Chrome";v="131.0.6778.267", "Chromium";v="131.0.6778.267", "Not_A Brand";v="24.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"15.0.0"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }

        self.user_id = self.get_id()

    def get_id(self):
        response = requests.get('https://www.facebook.com/', headers=self.headers, proxies=self.proxies).text
        try:
            user_id = response.split('"USER_ID":"')[1].split('"')[0]
            self.jazoest = response.split('jazoest=')[1].split('"')[0]
            self.fb_dtsg = response.split('"DTSGInitialData",[],{"token":"')[1].split('"')[0]
            self.lsd = response.split('"LSD",[],{"token":"')[1].split('"')[0]
            return user_id
        except:

            return 
            

class FacebookToken:
    def __init__(self, token: str, proxy: str = None):
        self.proxy = proxy
        self.token = token
        if proxy:
            proxy_parts = proxy.split(":")
            if len(proxy_parts) == 2:
                self.proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
            elif len(proxy_parts) == 4:
                ip, port, user, password = proxy_parts
                self.proxies = {"http": f"http://{user}:{password}@{ip}:{port}", "https": f"https://{user}:{password}@{ip}:{port}"}
        else:
            self.proxies = None

    def me(self) -> str:
        response = requests.get(f'https://graph.facebook.com/v11.0/me?access_token={self.token}', proxies=self.proxies).json()
        return response['id'] if 'id' in response else 'Invalid Token'

    def get_cookie(self) -> str:
        sub=requests.post('https://graph.facebook.com/auth/create_session_for_app', data={"locale": "vi_VN","format": "json","new_app_id": "6628568379","access_token": self.token,"generate_session_cookies":"1"}, proxies=self.proxies)
        cookie = ''
        for ck in sub.json()['session_cookies']:
            cookie += f'{ck["name"]}={ck["value"]};'
        return cookie
    
    def getComments(self, object_id: str = '123456789_123456789') -> list:
        response = requests.get(
            'https://graph.facebook.com/'+object_id+'/comments?order=reverse_chronological&fields=from{id,name,picture},message,created_time&access_token='+self.token,
            proxies=self.proxies,
        )
        response = json.loads(response.text)

        comments = []

        for comment in response['data']:
            comment_id = comment['id'].split('_')[1]
            post_id = comment['id'].split('_')[0]
            author_name = comment['from']['name']
            author_id = comment['from']['id']
            author_url = f'https://www.facebook.com/{author_id}'
            author_avatar = comment['from']['picture']['data']['url']
            content = comment['message'] if 'message' in comment else ''
            created_time = iso_to_timestamp(comment['created_time'])

            comment_data = {
                'comment_id': comment_id,
                'post_id': post_id,
                'author_name': author_name,
                'author_id': author_id,
                'author_url': author_url,
                'author_avatar': author_avatar,
                'content': content,
                'created_time': int(created_time),
            }
            comments.append(comment_data)
        
        return comments
    
    def getCount(self, object_id) -> tuple:
        response = requests.get(
            'https://graph.facebook.com/'+object_id+'/?fields=reactions.summary(true),comments.summary(true)&access_token=' + self.token,
            proxies=self.proxies
        )

        response = json.loads(response.text)
        reactions = response['reactions']['summary']['total_count'] if 'reactions' in response else 0
        comments = response['comments']['summary']['total_count'] if 'comments' in response else 0
        return reactions, comments


TOKEN_TO_APP_ID = {
    "EAAAAAY": "6628568379"
}

class FacebookTokenExtractor:
    def __init__(self, token_type: str, proxy: str = None):
        self.app_id = TOKEN_TO_APP_ID.get(token_type)
        if not self.app_id:
            raise ValueError("Invalid token type")
        self.session = requests.Session()
        self.session.headers.update({
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'vi,en;q=0.9,vi-VN;q=0.8,fr-FR;q=0.7,fr;q=0.6,en-US;q=0.5',
            'cache-control': 'max-age=0',
            'dpr': '1',
            'priority': 'u=0, i',
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
            'sec-ch-ua-full-version-list': '"Not A(Brand";v="8.0.0.0", "Chromium";v="132.0.6834.160", "Google Chrome";v="132.0.6834.160"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"15.0.0"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
        })
        if proxy:
            self.set_proxy(proxy)
    
    def set_proxy(self, proxy: str):
        proxy_parts = proxy.split(":")
        if len(proxy_parts) == 2:
            self.session.proxies = {"http": f"http://{proxy}", "https": f"https://{proxy}"}
        elif len(proxy_parts) == 4:
            ip, port, user, password = proxy_parts
            self.session.proxies = {"http": f"http://{user}:{password}@{ip}:{port}", "https": f"https://{user}:{password}@{ip}:{port}"}

    def change_cookies_fb(self, cookie: str):
        cookies = {}
        cks = cookie.replace(' ','').split(';')
        for ck in cks:
            try:
                key, value = ck.split('=')
                cookies[key] = value
            except:
                break
        return cookies

    def get_token(self, fb_dtsg: str, lsd: str, cookies: dict, c_user: str):
        headers = {
                'authority': 'www.facebook.com',
                'accept': '*/*',
                'accept-language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
                'content-type': 'application/x-www-form-urlencoded',
                'dnt': '1',
                'origin': 'https://www.facebook.com',
                'sec-ch-ua': '"Chromium";v="117", "Not;A=Brand";v="8"',
                'sec-ch-ua-full-version-list': '"Chromium";v="117.0.5938.157", "Not;A=Brand";v="8.0.0.0"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-model': '""',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
                'x-fb-friendly-name': 'useCometConsentPromptEndOfFlowBatchedMutation',
        }
        response = self.session.post('https://www.facebook.com/api/graphql/', data={
            'av': str(c_user),
            '__user': str(c_user),
            'fb_dtsg': fb_dtsg,
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'useCometConsentPromptEndOfFlowBatchedMutation',
            'variables': '{"input":{"client_mutation_id":"4","actor_id":"' + c_user + '","config_enum":"GDP_CONFIRM","device_id":null,"experience_id":"' + str(
                uuid.uuid4()
                ) + '","extra_params_json":"{\\"app_id\\":\\"' + self.app_id + '\\",\\"kid_directed_site\\":\\"false\\",\\"logger_id\\":\\"\\\\\\"' + str(
                uuid.uuid4()
                ) + '\\\\\\"\\",\\"next\\":\\"\\\\\\"confirm\\\\\\"\\",\\"redirect_uri\\":\\"\\\\\\"https:\\\\\\\\\\\\/\\\\\\\\\\\\/www.facebook.com\\\\\\\\\\\\/connect\\\\\\\\\\\\/login_success.html\\\\\\"\\",\\"response_type\\":\\"\\\\\\"token\\\\\\"\\",\\"return_scopes\\":\\"false\\",\\"scope\\":\\"[\\\\\\"user_subscriptions\\\\\\",\\\\\\"user_videos\\\\\\",\\\\\\"user_website\\\\\\",\\\\\\"user_work_history\\\\\\",\\\\\\"friends_about_me\\\\\\",\\\\\\"friends_actions.books\\\\\\",\\\\\\"friends_actions.music\\\\\\",\\\\\\"friends_actions.news\\\\\\",\\\\\\"friends_actions.video\\\\\\",\\\\\\"friends_activities\\\\\\",\\\\\\"friends_birthday\\\\\\",\\\\\\"friends_education_history\\\\\\",\\\\\\"friends_events\\\\\\",\\\\\\"friends_games_activity\\\\\\",\\\\\\"friends_groups\\\\\\",\\\\\\"friends_hometown\\\\\\",\\\\\\"friends_interests\\\\\\",\\\\\\"friends_likes\\\\\\",\\\\\\"friends_location\\\\\\",\\\\\\"friends_notes\\\\\\",\\\\\\"friends_photos\\\\\\",\\\\\\"friends_questions\\\\\\",\\\\\\"friends_relationship_details\\\\\\",\\\\\\"friends_relationships\\\\\\",\\\\\\"friends_religion_politics\\\\\\",\\\\\\"friends_status\\\\\\",\\\\\\"friends_subscriptions\\\\\\",\\\\\\"friends_videos\\\\\\",\\\\\\"friends_website\\\\\\",\\\\\\"friends_work_history\\\\\\",\\\\\\"ads_management\\\\\\",\\\\\\"create_event\\\\\\",\\\\\\"create_note\\\\\\",\\\\\\"export_stream\\\\\\",\\\\\\"friends_online_presence\\\\\\",\\\\\\"manage_friendlists\\\\\\",\\\\\\"manage_notifications\\\\\\",\\\\\\"manage_pages\\\\\\",\\\\\\"photo_upload\\\\\\",\\\\\\"publish_stream\\\\\\",\\\\\\"read_friendlists\\\\\\",\\\\\\"read_insights\\\\\\",\\\\\\"read_mailbox\\\\\\",\\\\\\"read_page_mailboxes\\\\\\",\\\\\\"read_requests\\\\\\",\\\\\\"read_stream\\\\\\",\\\\\\"rsvp_event\\\\\\",\\\\\\"share_item\\\\\\",\\\\\\"sms\\\\\\",\\\\\\"status_update\\\\\\",\\\\\\"user_online_presence\\\\\\",\\\\\\"video_upload\\\\\\",\\\\\\"xmpp_login\\\\\\"]\\",\\"steps\\":\\"{}\\",\\"tp\\":\\"\\\\\\"unspecified\\\\\\"\\",\\"cui_gk\\":\\"\\\\\\"[PASS]:\\\\\\"\\",\\"is_limited_login_shim\\":\\"false\\"}","flow_name":"GDP","flow_step_type":"STANDALONE","outcome":"APPROVED","source":"gdp_delegated","surface":"FACEBOOK_COMET"}}',
            'server_timestamps': 'true',
            'doc_id': '6494107973937368',
        }, cookies=cookies, headers=headers)
        try:
            json_response = response.json()
            print(json_response)
            uri = json_response["data"]["run_post_flow_action"]["uri"]
            fragment = urlparse(unquote(parse_qs(urlparse(uri).query)["close_uri"][0])).fragment
            return parse_qs(fragment).get("access_token", [None])[0]
        except Exception as e:
            return None

    def get_login(self, cookie: str):
        cookies = self.change_cookies_fb(cookie)
        response = self.session.get('https://www.facebook.com/', cookies=cookies)
        try:
            id_user = response.text.split('"actorId":"')[1].split('"')[0]
            if id_user == "0":
                return {"login": False}
            fb_dtsg = response.text.split('"DTSGInitialData",[],{"token":"')[1].split('"')[0]
            lsd = response.text.split('"LSD",[],{"token":"')[1].split('"')[0]
            access_token = self.get_token(fb_dtsg, lsd, cookies, id_user)
            return {"login": True, "access_token": access_token}
        except Exception as e:
            return {"error": str(e)}
        
def run_hidden(cookie, fb_dtsg, lsd, comment_id, i_user) -> None:
    headers = {
        'authority': 'www.beta.facebook.com',
        'accept': '*/*',
        'accept-language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
        'content-type': 'application/x-www-form-urlencoded',
        'dnt': '1',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-model': '""',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'cookie': cookie,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
        'x-fb-friendly-name': 'CometUFIHideCommentMutation',
        'x-fb-lsd': lsd,
    }
    data = {
        'av': i_user,
        '__aaid': '0',
        '__user': i_user,
        '__a': '1',
        'dpr': '1',
        '__ccg': 'EXCELLENT',
        '__comet_req': '15',
        'fb_dtsg': fb_dtsg,
        'lsd': lsd,
        '__spin_b': 'trunk',
        'fb_api_caller_class': 'RelayModern',
        'fb_api_req_friendly_name': 'CometUFIHideCommentMutation',
        'variables': '{"input":{"comment_id":"' + comment_id + '","feedback_source":110,"hide_location":"UFI","site":"comet","actor_id":"' + i_user + '","client_mutation_id":"2"},"feedLocation":"DEDICATED_COMMENTING_SURFACE","useDefaultActor":false,"scale":1}',
        'server_timestamps': 'true',
        'doc_id': '27837125255886039',
    }
    response = requests.post(
        'https://www.beta.facebook.com/api/graphql/', headers=headers, data=data
    ).text