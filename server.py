from flask import Flask, render_template, request, redirect, url_for
from util import generate_config
from scrapr import RedditScrapr
import os
import sqlite3


app = Flask(__name__)


def init_db():
    conn = sqlite3.connect("scrapr.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS configs (name text, path text)")
    c.execute("CREATE TABLE IF NOT EXISTS praw_configs (name text, path text)")
    conn.commit()
    conn.close()


def db_insert_config(table, name, path):
    conn = sqlite3.connect("scrapr.db")
    c = conn.cursor()
    c.execute("SELECT name FROM {table} WHERE name = ?".format(table=table), [name])
    if c.fetchone():
        conn.close()
        return False
    c.execute(
        "INSERT INTO {table} (name, path) VALUES (?,?)".format(table=table),
        [name, path],
    )
    conn.commit()
    conn.close()
    return True


def db_get_configs(table):
    configs = []
    conn = sqlite3.connect("scrapr.db")
    c = conn.cursor()
    c.execute("SELECT name, path FROM {table}".format(table=table))
    rows = c.fetchall()
    conn.close()
    for row in rows:
        configs.append({"name": row[0], "path": row[1]})
    return configs


def get_config_path(table, name):
    conn = sqlite3.connect("scrapr.db")
    c = conn.cursor()
    c.execute("SELECT path FROM {table} WHERE name = ?".format(table=table), [name])
    path = c.fetchone()[0]
    conn.close()
    return path


init_db()


@app.route("/", methods=["GET"])
def get_index():
    return render_template(
        "index.html",
        **{
            "scraprs": db_get_configs("configs"),
            "praws": db_get_configs("praw_configs"),
        }
    )


@app.route("/reddit/create", methods=["GET"])
def get_reddit_create():
    return render_template("reddit_create.html")


@app.route("/reddit/create", methods=["POST"])
def post_reddit_create():
    config_name = "_".join(request.form.get("configName", "").split(" "))
    subreddit = request.form.get("subreddit")
    limit = request.form.get("limit")
    sorting = request.form.get("sorting")
    keywords = request.form.get("keywords", "").split(",")
    tracked_users = request.form.get("trackedUsers", "").split(",")

    if not config_name and not subreddit and not limit and not sorting:
        return "Required paramater was not filled in. (Subreddit, Limit, Sorting)"

    params = {
        "subreddit": subreddit,
        "limit": int(limit),
        "sorting": sorting,
        "keywords": keywords,
        "tracked_users": tracked_users,
    }

    if db_insert_config(
        "configs",
        config_name,
        generate_config(config_name, "configs", ["db_name"], **params),
    ):
        return redirect(url_for("get_index"))
    else:
        return "Error creating the configuration."


@app.route("/praw/create", methods=["GET"])
def get_praw_create():
    return render_template("praw_create.html")


@app.route("/praw/create", methods=["POST"])
def post_praw_create():
    config_name = "_".join(request.form.get("configName", "").split(" "))
    client_id = request.form.get("clientId", "")
    client_secret = request.form.get("clientSecret", "")
    user_agent = request.form.get("userAgent", "")

    if not client_id and not client_secret and not limit and not user_agent:
        return "Required paramater was not filled in. (Client ID, Client Secret, User Agent)"

    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "user_agent": user_agent,
    }

    if db_insert_config(
        "praw_configs",
        config_name,
        generate_config(config_name, "praw_configs", **params),
    ):
        return redirect(url_for("get_index"))
    else:
        return "Error creating the configuration."


@app.route("/reddit/<name>", methods=["GET"])
def get_reddit_name(name):
    links = RedditScrapr(get_config_path("configs", name)).get_all_links()
    return render_template(
        "reddit_name.html",
        links=links,
        num_links=len(links),
        praw_configs=db_get_configs("praw_configs"),
        name=name,
    )


@app.route("/reddit/<name>/run", methods=["POST"])
def post_reddit_name_run(name):
    reddit_config_path = get_config_path("configs", name)
    praw_config_path = get_config_path("praw_configs", request.form.get("prawConfig"))

    try:
        RedditScrapr(reddit_config_path, praw_config_path).scrape()
    except TypeError:
        return "There was an error running your configuration."

    return redirect(url_for("get_reddit_name", name=name))


def db_delete_config(table, name):
    conn = sqlite3.connect("scrapr.db")
    c = conn.cursor()
    c.execute("DELETE FROM {table} WHERE name = ?".format(table=table), [name])
    conn.commit()
    conn.close()


@app.route("/reddit/<name>/delete", methods=["GET"])
def get_reddit_name_delete(name):
    config_path = get_config_path("configs", name)
    os.remove(config_path)
    db_delete_config("configs", name)
    return redirect(url_for("get_index"))


@app.route("/praw/<name>/delete", methods=["GET"])
def get_praw_name_delete(name):
    config_path = get_config_path("praw_configs", name)
    os.remove(config_path)
    db_delete_config("praw_configs", name)
    return redirect(url_for("get_index"))


app.run(host="0.0.0.0", port=8000)
