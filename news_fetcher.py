import feedparser
import smtplib
from datetime import datetime, timedelta
import re
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

CLIENTS = ["Xiaomi", "BYD", "Apple"]
DAYS_BACK = 7
MAX_NEWS_PER_CLIENT = 5
KEYWORDS = [
    "revenue", "sales", "earnings", "volume",
    "expansion", "capacity", "plant", "closure",
    "factory", "new project", "project",
    "new product", "launch"
]

def clean_text(text):
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def contains_keywords(text, keywords):
    text_low = text.lower()
    return any(k.lower() in text_low for k in keywords)

def fetch_news_for(client):
    rss_url = f"https://news.google.com/rss/search?q={client}+when:7d&hl=en-US&gl=US&ceid=US:en"
    return feedparser.parse(rss_url).entries

def within_last_week(entry):
    if "published_parsed" not in entry:
        return False
    pub_date = datetime(*entry.published_parsed[:6])
    return pub_date >= datetime.now() - timedelta(days=DAYS_BACK)

def make_paragraph_summary(big_news_items):
    if not big_news_items:
        return "No major updates were detected for Xiaomi, BYD, or Apple this week."

    client_to_items = {}
    for client, title in big_news_items:
        client_to_items.setdefault(client, []).append(title)

    paragraphs = []
    for client, titles in client_to_items.items():
        if len(titles) == 1:
            p = f"For {client}, the main development this week was: {titles[0]}."
        else:
            p = f"For {client}, key developments included: " + "; ".join(titles[:-1]) + f"; and {titles[-1]}."
        paragraphs.append(p)

    return "\n\n".join(paragraphs)

def generate_email_body():
    all_big_news = []
    detailed_sections = []

    for client in CLIENTS:
        entries = fetch_news_for(client)
        recent = [e for e in entries if within_last_week(e)]

        filtered = []
        for e in recent:
            full = clean_text(e.get("summary", "") + " " + e.get("title", ""))
            if contains_keywords(full, KEYWORDS):
                filtered.append(e)

        filtered = sorted(filtered, key=lambda e: len(e.get("summary", "")), reverse=True)[:MAX_NEWS_PER_CLIENT]

        if filtered:
            for e in filtered:
                all_big_news.append((client, e.title))

            det_text = f"\n\n=== {client.upper()} ===\n"
            for e in filtered:
                pub_date = datetime(*e.published_parsed[:6]).strftime("%Y-%m-%d %H:%M")
                det_text += f"\n--- {e.title} ---\n"
                det_text += f"Published: {pub_date}\n"
                det_text += f"Source: {e.link}\n"
                det_text += f"{clean_text(e.get('summary', ''))}\n"
            detailed_sections.append(det_text)
        else:
            detailed_sections.append(f"\n\n=== {client.upper()} ===\nNo major news found.")

    email_top = make_paragraph_summary(all_big_news)

    return email_top + "\n\n\n" + "\n".join(detailed_sections)

def send_email(body):
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    recipient = os.environ["EMAIL_TO"]

    msg = MIMEMultipart()
    msg["Subject"] = "Weekly News Summary"
    msg["From"] = sender
    msg["To"] = recipient

    msg.attach(MIMEText(body, "plain"))

    import ssl
    import smtplib

    smtp_server = "smtp.office365.com"
    port = 587

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

if __name__ == "__main__":
    body = generate_email_body()
    send_email(body)

