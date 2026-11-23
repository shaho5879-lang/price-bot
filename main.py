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


# اجبار به استفاده از IPv4 برای اتصال بدون قطعی به تلگرام
def allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = allowed_gai_family

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
bot = telebot.TeleBot(BOT_TOKEN)
scraper = cloudscraper.create_scraper()

# کاراکتر مخفی برای راست‌چین کردن صددرصدی پرچم‌ها در تلگرام
RLM = "\u200f"


def fa_num(text):
    """تبدیل اعداد انگلیسی به فونت فارسی"""
    if not text or text == "نامشخص":
        return "نامشخص"
    en = "0123456789"
    fa = "۰۱۲۳۴۵۶۷۸۹"
    return str(text).translate(str.maketrans(en, fa))


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

            # تلاش برای گرفتن اونس طلا از نوار بالای سایت
            if "ons" not in data:
                ons_li = soup.find("li", id="l-ons")
                if ons_li:
                    span = ons_li.find("span", class_="info-price")
                    if span and span.text:
                        data["ons"] = span.text.strip()

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
                                price.strip()
                                if name == "ons"
                                else rial_to_toman(price)
                            )
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    # محاسبه گرم آب‌شده از روی مظنه مثقال
    try:
        mesghal_toman = int(data.get("mesghal", "0").replace(",", ""))
        data["abshodeh_gram"] = f"{int(mesghal_toman / 4.3318):,}"
    except:
        data["abshodeh_gram"] = "نامشخص"

    # محاسبه طلای دست دوم (شکسته)
    if "gold_second" not in data or data["gold_second"] == "نامشخص":
        try:
            g18 = int(data.get("gold18", "0").replace(",", ""))
            data["gold_second"] = f"{int(g18 * (740 / 750)):,}"
        except:
            data["gold_second"] = "نامشخص"

    # دریافت بیت‌کوین، اتریوم و پشتیبان اونس جهانی طلا
    try:
        crypto_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,pax-gold&vs_currencies=usd"
        crypto_res = requests.get(crypto_url, timeout=10).json()
        data["btc"] = f"{crypto_res['bitcoin']['usd']:,}"
        data["eth"] = f"{crypto_res['ethereum']['usd']:,}"
        if "ons" not in data or data["ons"] == "نامشخص":
            data["ons"] = f"{int(crypto_res['pax-gold']['usd']):,}"
    except:
        data["btc"] = "نامشخص"
        data["eth"] = "نامشخص"
        if "ons" not in data:
            data["ons"] = "نامشخص"

    return data


def format_message(data):
    tz = pytz.timezone("Asia/Tehran")
    now = datetime.now(tz)
    j_date = fa_num(
        jdatetime.datetime.fromgregorian(datetime=now).strftime("%Y/%m/%d")
    )
    current_time = fa_num(now.strftime("%H:%M:%S"))

    lines = [
        f"{RLM}📊 **گزارش لحظه‌ای بازار تهران و جهان**",
        f"{RLM}📅 تاریخ: **{j_date}**  |  ⏰ ساعت: **{current_time}**",
        f"{RLM}➖➖➖➖➖➖➖➖➖➖",
        f"{RLM}💵 **۱۰ ارز برتر بازار تهران:**",
        f"{RLM}🇺🇸 دلار آمریکا: **{fa_num(data.get('usd'))}** تومان",
        f"{RLM}🇪🇺 یورو اروپا: **{fa_num(data.get('eur'))}** تومان",
        f"{RLM}🇦🇪 درهم امارات: **{fa_num(data.get('aed'))}** تومان",
        f"{RLM}🇬🇧 پوند انگلیس: **{fa_num(data.get('gbp'))}** تومان",
        f"{RLM}🇹🇷 لیر ترکیه: **{fa_num(data.get('try'))}** تومان",
        f"{RLM}🇨🇦 دلار کانادا: **{fa_num(data.get('cad'))}** تومان",
        f"{RLM}🇦🇺 دلار استرالیا: **{fa_num(data.get('aud'))}** تومان",
        f"{RLM}🇨🇳 یوان چین: **{fa_num(data.get('cny'))}** تومان",
        f"{RLM}🇨🇭 فرانک سوئیس: **{fa_num(data.get('chf'))}** تومان",
        f"{RLM}🇮🇶 دینار عراق: **{fa_num(data.get('iqd'))}** تومان",
        "",
        f"{RLM}✨ **بازار طلا و آب‌شده:**",
        f"{RLM}🔸 طلای ۱۸ عیار: **{fa_num(data.get('gold18'))}** تومان",
        f"{RLM}🔸 طلای ۲۴ عیار: **{fa_num(data.get('gold24'))}** تومان",
        (
            f"{RLM}🔸 طلای شکسته (دست‌دوم): **{fa_num(data.get('gold_second'))}**"
            " تومان"
        ),
        f"{RLM}🔸 مظنه آب‌شده (مثقال): **{fa_num(data.get('mesghal'))}** تومان",
        (
            f"{RLM}🔸 هر گرم طلای آب‌شده: **{fa_num(data.get('abshodeh_gram'))}**"
            " تومان"
        ),
        "",
        f"{RLM}🪙 **بازار سکه:**",
        f"{RLM}🌕 سکه امامی: **{fa_num(data.get('sekee'))}** تومان",
        f"{RLM}🌕 سکه بهار آزادی: **{fa_num(data.get('sekeb'))}** تومان",
        f"{RLM}🌓 نیم سکه: **{fa_num(data.get('nim'))}** تومان",
        f"{RLM}🌒 ربع سکه: **{fa_num(data.get('rob'))}** تومان",
        f"{RLM}🌑 سکه گرمی: **{fa_num(data.get('gerami'))}** تومان",
        "",
        f"{RLM}🌍 **بازارهای جهانی و رمزارز:**",
        f"{RLM}🏆 اونس جهانی طلا: **{fa_num(data.get('ons'))}** دلار",
        f"{RLM}🟠 بیت‌کوین: **{fa_num(data.get('btc'))}** دلار",
        f"{RLM}🔵 اتریوم: **{fa_num(data.get('eth'))}** دلار",
        f"{RLM}➖➖➖➖➖➖➖➖➖➖",
        f"{RLM}🔄 *بروزرسانی به وقت رسمی ایران*",
    ]
    return "\n".join(lines)


def is_price_command(message):
    if not message.text:
        return False
    t = message.text.strip().lower().replace("ي", "ی").replace("ك", "ک")
    return t in ["پرایس", "قیمت", "/price", "price", "/start"]


def handle_request(message):
    chat_id = message.chat.id
    try:
        if message.text.strip() != "/start":
            bot.delete_message(chat_id, message.message_id)
    except:
        pass

    wait_msg = bot.send_message(
        chat_id, f"{RLM}⏳ در حال دریافت آخرین قیمت‌های بازار..."
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


print("Bot is running with Persian RTL format...")
while True:
    try:
        bot.polling(none_stop=True, interval=2, timeout=20)
    except Exception as e:
        print(f"Reconnecting... {e}")
        time.sleep(3)