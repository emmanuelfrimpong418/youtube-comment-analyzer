import os
import sqlite3
import string
import argparse
import sys
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from constants import STOP_WORDS, YOUTUBE_NOISE_WORDS, CONTRACTIONS

load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Analyze YouTube video comments")
    subparsers = parser.add_subparsers(title="commands", dest="command")
    parser_fetch = subparsers.add_parser("fetch", help="Fetch comments from a YouTube video")
    parser_fetch.add_argument("url", help="YouTube video URL to fetch comments from")
    parser_search = subparsers.add_parser("search", help="Search comments for a keyword")
    parser_search.add_argument("keyword", help="Keyword to search for in comments")
    parser_top = subparsers.add_parser("top", help="Display top comments by likes")
    parser_top.add_argument("limit", type=int, help="Number of top comments to display")
    parser_freq = subparsers.add_parser("freq", help="Display most frequent words in comments")
    parser_freq.add_argument("limit", type=int, help="Number of most frequent words to display")
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    if args.command == "fetch":
        try:
            video_id = extract_video_id(args.url)
            comments_data = fetch_comments(video_id)
            save_comments(comments_data, video_id)
            print(f"Fetched and saved {len(comments_data)} comments for video {video_id}.")
        except KeyError:
            sys.exit("Invalid url!")
    else:
        try:
            if args.command == "search":
                display_comments(search_comments(args.keyword, get_last_video_id()))
            elif args.command == "top":
                display_comments(top_comments(args.limit, get_last_video_id()))
            elif args.command == "freq":
                display_frequency(word_frequency(args.limit, get_last_video_id()))
        except sqlite3.OperationalError:
            sys.exit("You need to call fetch first!")

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
    cur.execute("DELETE FROM comments WHERE video_id = ?", (video_id,))
    for comment in comments_data:
        comment_tuples.append((comment["comment"], comment["likes"], comment["author"], video_id))
    cur.executemany("INSERT INTO comments VALUES(?, ?, ?, ?)", comment_tuples)
    con.commit()
    con.close()

def search_comments(keyword, video_id):
    con = sqlite3.connect("video_data.db")
    cur = con.cursor()
    search_term = f"%{keyword}%"
    res = cur.execute("SELECT comment, likes, author FROM comments WHERE comment LIKE ? AND video_id = ?",
                      (search_term, video_id))
    results = res.fetchall()
    con.close()
    return results

def top_comments(limit, video_id):
    con = sqlite3.connect("video_data.db")
    cur = con.cursor()
    res = cur.execute("SELECT comment, likes, author FROM comments WHERE video_id = ? "
                      "ORDER BY likes DESC LIMIT ?",(video_id, limit))
    results = res.fetchall()
    con.close()
    return results

def word_frequency(limit, video_id):
    con = sqlite3.connect("video_data.db")
    cur = con.cursor()
    res = cur.execute("SELECT comment FROM comments WHERE video_id = ?", (video_id,))
    results = res.fetchall()
    word_count = {}
    for result in results:
        for word in result[0].split():
            word = word.lower().strip(string.punctuation)
            if (word not in STOP_WORDS and word not in YOUTUBE_NOISE_WORDS and word not in CONTRACTIONS
                    and any(char.isalpha() for char in word)):
                word_count[word] = word_count.get(word, 0) + 1
    con.close()
    sorted_words = sorted(word_count.items(), key=lambda pair: pair[1], reverse=True)
    return dict(sorted_words[:limit])

def get_last_video_id():
    con = sqlite3.connect("video_data.db")
    cur = con.cursor()
    res = cur.execute("SELECT video_id FROM comments ORDER BY rowid DESC LIMIT 1")
    result = res.fetchone()
    con.close()
    return result[0] if result else None

def display_comments(comments):
    header_text = f"COMMENTS RESULTS ({len(comments)} FOUND)"
    borders = "=" * 103
    print(borders)
    print(header_text.center(103))
    print(borders)
    for index, comment_data in enumerate(comments, 1):
        comment, likes, author = comment_data
        if likes == 1:
            print(f"{index}. {author} ({likes} like)")
            print(f'"{comment}"')
        else:
            print(f"{index}. {author} ({likes} likes)")
            print(f'"{comment}"')
    print(borders)

def display_frequency(freq_data):
    header_text = f"WORD FREQUENCY (TOP {len(freq_data)} FOUND)"
    borders = "=" * 103
    print(borders)
    print(header_text.center(103))
    print(borders)
    for index, word_data in enumerate(freq_data.items(), 1):
        word, frequency = word_data
        print(f"{index}. {word:<20}{frequency:>5}")
    print(borders)



if __name__ == "__main__":
    main()