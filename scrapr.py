import json
import os
import praw
import sqlite3
import re
from time import time


class Scrapr:
    def __init__(self, config):
        self.set_config(config)
        self.init_dirs()
        self.db_path = "scrapr_dbs/{}.db".format(self.config.get("db_name"))

    def set_config(self, config):
        with open(config, "r") as f:
            self.config = json.load(f)

    def init_dirs(self):
        if not os.path.exists("scrapr_dbs"):
            os.mkdir("scrapr_dbs")

    def get_config(self):
        return self.config

    def get_db(self):
        return sqlite3.connect(self.db_path)


class RedditScrapr(Scrapr):
    def __init__(self, config, praw_config=False):
        super().__init__(config)
        self.init_praw(praw_config)
        self.init_db()

    def init_praw(self, praw_config):
        if praw_config is False:
            self.praw = praw_config
        else:
            with open(praw_config, "r") as f:
                self.praw = praw.Reddit(**json.load(f))

    def init_db(self):
        if not os.path.exists(self.db_path):
            conn = super().get_db()
            c = conn.cursor()
            c.execute(
                "CREATE TABLE IF NOT EXISTS scrapr (permalink text PRIMARY KEY, title text, selftext text, author text, keywords text, date text)"
            )
            conn.commit()
            conn.close()

    def get_all_links(self):
        conn = super().get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM scrapr ORDER BY date DESC")
        rows = c.fetchall()
        conn.close()

        rows_formatted = []
        for row in rows:
            rows_formatted.append(
                {
                    "permalink": row[0],
                    "title": row[1],
                    "selftext": row[2],
                    "author": row[3],
                    "keywords": row[4],
                    "date": row[5],
                }
            )

        return rows_formatted

    def insert_submission(self, permalink, title, selftext, author, keywords):
        conn = super().get_db()
        c = conn.cursor()
        c.execute("SELECT permalink FROM scrapr WHERE permalink = ?", [permalink])
        if c.fetchone():
            conn.close()
            return False
        c.execute(
            "INSERT INTO scrapr (permalink, title, selftext, author, keywords, date) VALUES (?,?,?,?,?,?)",
            [permalink, title, selftext, author, keywords, time()],
        )
        conn.commit()
        conn.close()

    def scrape_submission(self, submission):
        title = submission.title
        author = submission.author.name
        permalink = submission.permalink
        selftext = submission.selftext
        combined_text = title + selftext
        keywords = self.config.get("keywords")
        keywords_regex = "|".join(keywords)
        tracked_users = self.config.get("tracked_users")

        if not keywords and not tracked_users:
            self.insert_submission(permalink, title, selftext, author, keywords_regex)

        if author in tracked_users:
            self.insert_submission(permalink, title, selftext, author, keywords_regex)

        text_regex = re.compile(keywords_regex, re.IGNORECASE)

        if text_regex.search(combined_text):
            self.insert_submission(permalink, title, selftext, author, keywords_regex)

    def scrape(self):
        sorting = self.config.get("sorting")
        if sorting == "hot":
            self.scrape_hot()
        if sorting == "new":
            self.scrape_new()
        if sorting == "top":
            self.scrape_top()
        if sorting == "rising":
            self.scrape_rising()
        if sorting == "controversial":
            self.scrape_controversial()

    def scrape_hot(self):
        limit = self.config.get("limit")
        for submission in self.praw.subreddit(self.config.get("subreddit")).hot(
            limit=limit
        ):
            self.scrape_submission(submission)

    def scrape_new(self):
        limit = self.config.get("limit")
        for submission in self.praw.subreddit(self.config.get("subreddit")).new(
            limit=limit
        ):
            self.scrape_submission(submission)

    def scrape_top(self):
        limit = self.config.get("limit")
        for submission in self.praw.subreddit(self.config.get("subreddit")).top(
            limit=limit
        ):
            self.scrape_submission(submission)

    def scrape_rising(self):
        limit = self.config.get("limit")
        for submission in self.praw.subreddit(self.config.get("subreddit")).rising(
            limit=limit
        ):
            self.scrape_submission(submission)

    def scrape_controversial(self):
        limit = self.config.get("limit")
        for submission in self.praw.subreddit(
            self.config.get("subreddit")
        ).controversial(limit=limit):
            self.scrape_submission(submission)
