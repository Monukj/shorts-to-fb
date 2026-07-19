import os
import time
import xml.etree.ElementTree as ET
import requests

YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UC2JeNtLYLDWCQroKQt3TPQQ")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "61590685063175")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")

TG_BOT_TOKEN = "8704061172:AAGLKmIgB4hQtD1IhPgX-HzFVTAyvoae714"
TG_CHAT_ID = "8216845039"

PROCESSED_TRACKER_FILE = "posted_shorts.txt"

def load_processed_shorts():
    if os.path.exists(PROCESSED_TRACKER_FILE):
        with open(PROCESSED_TRACKER_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def mark_short_as_processed(video_id):
    with open(PROCESSED_TRACKER_FILE, "a") as f:
        f.write(f"{video_id}\n")

def get_latest_shorts():
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={YOUTUBE_CHANNEL_ID}"
    try:
        response = requests.get(rss_url, timeout=15)
        if response.status_code != 200:
            return []
        root = ET.fromstring(response.content)
        ns = {'ns': 'http://www.w3.org/2005/Atom'}
        shorts = []
        for entry in root.findall('ns:entry', ns):
            video_id = entry.find('ns:id', ns).text.split(':')[-1]
            title = entry.find('ns:title', ns).text
            link = f"https://www.youtube.com/shorts/{video_id}"
            shorts.append({'id': video_id, 'title': title, 'link': link})
        return shorts
    except Exception as e:
        print(f"[-] RSS Feed checking error: {e}")
        return []

def extract_video_via_telegram(youtube_url):
    print(f"[+] Requesting Telegram engine for link: {youtube_url}")
    send_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TG_CHAT_ID, "text": youtube_url}
    try:
        res = requests.post(send_url, json=payload, timeout=10)
        if res.status_code != 200:
            return None
        time.sleep(15) 
        updates_url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/getUpdates"
        updates_res = requests.get(updates_url, timeout=10).json()
        if not updates_res.get("ok"):
            return None
        for update in reversed(updates_res.get("result", [])):
            message = update.get("message", {})
            if "video" in message:
                file_id = message["video"]["file_id"]
                file_info_url = f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/getFile?file_id={file_id}"
                file_info = requests.get(file_info_url).json()
                if file_info.get("ok"):
                    file_path = file_info["result"]["file_path"]
                    return f"https://api.telegram.org/file/bot{TG_BOT_TOKEN}/{file_path}"
        return None
    except Exception as e:
        return None

def upload_to_facebook(video_url, title):
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos"
    payload = {'description': title, 'file_url': video_url, 'access_token': FB_ACCESS_TOKEN}
    try:
        response = requests.post(url, data=payload, timeout=30)
        res_data = response.json()
        return response.status_code == 200 or "id" in res_data
    except Exception as e:
        return False

def run_automation_cycle():
    processed_shorts = load_processed_shorts()
    latest_shorts = get_latest_shorts()
    if not latest_shorts:
        return
    target_short = latest_shorts[0]
    if target_short['id'] in processed_shorts:
        print(f"[~] Content '{target_short['title']}' already dispatched.")
        return
    stream_url = extract_video_via_telegram(target_short['link'])
    if stream_url:
        if upload_to_facebook(stream_url, target_short['title']):
            mark_short_as_processed(target_short['id'])

if __name__ == "__main__":
    run_automation_cycle()
