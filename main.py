from flask import Flask, request
import requests
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
OMDB_API_KEY = os.environ['OMDB_API_KEY']
SHRINK_API_TOKEN = os.environ['SHRINK_API_TOKEN']
BLOGGER_CLIENT_ID = os.environ['BLOGGER_CLIENT_ID']
BLOGGER_CLIENT_SECRET = os.environ['BLOGGER_CLIENT_SECRET']
BLOGGER_REFRESH_TOKEN = os.environ['BLOGGER_REFRESH_TOKEN']
BLOG_ID = os.environ['BLOG_ID']
ADMIN_ID = int(os.environ['ADMIN_ID'])

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_API}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})

def shorten_link(original_link):
    if not original_link.startswith("http"):
        return None
    url = f"https://shrinkearn.com/api?api={SHRINK_API_TOKEN}&url={original_link}&format=text"
    res = requests.get(url)
    return res.text.strip() if res.ok else None

def fetch_omdb_data(title):
    url = f"https://www.omdbapi.com/?t={title}&apikey={OMDB_API_KEY}"
    res = requests.get(url)
    data = res.json()
    return data if data.get("Response") == "True" else None

def get_access_token():
    res = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": BLOGGER_CLIENT_ID,
        "client_secret": BLOGGER_CLIENT_SECRET,
        "refresh_token": BLOGGER_REFRESH_TOKEN,
        "grant_type": "refresh_token"
    })
    return res.json().get("access_token")

def post_to_blogger(movie, short_link, category, remark):
    token = get_access_token()
    if not token:
        return None

    content = f'''
    <div style="color:#fff;background:#000;padding:15px;font-family:sans-serif">
        <h2 style="text-align:center;color:#f4c430">{movie['Title']}</h2>
        <div style="text-align:center"><img src="{movie['Poster']}" style="max-width:300px;border-radius:8px"/></div>
        <p>{movie['Plot']}</p>
        <p><strong>Rating:</strong> {movie['imdbRating']}</p>
        <p><strong>Genre:</strong> {movie['Genre']}</p>
        <p><strong>Director:</strong> {movie['Director']}</p>
        <p><strong>Download:</strong><br><textarea readonly style="width:90%">{short_link}</textarea></p>
        <p><strong>Category:</strong> {category}</p>
        <p><strong>Remark:</strong> {remark}</p>
    </div>
    '''

    payload = {
        "title": f"Movie: {movie['Title']}",
        "content": content,
        "labels": [category]
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    res = requests.post(f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/", headers=headers, json=payload)
    if res.ok:
    return res.json().get("url")
else:
    print("❌ Blogger API Error:", res.text)  # ✅ This will log the full error to Render
    return None

@app.route(f"/{TELEGRAM_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    msg = data.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    user_id = msg.get("from", {}).get("id")

    if chat_id != ADMIN_ID:
        send_message(chat_id, "❌ You are not authorized to use this bot.")
        return ""

    text = msg.get("text", "")
    lines = text.splitlines()
    try:
        title = lines[0].split(":", 1)[1].strip()
        category = lines[1].split(":", 1)[1].strip()
        link = lines[2].split(":", 1)[1].strip()
    except Exception:
        send_message(chat_id, "⚠️ Invalid format. Please send like:\nMovie: Name\nCategory: Type\nLink: http://example.com")
        return ""

    movie = fetch_omdb_data(title)
    if not movie:
        send_message(chat_id, f"❌ Movie not found in OMDb: {title}")
        return ""

    short_link = shorten_link(link)
    if not short_link:
        send_message(chat_id, "❌ Failed to shorten the link.")
        return ""

    blog_url = post_to_blogger(movie, short_link, category, remark="Posted via Telegram")
    if blog_url:
        send_message(chat_id, f"✅ Posted Successfully!\n🔗 {blog_url}")
    else:
        send_message(chat_id, "❌ Failed to post to Blogger.")
    return "ok"

@app.route("/")
def index():
    return "Bot is running. Webhook URL: /" + TELEGRAM_TOKEN

if __name__ == "__main__":
    app.run(debug=True)
