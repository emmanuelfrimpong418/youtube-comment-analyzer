import os
import sqlite3
import string
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
from googleapiclient.discovery import build

STOP_WORDS = {"a", "an", "the",
    "and", "or", "but", "if", "then", "else", "so", "nor",
    "is", "am", "are", "was", "were", "be", "been", "being",
    "i", "you", "he", "she", "it", "we", "they",
    "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their",
    "mine", "yours", "ours", "theirs",
    "this", "that", "these", "those",
    "to", "of", "in", "on", "at", "for", "with", "about", "against",
    "between", "into", "through", "during", "before", "after",
    "above", "below", "from", "up", "down", "out", "off", "over", "under",
    "again", "further", "once",
    "as", "than", "too", "very", "just", "not", "no",
    "do", "does", "did", "doing",
    "have", "has", "had", "having",
    "can", "could", "will", "would", "shall", "should", "may", "might", "must",
    "what", "which", "who", "whom", "where", "when", "why", "how",
    "all", "any", "both", "each", "few", "more", "most",
    "other", "some", "such", "only", "own", "same",
    "there", "here", "now", "also"
}

YOUTUBE_NOISE_WORDS = {"video", "videos", "channel", "subscribe", "subscribed", "subscriber",
    "subscribers", "comment", "comments", "like", "likes", "liked",
    "dislike", "dislikes", "watch", "watching", "watched",
    "youtube", "viewer", "viewers", "content", "creator",
    "lol", "lmao", "omg", "wow", "yeah", "ok", "okay", "hey",
    "first", "second", "third", "love", "im", "thats", "thank", "thanks",
    "please", "pls", "really", "actually", "literally"
}

CONTRACTIONS = {
    "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't",
    "haven't", "hasn't", "hadn't", "won't", "wouldn't", "can't", "couldn't",
    "shouldn't", "mustn't", "shan't",
    "i'm", "you're", "he's", "she's", "it's", "we're", "they're",
    "i've", "you've", "we've", "they've",
    "i'll", "you'll", "he'll", "she'll", "we'll", "they'll",
    "i'd", "you'd", "he'd", "she'd", "we'd", "they'd",
    "that's", "there's", "what's", "who's", "let's",
}

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
    pass