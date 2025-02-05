from core.api import *
import threading
from time import sleep
from utils import DatabaseManager
from config import *
import random
import traceback
from datetime import datetime

def comment_progress(url, post_name, username, delay, token=None, cookie=None, proxy=None):
    try:
        print(f"\n[{datetime.now()}] 🔄 Bắt đầu xử lý post: {post_name}")
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        
        # Xử lý token và cookie
        if token:
            print(f"[{datetime.now()}] 🔑 Sử dụng token cho {post_name}")
            fbtk = FacebookToken(token=token, proxy=proxy)
            cookie = fbtk.get_cookie()
            print(f"[{datetime.now()}] 🍪 Đã lấy cookie từ token cho {post_name}")
        
        try:
            crawler = FacebookCrawler(url, cookie, proxy)
            crawler.getCount()
            comment_count = crawler.comment_count
            reaction_count = crawler.reaction_count
            # Thêm comment vào database
            comments = crawler.getComments()
        except:
            if not token:
                gettoken = FacebookTokenExtractor('EAAAAAY', proxy)
                token = gettoken.get_login(cookie)['access_token']
            
            fbtk = FacebookToken(token=token, proxy=proxy)
            cookie = fbtk.get_cookie()
            print(cookie)
            crawler = FacebookCrawler(url, cookie, proxy)
            comment_count, reaction_count = fbtk.getCount(crawler.owner_id + '_' + crawler.id)
            comments = fbtk.getComments(crawler.owner_id + '_' + crawler.id)


        print(f"[{datetime.now()}] 📊 Post {post_name} có {comment_count} comment và {reaction_count} reaction")

        # Cập nhật thông tin post
        db.bulk_update(
            'posts',
            [{
                'post_name': post_name,
                'reaction_count': crawler.reaction_count,
                'comment_count': crawler.comment_count,
                'last_comment': comments[0]['created_time'] if comments else None
            }],
            'post_name'
        )

        
        if comments:
            comment_data = db.fetch_data('comments')
            existing_comment_ids = {c[0] for c in comment_data}  # Giả sử comment_id nằm ở vị trí đầu tiên trong tuple

            # Lọc ra các comment chưa có trong database
            new_comments = [
                (c['comment_id'], crawler.id, post_name, c['author_id'], c['author_name'], 
                c['author_avatar'], c['content'], '', '', c['created_time'], username)
                for c in comments if c['comment_id'] not in existing_comment_ids
            ]
            db.add_data(
                'comments',
                ['comment_id', 'post_id', 'post_name', 'author_id', 'author_name', 
                 'author_avatar', 'content', 'info', 'phone_number', 'created_time', 'username'],
                new_comments
            )
            print(f"[{datetime.now()}] 💾 Đã lưu {len(new_comments)} comment mới cho {post_name}")

        db.close()
        sleep(delay/1000)  # Convert ms to seconds
        print(f"[{datetime.now()}] ⏳ Hoàn thành xử lý {post_name}. Tạm dừng {delay}ms")

    except Exception as e:
        print(f"\n[{datetime.now()}] ❌ Lỗi khi xử lý {post_name}:")
        traceback.print_exc()
        sleep(10)  # Tránh spam lỗi

def process_post(post_data):
    while True:
        try:
            # Lấy dữ liệu mới nhất mỗi lần lặp
            post_name = post_data[1]
            url = post_data[2]
            username = post_data[-1]
            delay = post_data[-3]

            db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
            tokens = db.fetch_data('tokens') or []
            cookies = db.fetch_data('cookies') or []
            proxies = db.fetch_data('proxies') or []
            db.close()

            # Random chọn proxy
            proxy = random.choice(proxies)[0] if proxies else None
            
            # Random chọn token hoặc cookie
            auth = None
            if tokens or cookies:
                if tokens and cookies:
                    auth = random.choice(["token", "cookie"])
                else:
                    auth = "token" if tokens else "cookie"
                
                if auth == "token":
                    token = random.choice(tokens)[1]
                    cookie = None
                else:
                    cookie = random.choice(cookies)[1]
                    token = None

            threading.Thread(target=comment_progress, args=(url, post_name, username, delay, token, cookie, proxy)).start()
            sleep(delay/1000)  # Convert ms to seconds

        except Exception as e:
            print(f"\n[{datetime.now()}] ❌ Lỗi luồng xử lý {post_data[1]}:")
            traceback.print_exc()
            sleep(5)  # Đợi 5s trước khi thử lại

def cookie_progress(cookie, cookie_id, proxy):
    db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
    
    gettoken = FacebookTokenExtractor('EAAAAAY', proxy=proxy)
    try:
        token = gettoken.get_login(cookie)['access_token']
        db.bulk_update(
            'tokens',
            [{'token_id': cookie_id, 'token': token}],
            'token_id'
        )
    except:
        db.bulk_update(
            'cookies',
            [{'cookie_id': cookie_id, 'status': 'die'}],
            'cookie_id'
        )

    db.close()

def progress_cookie():
    db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
    while True:
        threads = []
        proxies = db.fetch_data('proxies') or []
        proxy = random.choice(proxies)[0] if proxies else None

        cookies = db.fetch_data('cookies')
        for ck in cookies:
            cookie = ck[1]
            cookie_id = ck[0]
            t = threading.Thread(target=cookie_progress, args=(cookie, cookie_id, proxy))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()

        sleep(300)

def main():
    print(f"[{datetime.now()}] 🚀 Khởi động hệ thống...")
    threading.Thread(target=progress_cookie).start()
    while True:
        try:
            # Lấy danh sách post mới mỗi 30 giây
            db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
            current_posts = {post[1]: post for post in db.fetch_data('posts')}
            db.close()

            # Kiểm tra và tạo luồng mới
            active_threads = {t.name: t for t in threading.enumerate() if isinstance(t, threading.Thread)}
            
            for post_name, post in current_posts.items():
                if post_name not in active_threads:
                    print(f"[{datetime.now()}] 🧵 Tạo luồng mới cho: {post_name}")
                    thread = threading.Thread(
                        target=process_post, 
                        args=(post,),
                        name=post_name,
                        daemon=True
                    )
                    thread.start()

            sleep(30)  # Cập nhật danh sách post mỗi 30 giây

        except Exception as e:
            print(f"\n[{datetime.now()}] ❌ Lỗi chính:")
            traceback.print_exc()
            sleep(60)

if __name__ == "__main__":
    main()