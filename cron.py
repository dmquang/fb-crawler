import os
import sys
import time
import random
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from utils import DatabaseManager
from core.api import FacebookCrawler, FacebookAuthencation, CheckProxies
from config import *

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class CronJob:
    def __init__(self):
        try:
            self.db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')
        except Exception as e:
            logging.error(f"Failed to initialize CronJob: {e}")
            sys.exit(1)

    def main(self):
        last_scan_off, last_check_cookie, last_check_proxy = 0, 0, 0
        logging.info("Cron job started.")

        while True:
            try:
                current_time = time.time()

                # Scan active posts
                self.scan_comments()

                # Scan stopped posts every 20 minutes
                if current_time - last_scan_off >= 1200:
                    self.scan_comments_off()
                    last_scan_off = current_time

                # Check cookies every 1 hour
                if current_time - last_check_cookie >= 3600:
                    self.check_cookies()
                    last_check_cookie = current_time

                # Check proxies every 10 minutes
                if current_time - last_check_proxy >= 600:
                    self.check_proxies()
                    last_check_proxy = current_time

                time.sleep(SCAN_DELAY * 0.001)

            except Exception as e:
                logging.critical(f"Fatal error in main function: {e}. Restarting...")
                time.sleep(5)

    def scan_comments(self):
        self._scan_posts("posts", self._scanComments)

    def scan_comments_off(self):
        self._scan_posts("stopped_posts", self._scanCommentsOff)

    def _scan_posts(self, table, scan_function):
        try:
            posts = self.db.fetch_data(table)
            logging.info(f"Fetched {len(posts)} posts from {table}.")
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                for post in posts:
                    try:
                        username = post[9] if table == "posts" else None
                        proxy = self._get_proxy(username)
                        executor.submit(scan_function, post[1], proxy)
                    except Exception as e:
                        logging.error(f"Error scheduling scan for post {post[1]}: {e}")

        except Exception as e:
            logging.error(f"An error occurred in _scan_posts ({table}): {e}")

    def check_cookies(self):
        self._check_items("cookies", self._checkCookie)

    def check_proxies(self):
        self._check_items("proxies", self._checkProxy)

    def _check_items(self, table, check_function):
        try:
            items = self.db.fetch_data(table, condition="status = 'live'")
            logging.info(f"Checking {len(items)} {table}.")

            with ThreadPoolExecutor(max_workers=5) as executor:
                for item in items:
                    executor.submit(check_function, item[1])

        except Exception as e:
            logging.error(f"An error occurred in _check_items ({table}): {e}")

    def _scanComments(self, post_name, proxy=None):
        self._process_post(post_name, proxy, update_table="stopped_posts")

    def _scanCommentsOff(self, post_name, proxy=None):
        self._process_post(post_name, proxy, update_table="posts", delay=1200)

    def _process_post(self, post_name, proxy, update_table, delay=0):
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
                logging.warning(f"Proxy failed for {post_name}, trying admin cookie. Error: {e}")
                comments = self._fetch_with_admin_cookie(post_url, proxy)
                if comments is None:
                    return

            last_comment = comments[0]['created_time'] if comments else None
            self.db.bulk_update(update_table, [{'post_name': post_name, 'reaction_count': reaction_count, 'comment_count': comment_count, 'last_comment': last_comment}], 'post_name')

            for comment in comments:
                self._insert_comment(comment, post_name, username)

            logging.info(f"Finished scanning comments for post: {post_name}")
            if delay:
                time.sleep(delay)

        except Exception as e:
            logging.error(f"An error occurred while scanning comments for post {post_name}: {e}")

    def _fetch_with_admin_cookie(self, post_url, proxy):
        try:
            admin_cookies = self.db.fetch_data('cookies', condition="username = 'admin' AND status = 'live'")
            if not admin_cookies:
                logging.warning("No valid admin cookies found. Skipping post.")
                return None

            cookie = random.choice(admin_cookies)[1]
            crawler = FacebookCrawler(post_url, cookie, proxy)
            return crawler.getComments()
        except Exception as e:
            logging.error(f"Failed to fetch data with admin cookie. Skipping post. Error: {e}")
            return None

    def _insert_comment(self, comment, post_name, username):
        try:
            comment_id, post_id = comment['comment_id'], comment['post_id']
            author_id, author_name, author_avatar = comment['author_id'], comment['author_name'], comment['author_avatar']
            content, created_time = comment['content'], comment['created_time']

            if self.db.fetch_data('comments', condition=f"comment_id = '{comment_id}'"):
                logging.info(f"Comment {comment_id} already exists, skipping.")
                return

            logging.info(f"Inserting new comment {comment_id} for post {post_id}")
            self.db.add_data('comments',
                             ['comment_id', 'post_id', 'post_name', 'author_id', 'author_name', 'author_avatar', 'content', 'created_time', 'username'],
                             [(comment_id, post_id, post_name, author_id, author_name, author_avatar, content, created_time, username)])
        except Exception as e:
            logging.error(f"Error inserting comment {comment_id}: {e}")

    def _get_proxy(self, username):
        proxies = self.db.fetch_data('proxies', condition=f"username = '{username}' AND status = 'active'") if username else []
        if not proxies:
            proxies = self.db.fetch_data('proxies', condition="username = 'admin' AND status = 'active'")
        return random.choice(proxies)[0] if proxies else None

    def _checkCookie(self, cookie):
        fb = FacebookAuthencation(cookie)
        if not fb.user_id:
            self.db.bulk_update('cookies', [{'cookie': cookie, 'status': 'die'}], 'cookie')

    def _checkProxy(self, proxy):
        if not CheckProxies.check(proxy):
            self.db.bulk_update('proxies', [{'proxy': proxy, 'status': 'unactive'}], 'proxy')


if __name__ == "__main__":
    while True:
        try:
            cron = CronJob()
            cron.main()
        except Exception as e:
            logging.critical(f"Fatal error in script: {e}. Restarting...")
            time.sleep(5)
