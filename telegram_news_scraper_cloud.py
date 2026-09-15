import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration - Use environment variables for cloud deployment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "YOUR_CHANNEL_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# User agents to avoid blocking
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
]

def get_session():
    """Create a requests session with retry strategy"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({'User-Agent': random.choice(USER_AGENTS)})
    return session

def scrape_thehindu_current_affairs():
    """Scrape current affairs from The Hindu"""
    try:
        session = get_session()
        url = "https://www.thehindu.com/news/"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('a', {'data-test': 'internal-link'}, limit=2)
        
        posts = []
        for article in articles:
            headline = article.get_text(strip=True)
            link = article.get('href', '')
            if headline and link:
                if not link.startswith('http'):
                    link = 'https://www.thehindu.com' + link
                posts.append({
                    'title': headline,
                    'link': link,
                    'source': 'The Hindu'
                })
        
        return posts[:1]
    except Exception as e:
        logger.error(f"Error scraping The Hindu: {e}")
        return []

def scrape_bbc_current_affairs():
    """Scrape current affairs from BBC News"""
    try:
        session = get_session()
        url = "https://www.bbc.com/news"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('a', {'data-testid': 'internal-link'}, limit=2)
        
        posts = []
        for article in articles:
            headline = article.get_text(strip=True)
            link = article.get('href', '')
            if headline and link and len(headline) > 10:
                if not link.startswith('http'):
                    link = 'https://www.bbc.com' + link
                posts.append({
                    'title': headline,
                    'link': link,
                    'source': 'BBC News'
                })
        
        return posts[:1]
    except Exception as e:
        logger.error(f"Error scraping BBC News: {e}")
        return []

def scrape_history_polity():
    """Scrape history/polity content from Wikipedia This Day"""
    try:
        session = get_session()
        url = "https://en.wikipedia.org/wiki/Wikipedia:On_this_day/Today"
        response = session.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        events = []
        sections = soup.find_all(['ul', 'ol'])
        
        for section in sections:
            items = section.find_all('li', limit=3)
            for item in items:
                text = item.get_text(strip=True)
                if text and len(text) > 20:
                    events.append(text)
        
        posts = []
        for event in events[:2]:
            posts.append({
                'title': event,
                'link': url,
                'source': 'Wikipedia: On This Day'
            })
        
        return posts
    except Exception as e:
        logger.error(f"Error scraping Wikipedia: {e}")
        return []

def scrape_indian_history():
    """Scrape Indian history facts"""
    try:
        facts = [
            "India is the world's largest democracy with over 1.4 billion people",
            "The Indian Constitution is the longest written constitution in the world",
            "India's ancient civilization dates back to over 5,000 years",
            "The Maurya Empire (322-185 BCE) was one of ancient India's greatest empires",
            "The Mughal Empire significantly influenced Indian culture and architecture",
            "India became independent on August 15, 1947",
            "Dr. B.R. Ambedkar was the chief architect of the Indian Constitution",
            "The Vedas are among the oldest sacred texts of India (1500-500 BCE)",
            "The Ashoka Empire extended across most of the Indian subcontinent",
            "The Indus Valley Civilization flourished around 2600-1900 BCE",
        ]
        
        selected_facts = random.sample(facts, min(2, len(facts)))
        
        posts = []
        for fact in selected_facts:
            posts.append({
                'title': fact,
                'link': '',
                'source': 'Indian History'
            })
        
        return posts
    except Exception as e:
        logger.error(f"Error getting history facts: {e}")
        return []

def send_telegram_message(message):
    """Send message to Telegram channel"""
    try:
        payload = {
            'chat_id': TELEGRAM_CHANNEL_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }
        
        response = requests.post(TELEGRAM_API_URL, data=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("Message sent successfully to Telegram")
            return True
        else:
            logger.error(f"Failed to send message. Status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")
        return False

def format_message(current_affairs, history_polity):
    """Format scraped content into a nice Telegram message"""
    message = f"<b>📰 Daily News Update - {datetime.now().strftime('%d %B %Y')}</b>\n\n"
    
    if current_affairs:
        message += "<b>🌍 Current Affairs:</b>\n"
        for i, article in enumerate(current_affairs, 1):
            title = article.get('title', '')[:100]
            source = article.get('source', 'Unknown')
            link = article.get('link', '')
            
            if link:
                message += f"{i}. <a href='{link}'>{title}</a>\n"
            else:
                message += f"{i}. {title}\n"
            message += f"   📌 <i>{source}</i>\n\n"
    
    if history_polity:
        message += "<b>📚 History & Polity:</b>\n"
        for i, item in enumerate(history_polity, 1):
            title = item.get('title', '')[:150]
            source = item.get('source', 'Unknown')
            
            message += f"{i}. {title}\n"
            message += f"   📌 <i>{source}</i>\n\n"
    
    message += "<i>Updated daily at scheduled time</i>"
    
    return message

def daily_scrape_and_post():
    """Main function to scrape and post daily"""
    logger.info("=" * 50)
    logger.info("Starting daily scrape and post...")
    logger.info("=" * 50)
    
    try:
        # Scrape Current Affairs from multiple sources
        logger.info("Scraping current affairs...")
        current_affairs = []
        current_affairs.extend(scrape_thehindu_current_affairs())
        current_affairs.extend(scrape_bbc_current_affairs())
        logger.info(f"Found {len(current_affairs)} current affairs posts")
        
        # Scrape History & Polity
        logger.info("Scraping history and polity...")
        history_polity = []
        history_polity.extend(scrape_history_polity())
        history_polity.extend(scrape_indian_history())
        logger.info(f"Found {len(history_polity)} history/polity posts")
        
        if not current_affairs:
            logger.warning("No current affairs found")
        if not history_polity:
            logger.warning("No history/polity content found")
        
        # Limit to required posts
        current_affairs = current_affairs[:1]
        history_polity = history_polity[:2]
        
        # Format and send message
        if current_affairs or history_polity:
            message = format_message(current_affairs, history_polity)
            logger.info("Sending message to Telegram...")
            send_telegram_message(message)
            logger.info("Daily post completed successfully")
        else:
            logger.warning("No content to post")
    
    except Exception as e:
        logger.error(f"Error in daily scrape and post: {e}")
        logger.error("Attempting to send error notification to Telegram...")
        try:
            error_msg = f"<b>⚠️ Scraper Error</b>\n\nError: {str(e)}\n\nTime: {datetime.now().strftime('%d %B %Y %H:%M:%S')}"
            send_telegram_message(error_msg)
        except:
            logger.error("Could not send error notification")

def schedule_daily_posts(hour=8, minute=0):
    """Schedule daily posts at specific time (24-hour format)"""
    time_str = f"{hour:02d}:{minute:02d}"
    schedule.every().day.at(time_str).do(daily_scrape_and_post)
    logger.info(f"Scheduled daily posts at {time_str}")

def run_scheduler():
    """Keep the scheduler running"""
    logger.info("Scheduler started. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("=" * 50)
    print("🤖 Telegram Daily News Scraper (Cloud Version)")
    print("=" * 50)
    print(f"Bot Token: {TELEGRAM_BOT_TOKEN[:20] if TELEGRAM_BOT_TOKEN != 'YOUR_BOT_TOKEN' else 'NOT SET'}...")
    print(f"Channel: {TELEGRAM_CHANNEL_ID if TELEGRAM_CHANNEL_ID != 'YOUR_CHANNEL_ID' else 'NOT SET'}")
    print("=" * 50)
    
    # Check if credentials are set
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN" or TELEGRAM_CHANNEL_ID == "YOUR_CHANNEL_ID":
        logger.error("❌ ERROR: Bot Token or Channel ID not set!")
        logger.error("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID environment variables")
        exit(1)
    
    # Run once immediately on startup
    logger.info("📍 Running initial scrape on startup...")
    daily_scrape_and_post()
    
    # Schedule for daily execution
    logger.info("⏰ Setting up scheduler...")
    schedule_daily_posts(hour=8, minute=0)  # Posts at 8:00 AM daily
    
    # Keep running
    logger.info("✅ Scraper is now running!")
    run_scheduler()
