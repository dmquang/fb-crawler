from flask import Flask, render_template, jsonify, request, redirect, url_for
from core.api import FacebookCrawler, FacebookAuthencation, CheckProxies, FacebookToken, FacebookTokenExtractor
from utils import DatabaseManager
from config import *
import time
import jwt
from functools import wraps
import pandas as pd
from io import BytesIO
from flask import Response
import random
from datetime import datetime, timedelta
from flask_socketio import SocketIO, emit

# Khởi tạo Flask app
app = Flask(__name__)
socketio = SocketIO(app)

SECRET_KEY = 'Hoàng Chương'  # Change this to a secure secret key

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user = data['username']
        except:
            return jsonify({'error': 'Token is invalid'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    return render_template('logout.html')


@app.route('/dashboard')
def dashboard():
    return redirect(url_for('posts_page'))

@app.route('/posts')
def posts_page():
    return render_template('posts.html')

@app.route('/posts-off')
def postsoff_page():
    return render_template('/posts-off.html')

@app.route('/cookies')
def cookies():
    return render_template('cookies.html')

@app.route('/proxies')
def proxies():
    return render_template('proxies.html')

@socketio.on('connect', namespace='/ws/comments')
def handle_connect():
    print('Client connected to comments WebSocket')
    emit('message', {'data': 'Connected to WebSocket'})

@app.route('/comments')
def comments():
    return render_template('comments.html')

@socketio.on('get_comments', namespace='/ws/comments')
def send_comments(data):
    try:
        username = data.get('username', '')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        page = int(data.get('page', 1))  # Trang hiện tại
        limit = int(data.get('limit', 30))  # Số comment mỗi lần tải
        offset = (page - 1) * limit  # Tính offset cho SQL

        if not username:
            emit('error', {'error': 'Username is required'})
            return

        if start_date == 'null':
            start_date = None
        if end_date == 'null':
            end_date = None

        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

        conditions = []
        if username != 'admin':
            conditions.append(f"username = '{username}'")
        if start_date:
            conditions.append(f"created_time >= UNIX_TIMESTAMP('{start_date} 00:00:00')")
        if end_date:
            conditions.append(f"created_time <= UNIX_TIMESTAMP('{end_date} 23:59:59')")

        condition_query = ' AND '.join(conditions) if conditions else '1=1'
        query = f"""
            SELECT * FROM comments 
            WHERE {condition_query} 
            ORDER BY created_time DESC 
            LIMIT {limit} OFFSET {offset}
        """

        comments = db.execute_query(query)
        db.close()

        comments_data = [
            {
                'comment_id': comment[0],
                'post_id': comment[1],
                'post_name': comment[2],
                'author_id': comment[3],
                'author_name': comment[4],
                'author_avatar': comment[5],
                'content': comment[6],
                'info': comment[7],
                'phone_number': comment[8],
                'created_time': comment[9],
                'username': comment[10],
                'note': comment[11],
            }
            for comment in comments
        ]

        # Kiểm tra còn comment hay không
        has_more = len(comments_data) == limit

        emit('comments', {'comments': comments_data, 'has_more': has_more})
    except Exception as e:
        emit('error', {'error': str(e)})



@app.route('/api/comments/export')
def export_comments():
    try:
        # Lấy các tham số từ query parameters
        username = request.args.get('username')
        start_date = request.args.get('start_date')  # Ngày bắt đầu (YYYY-MM-DD)
        end_date = request.args.get('end_date')      # Ngày kết thúc (YYYY-MM-DD)

        # Kiểm tra username
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        
        # Kiểm tra nếu start_date và end_date là "null"
        if start_date == 'null':
            start_date = None
        if end_date == 'null':
            end_date = None

        # Kết nối database
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

        # Xây dựng điều kiện lọc
        conditions = []
        
        # Lọc theo username, ngoại trừ 'admin'
        if username != 'admin':
            conditions.append(f"username = '{username}'")

        # Lọc theo ngày nếu có, nếu không có thì không lọc theo ngày
        if start_date and end_date:
            conditions.append(f"created_time >= UNIX_TIMESTAMP('{start_date} 00:00:00')")
            conditions.append(f"created_time <= UNIX_TIMESTAMP('{end_date} 23:59:59')")
        elif start_date:
            conditions.append(f"created_time >= UNIX_TIMESTAMP('{start_date} 00:00:00')")
        elif end_date:
            conditions.append(f"created_time <= UNIX_TIMESTAMP('{end_date} 23:59:59')")

        # Kết hợp các điều kiện
        condition_query = ' AND '.join(conditions) if conditions else ''

        # Fetch dữ liệu từ database
        comments = db.fetch_data('comments', condition=condition_query)
        db.close()

        # Chuyển dữ liệu thành danh sách dictionary
        comments_data = [
            {
                'comment_id': comment[0],
                'post_id': comment[1],
                'post_name': comment[2],
                'author_id': comment[3],
                'author_name': comment[4],
                'author_avatar': comment[5],
                'content': comment[6],
                'info': comment[7],
                'phone_number': comment[8],
                'created_time': comment[9],
                'username': comment[10],
            }
            for comment in comments
        ]

        # Tạo DataFrame từ dữ liệu
        df = pd.DataFrame(comments_data)

        # Tạo một đối tượng BytesIO để lưu trữ tệp Excel trong bộ nhớ
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Comments')

        output.seek(0)

        # Trả về file Excel dưới dạng response
        return Response(output, 
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                        headers={"Content-Disposition": "attachment; filename=comments.xlsx"})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/comments/hide', methods=['POST'])
def hide_comment():
    db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
    comment_id = request.get_json()['comment_id']


    

@app.route('/api/posts/toggle', methods=['POST'])
def toggle_post():
    try:
        data = request.get_json()
        post_name = data.get('post_name')
        
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        
        # Lấy thông tin post hiện tại
        post_sql = "SELECT * FROM posts WHERE post_name = %s"
        post = db.execute_query(post_sql, (post_name,))
        
        # Chuyển post sang bảng stopped_posts nếu đang active
        if post[0][8] == 'active':  # Giả sử status là cột thứ 9
            insert_sql = """
                INSERT INTO stopped_posts 
                SELECT *, UNIX_TIMESTAMP() as stopped_time 
                FROM posts WHERE post_name = %s
            """
            db.execute_query(insert_sql, (post_name,))
            
            # Cập nhật status trong posts
            update_sql = "UPDATE posts SET status = 'stopped' WHERE post_name = %s"
            db.execute_query(update_sql, (post_name,))
        else:
            # Xóa khỏi stopped_posts và cập nhật status
            delete_sql = "DELETE FROM stopped_posts WHERE post_name = %s"
            db.execute_query(delete_sql, (post_name,))
            
            update_sql = "UPDATE posts SET status = 'active' WHERE post_name = %s"
            db.execute_query(update_sql, (post_name,))
        
        db.close()
        return jsonify({'success': True, 'message': 'Post status updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/posts/delete', methods=['DELETE', 'POST'])
def delete_post():
    try:
        data = request.get_json()
        post_name = data['post_name']

        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        
        db.delete_data('posts', f"post_name = '{post_name}'")
        db.delete_data('stopped_posts', f"post_name = '{post_name}'")

        db.close()

        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts/stop', methods=['POST'])
def stop_post():
    try:
        data = request.get_json()
        post_name = data['post_name']
        
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

        # Fetch the post details
        post_sql = "SELECT * FROM posts WHERE post_name = %s"
        post = db.execute_query(post_sql, (post_name,))[0]
        #('908470518127187', 'rap', 'https://www.facebook.com/share/v/18tef9pgYq/', 2043, 1333, 1737870768, 1737961517, 10000, 'active', 'qquang72')
        print(post)
        username = post[-1]
        
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        db.add_data('stopped_posts', ['post_id', 'post_name', 'post_url', 'reaction_count', 'comment_count', 'time_created', 'last_comment', 'delay', 'status', 'username', 'stopped_time'], [(post[0], post[1], post[2], post[3], post[4], post[5], post[6], post[7], 'stopped', username, f'{int(time.time())}')])

        # Delete the post from the original table
        db.delete_data('posts', f"post_name = '{post_name}'")

        db.close()

        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@app.route('/api/stopped-posts', methods=['POST'])
def get_stopped_posts_v2():  # Renamed function to avoid conflict
    try:
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        
        username = request.get_json()['username']

        if username != 'admin':
            stopped_posts_sql = f"SELECT * FROM stopped_posts WHERE username = '{username}'"
        else:
            stopped_posts_sql = "SELECT * FROM stopped_posts"
        posts = db.execute_query(stopped_posts_sql)
        db.close()

        return jsonify({
            'stopped_posts': [{
                'id': p[0],
                'post_name': p[1],
                'post_url': p[2],
                'reaction_count': p[3],
                'comment_count': p[4],
                'time_created': p[5],
                'delay': p[7],
                'status': p[8],
                'username': p[9],
                'stopped_time': p[10]
            } for p in posts]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/posts/edit', methods=['POST'])
def edit_post():
    try:
        data = request.get_json()
        post_name = data['post_name']
        delay = data['delay']
        
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        
        # Update post delay in the database
        update_sql = """
            UPDATE posts 
            SET delay = %s 
            WHERE post_name = %s
        """
        db.execute_query(update_sql, (delay, post_name))
        db.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/posts/add', methods=['POST'])
def add_post():
    try:
        # Nhận dữ liệu từ request
        data = request.get_json()
        post_name = data.get('post_name')
        post_url = data.get('post_url')
        username = data.get('username')

        if not post_name or not post_url or not username:
            return jsonify({'success': False, 'error': 'Thiếu thông tin đầu vào'}), 400

        # Kết nối database
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        if post_url in [p[2] for p in db.fetch_data('posts')]:
            db.close()
            return jsonify({'success': False, 'error': 'Bài viết đã tồn tại'}), 400
        
        try:
            try:
                status = 'active'
                # Lấy proxy từ database
                proxies = db.fetch_data('proxies') or []
                if not proxies:
                    return jsonify({'success': False, 'error': f'Không có proxy trong db!'}), 400
                
                proxy = random.choice(proxies)[0] if proxies else None
                
                # Khởi tạo FacebookCrawler
                crawler = FacebookCrawler(url=post_url, proxy=proxy)
                comments = crawler.getComments()
                comment_count, reaction_count = crawler.comment_count, crawler.reaction_count


            except:
                status = 'private'
                # Nếu crawler thất bại, dùng token hoặc cookie
                tokens = db.fetch_data('tokens') or []
                cookies = db.fetch_data('cookies') or []
                token = random.choice(tokens)[1] if tokens else None
                cookie = random.choice(cookies)[1] if cookies else None

                if token:
                    try:
                        print(f"[{datetime.now()}] 🔑 Sử dụng token cho {post_name}")
                        fbtk = FacebookToken(token=token, proxy=proxy)
                        cookie = fbtk.get_cookie()
                        crawler = FacebookCrawler(post_url, cookie, proxy)
                        try:
                            comment_count, reaction_count = fbtk.getCount(f"{crawler.owner_id}_{crawler.id}")
                        except:
                            comment_count, reaction_count = fbtk.getCount(f"{crawler.id}")
                        comments = fbtk.getComments(f"{crawler.id}")
                    except:
                        if cookie:
                            crawler = FacebookCrawler(post_url, cookie, proxy)
                            comments = crawler.getComments()
                            comment_count, reaction_count = crawler.comment_count, crawler.reaction_count

                if cookie:
                    if comments:
                        pass
                    else:
                        crawler = FacebookCrawler(post_url, cookie, proxy)
                        comments = crawler.getComments()
                        comment_count, reaction_count = crawler.comment_count, crawler.reaction_count

        except:
            return jsonify({'success': False, 'error': f'Something wrong, please try again! Proxy: {proxy}'}), 400

        # Lưu thông tin bài viết vào database
        print(status)
        post_id = crawler.id
        
        time_created = int(time.time())
        print((post_id, post_name, post_url, username, int(reaction_count), int(comment_count), time_created, comments[0]['created_time'] if comments else '0', status, SCAN_DELAY))

        db.add_data(
            'posts',
            columns=['post_id', 'post_name', 'post_url', 'username', 'reaction_count', 'comment_count', 'time_created', 'last_comment', 'status', 'delay'],
            values_list=[(post_id, post_name, post_url, username, int(reaction_count), int(comment_count), time_created, comments[0]['created_time'] if comments else '0', status, SCAN_DELAY)]
        )

        # Lưu comment vào database nếu có
        if comments:
            existing_comment_ids = {c[0] for c in db.fetch_data('comments')}
            new_comments = [
                (c['comment_id'], crawler.id, post_name, c['author_id'], c['author_name'],
                 c['author_avatar'], c['content'], '', '', c['created_time'], username)
                for c in comments if c['comment_id'] not in existing_comment_ids
            ]
            if new_comments:
                db.add_data(
                    'comments',
                    ['comment_id', 'post_id', 'post_name', 'author_id', 'author_name',
                     'author_avatar', 'content', 'info', 'phone_number', 'created_time', 'username'],
                    new_comments
                )
                print(f"[{datetime.now()}] 💾 Đã lưu {len(new_comments)} comment mới cho {post_name}")

        
        db.close()
        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

    finally:
        db.close()  


@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        # Tạo token JWT

        if username == ADMIN_USERNAME and password  == ADMIN_PASSWORD:
            token = jwt.encode({
                'username': username,
                'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
            }, SECRET_KEY, algorithm='HS256')

            return jsonify({
                    'success': True,
                    'token': token,
                    'username': username,
                    'is_admin': True
                }), 200

        # Kết nối tới database admin để xác thực người dùng
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='admin')
        
        # Kiểm tra thông tin đăng nhập
        login_sql = "SELECT * FROM admin.users WHERE username = %s AND password = %s"
        result = db.execute_query(login_sql, (username, password))
        db.close()
        if result:
            user = result[0]
            
            # Kiểm tra thời gian hết hạn
            current_time = int(time.time())
            if user[5] < current_time:
                return jsonify({
                    'success': False, 
                    'error': 'Account has expired'
                }), 401
            
            # Tạo token JWT
            token = jwt.encode({
                'username': username,
                'is_admin': user[6] == 'admin',  # Kiểm tra quyền admin
                'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)
            }, SECRET_KEY, algorithm='HS256')
            
            return jsonify({
                'success': True,
                'token': token,
                'username': username,
                'is_admin': user[6] == 'admin'
            }), 200
        else:
            return jsonify({
                'success': False, 
                'error': 'Invalid username or password'
            }), 401
            
    except Exception as e:
        return jsonify({
            'success': False, 
            'error': str(e)
        }), 500

# Add admin check decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'Unauthorized'}), 401
            
        try:
            token = auth_header.split(" ")[1]
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            
            # Check if user is admin from token
            if not data.get('is_admin'):
                return jsonify({'error': 'Admin privileges required'}), 403
                
        except:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated_function

# Route để hiển thị trang admin
@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# API lấy danh sách người dùng
@app.route('/api/admin/users')
def get_users():
    try:
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='admin')
        
        print("Fetching users from admin database...")
        
        users_sql = "SELECT * FROM users"
        users = db.execute_query(users_sql)
        
        print(f"Found {len(users) if users else 0} users")
        db.close()
        
        if not users:
            return jsonify({'users': []}), 200
            
        return jsonify({
            'users': [{
                'username': user[0],
                'link_scan_limit': user[2],
                'link_follow_limit': user[3],
                'link_hide_limit': user[4],
                'expire_time': user[5],
                'permission': user[6]
            } for user in users if user[0] != 'admin']
        }), 200
        
    except Exception as e:
        print(f"Error in get_users: {str(e)}")
        return jsonify({'error': str(e)}), 500

# API thêm người dùng mới
@app.route('/api/admin/users', methods=['POST'])
def add_user():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        scan_limit = data.get('link_scan_limit')
        follow_limit = data.get('link_follow_limit')
        hide_limit = data.get('link_hide_limit')
        expire_days = data.get('expire_days')
        permission = 'user'  # Default permission for new users
        
        if not all([username, password, scan_limit, follow_limit, hide_limit, expire_days]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
            
        expire_time = int(time.time() + (int(expire_days) * 24 * 60 * 60))
        
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='admin')
        
        # Kiểm tra nếu username đã tồn tại
        check_sql = "SELECT COUNT(*) FROM users WHERE username = %s"
        result = db.execute_query(check_sql, (username,))
        if result[0][0] > 0:
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
            
        # Chèn người dùng mới vào cơ sở dữ liệu
        insert_sql = """
            INSERT INTO users (username, password, link_scan_limit, link_follow_limit, 
                             link_hide_limit, expire_time, permission)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (username, password, scan_limit, follow_limit, hide_limit, expire_time, permission)
        db.execute_query(insert_sql, values)
        db.close()
        return jsonify({
            'success': True, 
            'message': 'User added successfully',
            'user': {
                'username': username,
                'link_scan_limit': scan_limit,
                'link_follow_limit': follow_limit,
                'link_hide_limit': hide_limit,
                'expire_time': expire_time,
                'permission': permission
            }
        }), 200
        
    except Exception as e:
        print('Error adding user:', str(e))
        return jsonify({'success': False, 'error': str(e)}), 500

# API cập nhật người dùng
@app.route('/api/admin/users/<username>', methods=['PUT'])
@admin_required
def update_user(username):
    try:
        data = request.get_json()
        scan_limit = data.get('link_scan_limit')
        follow_limit = data.get('link_follow_limit')
        hide_limit = data.get('link_hide_limit')
        expire_days = data.get('expire_days')
        permission = data.get('permission')
        password = data.get('password')
        
        expire_time = int(time.time() + (expire_days * 24 * 60 * 60))
        
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='admin')
        
        if password:
            update_sql = """
                UPDATE users 
                SET password = %s, link_scan_limit = %s, link_follow_limit = %s,
                    link_hide_limit = %s, expire_time = %s, permission = %s
                WHERE username = %s
            """
            values = (password, scan_limit, follow_limit, hide_limit, expire_time, permission, username)
        else:
            update_sql = """
                UPDATE users 
                SET link_scan_limit = %s, link_follow_limit = %s,
                    link_hide_limit = %s, expire_time = %s, permission = %s
                WHERE username = %s
            """
            values = (scan_limit, follow_limit, hide_limit, expire_time, permission, username)
            
        db.execute_query(update_sql, values)
        db.close()
        return jsonify({'success': True, 'message': 'User updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API xóa người dùng
@app.route('/api/admin/delete-user/', methods=['DELETE'])
def delete_user():
    try:
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='admin')
        username = request.get_json()['username']

        # Kiểm tra xem người dùng có tồn tại không
        check_sql = "SELECT COUNT(*) FROM users WHERE username = %s"
        result = db.execute_query(check_sql, (username,))
        if result[0][0] == 0:
            return jsonify({'error': 'User not found'}), 404
            
        # Xóa người dùng
        delete_sql = "DELETE FROM users WHERE username = %s"
        db.execute_query(delete_sql, (username,))
        db.close()
        return jsonify({'success': True, 'message': 'User deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_current_username():
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None  # or raise an error if needed

    token = auth_header.split(" ")[1]  # Extract the token from the header
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return data['username']  # Return the username from the decoded token
    except Exception as e:
        return None  # or handle the error as needed

@app.route('/api/user/all-posts', methods=['GET', 'POST'])
def get_user_posts():
    try:
        # Kết nối tới database user
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

        if request.method == 'POST':
            username = request.get_json()['username']
            # Lấy tất cả posts của user
            posts = db.fetch_data('posts', condition=f"username = '{username}'")
        else:
            posts = db.fetch_data('posts')

        db.close()
        
        return jsonify({
            'posts': [{
                'id': p[0],
                'post_name': p[1],
                'post_url': p[2],
                'reaction_count': p[3],
                'comment_count': p[4],
                'time_created': p[5],
                'last_comment': p[6],
                'delay': p[7],
                'status': p[8],
                'username': p[9]
            } for p in posts]
        }), 200
        
    except Exception as e:
        print(f"Error in get_user_posts: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/user/all-comments', methods=['GET', 'POST'])
def get_user_comments():
    try:
        # Kết nối tới database user
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

        if request.method == 'POST':
            username = request.get_json()['username']
            # Lấy tất cả posts của user
            comments = db.fetch_data('comments', condition=f"username = '{username}'")
        else:
            comments = db.fetch_data('comments')

        db.close()
        
        return jsonify({
            'comments': [{
                'id': c[0],
                'post_id': c[1],
                'post_name': c[2],
                'author_id': c[3],
                'author_name': c[4],
                'author_avatar': c[5],
                'content': c[6],
                'info': c[7],
                'phone_number': c[8],
                'created_time': c[9],
                'username': c[10]
            } for c in comments]
        }), 200
        
    except Exception as e:
        print(f"Error in get_user_posts: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/posts/off', methods=['GET'])
def get_stopped_posts():
    try:
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        
        # Fetch all stopped posts
        stopped_posts_sql = "SELECT * FROM stopped_posts"
        posts = db.execute_query(stopped_posts_sql)
        db.close()
        return jsonify({
            'stopped_posts': [{
                'id': p[0],
                'post_name': p[1],
                'post_url': p[2],
                'reaction_count': p[3],
                'comment_count': p[4],
                'time_created': p[5],
                'delay': p[7],
                'status': p[8],
                'username': p[9],
                'stopped_time': p[10]
            } for p in posts]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts/resume', methods=['POST'])
def resume_post():
    # Lấy thông tin post_name từ request
    post_name = request.get_json().get('post_name')

    if not post_name:
        return jsonify({'error': 'Missing post_name in request body'}), 400

    # Kết nối cơ sở dữ liệu
    db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

    # Lấy dữ liệu từ bảng `stopped_posts`
    stopped_posts = db.fetch_data(
        table='stopped_posts', 
        columns='post_id, post_name, post_url, reaction_count, comment_count, time_created, last_comment, delay, username',
        condition=f"post_name = '{post_name}'"
    )

    if not stopped_posts:
        return jsonify({'error': 'Post name is invalid or not stopped!'}), 404

    # Lấy dữ liệu của bài viết cần resume
    stopped_post_data = stopped_posts[0]

    # ('624818366721418', 'wibu', 'https://www.facebook.com/share/p/1A1zwXG9ba/', 4859, 530, 1737805103, None, 10000, 'admin')
    #'post_id', 'post_name', 'post_url', 'reaction_count', 'comment_count', 'time_created', 'last_comment', 'delay', 'status', 'username'
    # Chuyển bài viết vào bảng `posts`x
    try:
        # Thêm bài viết vào bảng `posts`
        db.add_data(
            table='posts',
            columns=['post_id', 'post_name', 'post_url', 'reaction_count', 'comment_count', 'time_created', 'last_comment', 'delay', 'status', 'username'],
            values_list=[(
                stopped_post_data[0],  # post_id
                stopped_post_data[1],  # post_name
                stopped_post_data[2],  # post_url
                stopped_post_data[3],  # reaction_count
                stopped_post_data[4],  # comment_count
                stopped_post_data[5],  # time_created
                stopped_post_data[6],  # last_comment
                stopped_post_data[7],  # delay
                'active',              # status
                stopped_post_data[-1]   # username
            )]
        )

        # Xóa bài viết khỏi bảng `stopped_posts`
        db.delete_data(
            table='stopped_posts',
            condition=f"post_name = '{post_name}'"
        )
        db.close()
        return jsonify({'message': 'Post successfully resumed!'}), 200

    except Exception as e:
        return jsonify({'error': 'An error occurred while resuming the post'}), 500


@app.route('/api/user/cookies', methods=['GET', 'POST', 'DELETE'])  # Đã sửa methods
def user_cookies():
    try:
        if request.method == 'GET':
            db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
            username = request.args.get('user')
            cookies = db.fetch_data('cookies', condition=f"username = '{username}'")
            db.close()
            return jsonify({
                'cookies': [{
                    'cookie_id': ck[0],
                    'cookie': ck[1],
                    'status': ck[2],
                    'username': ck[3]
                } for ck in cookies]
            }), 200
            

        elif request.method == 'POST':  # Đã đổi từ 'ADD' sang 'POST'
            db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
            data = request.get_json()
            if 'cookie' not in data:
                return jsonify({'error': 'Missing cookie in request data'}), 400
                
            cookie = data['cookie']
            username = data['username']
            proxies = db.fetch_data('proxies', condition=f"username = 'admin' AND status = 'Active'")
            if proxies != []:
                proxy = random.choice(proxies)[0]
                fb = FacebookAuthencation(cookie, proxy=proxy)
            else:
                fb = FacebookAuthencation(cookie)
            
            if not fb.user_id:
                return jsonify({'error': 'Invalid cookie or cookie is expired!'}), 400
                
            db.add_data('cookies', ['cookie_id', 'cookie', 'status', 'username'], 
                       [(fb.user_id, cookie, 'Live', username)])
            db.close()
            return jsonify({'message': 'Cookie added successfully!'}), 200

        elif request.method == 'DELETE':
            db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
            data = request.get_json()
            if 'cookie' not in data:
                return jsonify({'error': 'Missing cookie in request data'}), 400
            
            cookie = data['cookie']
                
            db.delete_data('cookies', condition=f"cookie = '{cookie}'")
            db.close()
            return jsonify({'message': 'Cookie deleted successfully!'}), 200

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/user/proxies', methods=['GET', 'POST', 'DELETE'])
def user_proxies():
    try:
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

        if request.method == 'GET':
            username = request.args.get('user')
            proxies = db.fetch_data('proxies', condition=f"username = '{username}'")
            db.close()
            return jsonify({
                'proxies': [{
                    'proxy': p[0],
                    'status': p[1],
                    'username': p[2]
                } for p in proxies]
            }), 200

        elif request.method == 'POST':
            data = request.get_json()
            if 'proxy' not in data or 'username' not in data:
                return jsonify({'error': 'Missing proxy or username in request data'}), 400

            proxy = data['proxy']
            username = data['username']
            if not CheckProxies.check(proxy):
                return jsonify({'error': 'Proxy is invalid or not working!'}), 500
            
            db.add_data('proxies', ['proxy', 'status', 'username'], [(proxy, 'Active', username)])
            db.close()
            return jsonify({'message': 'Proxy added successfully!'}), 200

        elif request.method == 'DELETE':
            data = request.get_json()
            if 'proxy' not in data or 'username' not in data:
                return jsonify({'error': 'Missing proxy or username in request data'}), 400

            proxy = data['proxy']
            username = data['username']

            db.delete_data('proxies', condition=f"proxy = '{proxy}' AND username = '{username}'")
            db.close()
            return jsonify({'message': 'Proxy deleted successfully!'}), 200

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/user/tokens', methods=['GET', 'POST', 'DELETE'])
def user_tokens():
    try:
        db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

        if request.method == 'GET':
            username = request.args.get('user')
            data = db.fetch_data('tokens', condition=f"WHERE username = '{username}'" if username != 'admin' else '')
            db.close()

            return jsonify({'tokens': [{
                'token_id': t[0],
                'token': t[1],
                'status': t[2],
                'username': t[3]
            } for t in data ]})
        
        elif request.method == 'POST':
            username = request.get_json()['username']
            dataInput = request.get_json()['data']
            type = request.get_json()['type']
            
            proxy = None
            proxies = db.fetch_data('proxies', condition=f"status = 'Active'")
            if proxies != []:
                proxy = random.choice(proxies)[0]
            

            if type == 'token':
                token = dataInput
            else:
                gettoken = FacebookTokenExtractor('EAAAAAY', proxy)
                token = gettoken.get_login(dataInput)['access_token']
                
            fb_token = FacebookToken(token=token, proxy=proxy)

            token_id = fb_token.me()
            if token_id == 'Invalid Token':
                return jsonify({'error': 'Invalid token'}), 400

            db.add_data(
                'tokens',
                columns=['token_id', 'token', 'status', 'username'],
                values_list=[(token_id, token, 'live', username)]
            )
            db.close()

            return jsonify({'message': 'Token added successfully!'}), 200
        
        elif request.method == 'DELETE':
            username = request.get_json()['username']
            token_id = request.get_json()['token_id']

            db.delete_data('tokens', condition=f"token_id = '{token_id}'")
            db.close()

            return jsonify({'message': 'Token deleted successfully!'}), 200
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/tokens')
def tokens():
    return render_template('tokens.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7220)
