import os
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


if __name__ == "__main__":
    pass