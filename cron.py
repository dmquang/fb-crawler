import asyncio
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from utils import DatabaseManager
from core.api import FacebookCrawler, FacebookAuthencation, CheckProxies
from config import *

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class CronJob:
    def __init__(self):
        try:
            self.db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
            self.semaphore = asyncio.Semaphore(20)  # Giới hạn số lượng tác vụ đồng thời
            self.thread_pool = ThreadPoolExecutor(max_workers=20)  # Tạo một ThreadPoolExecutor với 20 luồng
        except Exception as e:
            logging.error(f"Failed to initialize CronJob: {e}")
            raise

    async def run(self):
        logging.info("Cron job started.")
        while True:
            try:
                tasks = [
                    self.scan_comments(),
                    self.check_cookies(),
                    self.check_proxies()
                ]
                await asyncio.gather(*tasks)
                await asyncio.sleep(SCAN_DELAY * 0.001)
            except Exception as e:
                logging.critical(f"Fatal error in main loop: {e}. Restarting...")
                await asyncio.sleep(5)

    async def scan_comments(self):
        await self._scan_posts("posts", self._scanComments)

    async def _scan_posts(self, table, scan_function):
        try:
            posts = self.db.fetch_data(table)
            if not posts:
                logging.info(f"No posts found in {table}.")
                return

            logging.info(f"Fetched {len(posts)} posts from {table}.")
            tasks = [
                self._run_with_semaphore(scan_function, post[1], self._get_proxy(post[9] if table == "posts" else None))
                for post in posts
            ]
            await asyncio.gather(*tasks)
        except Exception as e:
            logging.error(f"An error occurred in _scan_posts ({table}): {e}")

    async def _run_with_semaphore(self, func, *args, **kwargs):
        async with self.semaphore:
            await func(*args, **kwargs)

    async def check_cookies(self):
        await self._check_items("cookies", self._checkCookie)

    async def check_proxies(self):
        await self._check_items("proxies", self._checkProxy)

    async def _check_items(self, table, check_function):
        try:
            condition = "status = 'Active'" if table == "proxies" else "status = 'live'"
            items = self.db.fetch_data(table, condition=condition)

            if not items:
                logging.info(f"No {table} to check.")
                return

            logging.info(f"Checking {len(items)} {table}.")
            tasks = [self._run_with_semaphore(check_function, item[1]) for item in items]
            await asyncio.gather(*tasks)
        except Exception as e:
            logging.error(f"An error occurred in _check_items ({table}): {e}")

    async def _scanComments(self, post_name, proxy=None):
        # Chạy _process_post trong một luồng riêng
        await asyncio.get_event_loop().run_in_executor(
            self.thread_pool,  # Sử dụng ThreadPoolExecutor
            self._run_process_post,  # Gọi hàm wrapper
            post_name, proxy, "posts"
        )

    def _run_process_post(self, post_name, proxy, update_table):
        # Tạo một event loop mới trong luồng riêng
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._process_post(post_name, proxy, update_table))
        except Exception as e:
            logging.error(f"Error in _run_process_post: {e}")
        finally:
            loop.close()

    async def _process_post(self, post_name, proxy, update_table, delay=0):
        try:
            logging.info(f"Scanning comments for post: {post_name}")
            data = self.db.fetch_data('posts', condition=f"post_name = '{post_name}'")

            if not data:
                return

            username, post_url = data[0][9], data[0][2]

            try:
                crawler = FacebookCrawler(url=post_url, proxy=proxy)
                reaction_count, comment_count, comments = crawler.reaction_count, crawler.comment_count, crawler.getComments()
            except Exception as e:
                cookies = self.db.fetch_data('cookies', condition="username = 'admin' AND status = 'live'")
                cookie = random.choice(cookies)[1]
                crawler = FacebookCrawler(url=post_url, cookie=cookie, proxy=proxy)
                reaction_count, comment_count, comments = crawler.getComments()
                if comments is None:
                    return

            last_comment = comments[0]['created_time'] if comments else None
            self.db.bulk_update(update_table, [{'post_name': post_name, 'reaction_count': reaction_count, 'comment_count': comment_count, 'last_comment': last_comment}], 'post_name')

            tasks = [self._insert_comment(comment, post_name, username) for comment in comments]
            await asyncio.gather(*tasks)

            logging.info(f"Finished scanning comments for post: {post_name}")
        except Exception as e:
            logging.error(f"An error occurred while scanning comments for post {post_name}: {e}")

    async def _insert_comment(self, comment, post_name, username):
        try:
            comment_id = comment['comment_id']
            if self.db.fetch_data('comments', condition=f"comment_id = '{comment_id}'"):
                logging.info(f"Comment {comment_id} already exists, skipping.")
                return

            self.db.add_data(
                'comments',
                ['comment_id', 'post_id', 'post_name', 'author_id', 'author_name', 'author_avatar', 'content', 'created_time', 'username'],
                [(comment['comment_id'], comment['post_id'], post_name, comment['author_id'], comment['author_name'], comment['author_avatar'], comment['content'], comment['created_time'], username)]
            )
        except Exception as e:
            logging.error(f"Error inserting comment {comment['comment_id']}: {e}")

    async def _checkCookie(self, cookie):
        try:
            fb = FacebookAuthencation(cookie)
            if not fb.user_id:
                self.db.bulk_update('cookies', [{'cookie': cookie, 'status': 'die'}], 'cookie')
        except Exception as e:
            logging.error(f"Error checking cookie {cookie}: {e}")

    async def _checkProxy(self, proxy):
        try:
            if not CheckProxies.check(proxy):
                self.db.bulk_update('proxies', [{'proxy': proxy, 'status': 'unactive'}], 'proxy')
        except Exception as e:
            logging.error(f"Error checking proxy {proxy}: {e}")

    def _get_proxy(self, username=None):
        try:
            proxies = self.db.fetch_data('proxies', condition=f"username = '{username}' AND status = 'Active'") if username else []
            if not proxies:
                proxies = self.db.fetch_data('proxies', condition="username = 'admin' AND status = 'Active'")
            return random.choice(proxies)[0] if proxies else None
        except Exception as e:
            logging.error(f"Error fetching proxy for username {username}: {e}")
            return None


if __name__ == "__main__":
    cron = CronJob()
    asyncio.run(cron.run())