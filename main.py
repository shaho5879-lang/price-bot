from datetime import datetime
import os
import socket
import time
from bs4 import BeautifulSoup
import cloudscraper
import jdatetime
import pytz
import requests
import telebot
import urllib3.util.connection as urllib3_cn


# --- حل قطعی مشکل تایم‌اوت تلگرام در سرور گیت‌هاب (اجبار به استفاده از IPv4) ---
def allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = allowed_gai_family
# -------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
bot = telebot.TeleBot(BOT_TOKEN)
scraper = cloudscraper.create_scraper()


def rial_to_toman(price_str):
    try:
        clean_price = int(str(price_str).replace(",", "").strip())
        return f"{clean_price // 10:,}"
    except:
        return "نامشخص"


def get_market_data():
    data = {}
    urls = [
        "https://www.tgju.org/currency",
        "https://www.tgju.org/gold-chart",
        "https://www.tgju.org/coin",
    ]

    keys = {
        "usd": "price_dollar_rl",
        "eur": "price_eur",
        "aed": "price_aed",
        "gbp": "price_gbp",
        "try": "price_try",
        "cad": "price_cad",
        "aud": "price_aud",
        "cny": "price_cny",
        "chf": "price_chf",
        "iqd": "price_iqd",
        "gold18": "geram18",
        "gold24": "geram24",
        "gold_second": "gold_mini_size",
        "mesghal": "mesghal",
        "ons": "ons",
        "sekee": "sekee",
        "sekeb": "sekeb",
        "nim": "nim",
        "rob": "rob",
        "gerami": "gerami",
    }

    for url in urls:
        try:
            res = scraper.get(url, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            for name, slug in keys.items():
                if name not in data:
                    row = soup.find("tr", {"data-market-row": slug})
                    if row:
                        price = row.get("data-price")
                        if not price:
                            td = row.find("td", class_="nf")
                            price = td.text if td else None
                        if price:
                            data[name] = (
                                price
                                if name == "ons"
                                else rial_to_toman(price)
                            )
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    try:
        mesghal_toman = int(data.get("mesghal", "0").replace(",", ""))
        data["abshodeh_gram"] = f"{int(mesghal_toman / 4.3318):,}"
    except:
        data["abshodeh_gram"] = "نامشخص"

    if "gold_second" not in data or data["gold_second"] == "نامشخص":
        try:
            g18 = int(data.get("gold18", "0").replace(",", ""))
            data["gold_second"] = f"{int(g18 * (740 / 750)):,}"
        except:
            data["gold_second"] = "نامشخص"

    try:
        crypto_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"
        crypto_res = requests.get(crypto_url, timeout=10).json()
        data["btc"] = f"{crypto_res['bitcoin']['usd']:,}"
        data["eth"] = f"{crypto_res['ethereum']['usd']:,}"
    except:
        data["btc"] = "نامشخص"
        data["eth"] = "نامشخص"

    return data


def format_message(data):
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    j_date = jdatetime.datetime.fromgregorian(datetime=now).strftime(
        "%Y/%m/%d"
    )
    current_time = now.strftime("%H:%M:%S")

    return f"""📊 **گزارش لحظه‌ای بازار تهران و جهان**
📅 تاریخ: `{j_date}`  |  ⏰ ساعت: `{current_time}`
➖➖➖➖➖➖➖➖➖➖
💵 **۱۰ ارز برتر بازار تهران:**
🇺🇸 دلار آمریکا: **{data.get('usd', '-')}** تومان
🇪🇺 یورو اروپا: **{data.get('eur', '-')}** تومان
🇦🇪 درهم امارات: **{data.get('aed', '-')}** تومان
🇬🇧 پوند انگلیس: **{data.get('gbp', '-')}** تومان
🇹🇷 لیر ترکیه: **{data.get('try', '-')}** تومان
🇨🇦 دلار کانادا: **{data.get('cad', '-')}** تومان
🇦🇺 دلار استرالیا: **{data.get('aud', '-')}** تومان
🇨🇳 یوان چین: **{data.get('cny', '-')}** تومان
🇨🇭 فرانک سوئیس: **{data.get('chf', '-')}** تومان
🇮🇶 دینار عراق: **{data.get('iqd', '-')}** تومان

✨ **بازار طلا و آب‌شده:**
🔸 طلای ۱۸ عیار: **{data.get('gold18', '-')}** تومان
🔸 طلای ۲۴ عیار: **{data.get('gold24', '-')}** تومان
🔸 طلای شکسته (دست‌دوم): **{data.get('gold_second', '-')}** تومان
🔸 مظنه آب‌شده (مثقال): **{data.get('mesghal', '-')}** تومان
🔸 هر گرم طلای آب‌شده: **{data.get('abshodeh_gram', '-')}** تومان

🪙 **بازار سکه:**
🌕 سکه امامی: **{data.get('sekee', '-')}** تومان
🌕 سکه بهار آزادی: **{data.get('sekeb', '-')}** تومان
🌓 نیم سکه: **{data.get('nim', '-')}** تومان
🌒 ربع سکه: **{data.get('rob', '-')}** تومان
🌑 سکه گرمی: **{data.get('gerami', '-')}** تومان

🌍 **بازارهای جهانی و رمزارز:**
🏆 اونس جهانی طلا: **{data.get('ons', '-')}** دلار
🟠 بیت‌کوین (BTC): **{data.get('btc', '-')}** دلار
🔵 اتریوم (ETH): **{data.get('eth', '-')}** دلار
➖➖➖➖➖➖➖➖➖➖
🔄 *بروزرسانی به وقت رسمی ایران*"""


def is_price_command(message):
    if not message.text:
        return False
    t = message.text.strip().lower().replace("ي", "ی").replace("ك", "ک")
    return t in ["پرایس", "/price", "price", "قیمت", "/start"]


def handle_request(message):
    chat_id = message.chat.id
    try:
        if message.text.strip() != "/start":
            bot.delete_message(chat_id, message.message_id)
    except:
        pass

    wait_msg = bot.send_message(
        chat_id, "⏳ در حال دریافت آخرین قیمت‌های بازار..."
    )
    market_data = get_market_data()
    final_text = format_message(market_data)
    bot.edit_message_text(
        final_text, chat_id, wait_msg.message_id, parse_mode="Markdown"
    )


@bot.channel_post_handler(func=is_price_command)
def channel_handler(message):
    handle_request(message)


@bot.message_handler(func=is_price_command)
def private_handler(message):
    handle_request(message)


print("Bot connected via IPv4 and is running...")
while True:
    try:
        bot.polling(none_stop=True, interval=2, timeout=20)
    except Exception as e:
        print(f"Reconnecting... {e}")
        time.sleep(3)