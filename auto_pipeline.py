import os
import time
import asyncio
import xml.etree.ElementTree as ET
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- CONFIGURATION ---
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UC2JeNtLYLDWCQroKQt3TPQQ")
FB_PAGE_ID = os.getenv("FB_PAGE_ID", "61590685063175")
FB_ACCESS_TOKEN = os.getenv("FB_ACCESS_TOKEN")

# Telegram API & Session credentials
API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
TG_SESSION_STRING = os.getenv("TG_SESSION_STRING")
DOWNLOADER_BOT_USERNAME = "@SaveBlog" # Aapke bot ka username

def is_already_posted_on_fb(title):
    print(f"[+] Checking Facebook Page feed for duplicate: '{title}'")
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/feed"
    payload = {'access_token': FB_ACCESS_TOKEN, 'limit': 10}
    try:
        response = requests.get(url, params=payload, timeout=20)
        res_data = response.json()
        if "data" in res_data:
            for post in res_data["data"]:
                if title in post.get("message", "") or title in post.get("description", ""):
                    return True
        return False
    except Exception as e:
        print(f"[-] Error while checking Facebook duplicates: {e}")
        return False

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
        print(f"[-] RSS Feed Error: {e}")
        return []

async def extract_video_via_user_side(youtube_url):
    print("[+] Connecting to Telegram via Saved Session String...")
    # Bina kisi interactive input ke direct string based authorization
    client = TelegramClient(StringSession(TG_SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    try:
        # Aapki profile se bot ko link send hoga
        await client.send_message(DOWNLOADER_BOT_USERNAME, youtube_url)
        print("[+] Link pushed from user context. Awaiting 25 seconds for bot reply...")
        await asyncio.sleep(25)
        
        # Latest messages mein se video file dhoodhna
        async for message in client.iter_messages(DOWNLOADER_BOT_USERNAME, limit=3):
            if message.video:
                print("[+] Target video file payload found!")
                file_path = await client.download_media(message.video, 'temp_short.mp4')
                await client.disconnect()
                return file_path
    except Exception as e:
        print(f"[-] Session Automation Error: {e}")
    
    await client.disconnect()
    return None

def upload_to_facebook_local(file_path, title):
    print("[+] Uploading video binary directly to Facebook...")
    url = f"https://graph.facebook.com/v19.0/{FB_PAGE_ID}/videos"
    
    with open(file_path, 'rb') as video_file:
        files = {'source': video_file}
        payload = {'description': title, 'access_token': FB_ACCESS_TOKEN}
        try:
            response = requests.post(url, data=payload, files=files, timeout=60)
            res_data = response.json()
            return response.status_code == 200 or "id" in res_data
        except Exception as e:
            print(f"[-] FB Upload Error: {e}")
            return False

async def main():
    latest_shorts = get_latest_shorts()
    if not latest_shorts:
        print("[-] No videos found in RSS feed.")
        return
    
    target_short = latest_shorts[0]
    if is_already_posted_on_fb(target_short['title']):
        print(f"[~] Skipping! '{target_short['title']}' is already live on Facebook.")
        return
        
    local_video = await extract_video_via_user_side(target_short['link'])
    if local_video and os.path.exists(local_video):
        if upload_to_facebook_local(local_video, target_short['title']):
            print("[+] Success! Automation cycle complete.")
        else:
            print("[-] Failed to upload to Facebook.")
        
        # Temporary downloaded video delete karna
        os.remove(local_video)
    else:
        print("[-] Could not retrieve video from Telegram bot responses.")

if __name__ == "__main__":
    asyncio.run(main())
