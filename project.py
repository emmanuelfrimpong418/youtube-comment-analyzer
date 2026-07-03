import os
import sqlite3
import string
import argparse
import sys
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from constants import STOP_WORDS, YOUTUBE_NOISE_WORDS, CONTRACTIONS

load_dotenv()

class CommentsFetchError(Exception):
    """Raised when comments cannot be fetched from the YouTube API."""
    pass

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
        except ValueError:
            sys.exit("Invalid url!")
        except CommentsFetchError as e:
            sys.exit(str(e))
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
    if not url:
        raise ValueError("Invalid url!")
    result = urlparse(url)
    if "youtu.be" in result.netloc:
        video_id = result.path.lstrip("/")
    else:
        video_id = parse_qs(result.query).get("v", [""])[0]
    if not video_id:
        raise ValueError("Invalid url!")
    return video_id

def fetch_comments(video_id):
    comments_data = []
    api_key = os.environ.get("YOUTUBE_API_KEY")
    youtube = build("youtube", "v3", developerKey=api_key)
    try:
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
    except HttpError as error:
        reason = error.error_details[0]["reason"] if error.error_details else ""
        if reason == "badRequest":
            raise CommentsFetchError("Invalid API key. Check your .env file.")
        elif reason == "videoNotFound":
            raise CommentsFetchError("Video not found. Check the URL.")
        elif reason == "commentsDisabled":
            raise CommentsFetchError("Comments are disabled for this video.")
        elif reason == "quotaExceeded":
            raise CommentsFetchError("YouTube API quota exceeded. Try again later.")
        else:
            raise CommentsFetchError("Could not fetch comments from YouTube.")
    return comments_data

def save_comments(comments_data, video_id):
    comment_tuples = []
    with sqlite3.connect("video_data.db") as con:
        cur = con.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS comments(comment TEXT, likes INTEGER, author TEXT, video_id TEXT)")
        cur.execute("DELETE FROM comments WHERE video_id = ?", (video_id,))
        for comment in comments_data:
            comment_tuples.append((comment["comment"], comment["likes"], comment["author"], video_id))
        cur.executemany("INSERT INTO comments VALUES(?, ?, ?, ?)", comment_tuples)

def search_comments(keyword, video_id):
    with sqlite3.connect("video_data.db") as con:
        cur = con.cursor()
        search_term = f"%{keyword}%"
        res = cur.execute("SELECT comment, likes, author FROM comments WHERE comment LIKE ? AND video_id = ?",
                          (search_term, video_id))
        results = res.fetchall()
    return results

def top_comments(limit, video_id):
    with sqlite3.connect("video_data.db") as con:
        cur = con.cursor()
        res = cur.execute("SELECT comment, likes, author FROM comments WHERE video_id = ? "
                          "ORDER BY likes DESC LIMIT ?",(video_id, limit))
        results = res.fetchall()
    return results

def word_frequency(limit, video_id):
    with sqlite3.connect("video_data.db") as con:
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
    sorted_words = sorted(word_count.items(), key=lambda pair: pair[1], reverse=True)
    return dict(sorted_words[:limit])

def compute_stats(video_id):
    with sqlite3.connect("video_data.db") as con:
        cur = con.cursor()
        res = cur.execute("SELECT comment, likes, author FROM comments WHERE video_id = ? ORDER BY likes DESC",
                          (video_id,))
        results = res.fetchall()
    if not results:
        raise ValueError("No comments found!")
    comments_analyzed = len(results)
    most_liked_comment = results[0]
    total_likes = 0
    total_comment_length = 0
    for result in results:
        total_likes += result[1]
        total_comment_length += len(result[0].split())
    average_likes = total_likes/comments_analyzed
    average_comment_length = total_comment_length / comments_analyzed
    return {"comments_analyzed": comments_analyzed, "total_likes": total_likes, "average_likes": average_likes,
            "average_comment_length": average_comment_length, "most_liked_comment": most_liked_comment}

def get_last_video_id():
    with sqlite3.connect("video_data.db") as con:
        cur = con.cursor()
        res = cur.execute("SELECT video_id FROM comments ORDER BY rowid DESC LIMIT 1")
        result = res.fetchone()
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

def display_stats(stats_data):
    header_text = "GENERAL STATISTICS"
    borders = "=" * 103
    comment, likes, author = stats_data["most_liked_comment"]
    print(borders)
    print(header_text.center(103))
    print(borders)
    print(f"Comments analyzed: {stats_data['comments_analyzed']:,}")
    print(f"Total likes: {stats_data['total_likes']:,}")
    print(f"Average likes per comment: {stats_data['average_likes']:.1f}")
    print(f"Average comment length: {stats_data['average_comment_length']:.1f}")
    print("Most liked comment:")
    print(f"Author: {author}")
    print(f"Likes: {likes:,}")
    print(f"Comment: {comment}")



if __name__ == "__main__":
    main()