import logging
from datetime import datetime
import os
import sys
import time
import threading
from typing import Dict
from utils import DatabaseManager
from core.api import FacebookCrawler
from config import *


class CronJob:
    def __init__(self):
        if not os.path.exists('logs'):
            os.makedirs('logs')

        log_filename = f'logs/cron_{datetime.now().strftime("%Y-%m-%d")}.log'

        logging.basicConfig(
            format='%(asctime)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_filename)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.db = DatabaseManager(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database='user')

    def main(self):
        self.logger.info("Cron job started.")
        while True:
            try:
                data = self.db.fetch_data('posts')
                self.logger.info(f"Fetched {len(data)} posts from database.")

                threads = []
                for post in data:
                    post_name = post[1]
                    self.logger.info(f"Starting new thread to scan comments for post: {post_name}")
                    thread = threading.Thread(target=self._scanComments, args=(post_name,))
                    threads.append(thread)
                    thread.start()

                for thread in threads:
                    thread.join()

                time.sleep(SCAN_DELAY * 0.001)

            except Exception as e:
                self.logger.error(f"An error occurred in the main loop: {e}")
                time.sleep(SCAN_DELAY * 0.001)

    def _scanComments(self, post_name):
        try:
            self.logger.info(f"Scanning comments for post: {post_name}")
            data = self.db.fetch_data('posts', condition=f"post_name = '{post_name}'")

            if data == []:
                return

            username = data[0][9]
            post_url = data[0][2]

            self.logger.info(f"Fetching comments for post {post_name} from URL: {post_url}")
            crawler = FacebookCrawler(post_url)
            reaction_count = crawler.reaction_count
            comment_count = crawler.comment_count
            comments = crawler.getComments()
            last_comment = comments[0]['created_time'] if comments else None

            self.logger.info(f"Updating post {post_name} with {reaction_count} reactions, {comment_count} comments, and last comment at {last_comment}")
            self.db.bulk_update('posts', [{'post_name': post_name, 'reaction_count': reaction_count, 'comment_count': comment_count, 'last_comment': last_comment}], 'post_name')

            for comment in comments:
                comment_id = comment['comment_id']
                post_id = comment['post_id']
                author_id = comment['author_id']
                author_name = comment['author_name']
                author_avatar = comment['author_avatar']
                content = comment['content']
                created_time = comment['created_time']

                db_comments = self.db.fetch_data('comments', condition=f"comment_id = '{comment_id}'")
                if db_comments != []:
                    self.logger.info(f"Comment with ID {comment_id} already exists, skipping insert.")
                    continue

                self.logger.info(f"Inserting new comment with ID {comment_id} for post {post_id}")
                self.db.add_data('comments',
                                    ['comment_id', 'post_id', 'post_name', 'author_id', 'author_name', 'author_avatar', 'content', 'created_time', 'username'],
                                    [(comment_id, post_id, post_name, author_id, author_name, author_avatar, content, created_time, username)]
                )
            self.logger.info(f"Finished scanning comments for post: {post_name}")
        except Exception as e:
            self.logger.error(f"An error occurred while scanning comments for post {post_name}: {e}")
 

if __name__ == "__main__":
    cron = CronJob()
    cron.main()