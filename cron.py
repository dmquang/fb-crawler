from core.api import *
import threading
from time import sleep
from utils import DatabaseManager
from config import *
import random
import traceback
from datetime import datetime

def comment_progress(url, post_name, post_id, username, delay, token=None, cookie=None, proxy=None):
    try:
        print(f"\n[{datetime.now()}] 🔄 Bắt đầu xử lý post: {post_name}")
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        
        comment_count, reaction_count = None, None
        # Lấy proxy từ database
        proxies = db.fetch_data('proxies', condition=f"username = 'admin'")
        proxy = random.choice(proxies)[0] if proxies else None
        try:
            try:
                    
                # Khởi tạo FacebookCrawler
                crawler = FacebookCrawler(url=url, proxy=proxy)
                comments = crawler.getComments()
                comment_count, reaction_count = crawler.comment_count, crawler.reaction_count

            except Exception:
                # Nếu crawler thất bại, dùng token hoặc cookie
                tokens = db.fetch_data('tokens') or []
                cookies = db.fetch_data('cookies') or []
                token = random.choice(tokens)[1] if tokens else None
                cookie = random.choice(cookies)[1] if cookies else None

                if token:
                    print(f"[{datetime.now()}] 🔑 Sử dụng token cho {post_name}")
                    fbtk = FacebookToken(token=token, proxy=proxy)
                    comments = fbtk.getComments(post_id)
                else:
                    crawler = FacebookCrawler(url, cookie, proxy)
                    comments = crawler.getComments()
                    comment_count, reaction_count = crawler.comment_count, crawler.reaction_count

        except:
            print(f"[{datetime.now()}] 🌐 Proxy {proxy} bị giới hạn")
            return 


        print(f"[{datetime.now()}] 📊 Post {post_name} có {comment_count} comment và {reaction_count} reaction")

        # Cập nhật thông tin post
        db.bulk_update(
            'posts',
            [{
                'post_name': post_name,
                'reaction_count': reaction_count if reaction_count else 0,
                'comment_count': comment_count if comment_count else 0,
                'last_comment': comments[0]['created_time'] if comments else None,
            }],
            'post_name'
        )

        if comments:
            comment_data = db.fetch_data('comments')
            existing_comment_ids = {c[0] for c in comment_data}  # Giả sử comment_id nằm ở vị trí đầu tiên trong tuple

            # Lọc ra các comment chưa có trong database
            new_comments = [
                (c['comment_id'], post_id, post_name, c['author_id'], c['author_name'], 
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
            post_id = post_data[0]
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

            threading.Thread(target=comment_progress, args=(url, post_name, post_id, username, delay, token, cookie, proxy)).start()
            sleep(delay/1000)  # Convert ms to seconds

        except Exception as e:
            print(f"\n[{datetime.now()}] ❌ Lỗi luồng xử lý {post_data[1]}:")
            traceback.print_exc()
            sleep(5)  # Đợi 5s trước khi thử lại


def token_progress(token_id, token, proxy):
    db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
    tk = FacebookToken(token, proxy)
    if tk.me() == 'Invalid Token':
        db.bulk_update(
            'tokens',
            [{'token_id': token_id, 'token': token, 'status': 'die'}],
            'token_id'
        )
    db.close()

def progress_token():
    db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
    while True:
        threads = []
        proxies = db.fetch_data('proxies') or []
        proxy = random.choice(proxies)[0] if proxies else None

        tokens = db.fetch_data('tokens', condition=f"status = 'live'")
        for tk in tokens:
            token_id = tk[0]
            token = tk[1]
            thread = threading.Thread(target=token_progress, args=(token_id, token, proxy))
            threads.append(thread)
            thread.start()
            sleep(0.1)  # Đợi 100ms trước khi tạo luồng tiếp theo
        
        for t in threads:
            t.join()
    
        sleep(120)

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

        cookies = db.fetch_data('cookies', condition=f"status = 'live'")
        for ck in cookies:
            cookie = ck[1]
            cookie_id = ck[0]
            t = threading.Thread(target=cookie_progress, args=(cookie, cookie_id, proxy))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()

        sleep(120)


def main():
    print(f"[{datetime.now()}] 🚀 Khởi động hệ thống...")
    threading.Thread(target=progress_cookie).start()
    threading.Thread(target=progress_token).start()
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