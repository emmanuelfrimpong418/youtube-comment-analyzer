import os
import sqlite3
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build

load_dotenv()

def main():
    pass

def extract_video_id(url):
    result = urlparse(url)
    if "youtu.be" in result.netloc:
        video_id = result.path.lstrip("/")
    else:
        video_id = parse_qs(result.query)["v"][0]
    return video_id

def fetch_comments(video_id):
    comments_data = []
    api_key = os.environ.get("YOUTUBE_API_KEY")
    youtube = build("youtube", "v3", developerKey=api_key)
    get_comments = youtube.commentThreads().list(part="snippet", videoId=video_id, textFormat="plainText")
    response = get_comments.execute()
    for comment in  response["items"]:
        index = comment["snippet"]["topLevelComment"]["snippet"]
        comments_data.append({"comment": index["textDisplay"], "likes": index["likeCount"],
                              "author": index["authorDisplayName"]})
    while True:
        if response.get("nextPageToken"):
            get_comments = youtube.commentThreads().list(part="snippet", videoId=video_id, textFormat="plainText",
                                                         pageToken=response["nextPageToken"])
            response = get_comments.execute()
            for comment in response["items"]:
                index = comment["snippet"]["topLevelComment"]["snippet"]
                comments_data.append({"comment": index["textDisplay"], "likes": index["likeCount"],
                                      "author": index["authorDisplayName"]})
        else:
            break
    return comments_data

def save_comments(comments_data, video_id):
    comment_tuples = []
    con = sqlite3.connect("video_data.db")
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS comments(comment, likes, author, video_id)")
    for comment in comments_data:
        comment_tuples.append((comment["comment"], comment["likes"], comment["author"], video_id))
    cur.executemany("INSERT INTO comments VALUES(?, ?, ?, ?)", comment_tuples)
    con.commit()
    con.close()

def search_comments(keyword):
    con = sqlite3.connect("video_data.db")
    cur = con.cursor()
    search_term = f"%{keyword}%"
    res = cur.execute("SELECT comment, likes, author FROM comments WHERE comment LIKE ?", (search_term,))
    results = res.fetchall()
    con.close()
    return results



if __name__ == "__main__":
    pass