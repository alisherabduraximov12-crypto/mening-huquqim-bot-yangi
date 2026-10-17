import os
import logging
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("mening-huquqim")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""
OPENAI_URL = "https://api.openai.com/v1/responses"

CONTACT_TEXT = (
    "📞 Raqobat qo‘mitasi Call-markazi: 1159\n"
    "✉️ Elektron pochta: info@raqobat.gov.uz\n"
    "📍 Manzil: 100128, Toshkent shahri, Labzak ko‘chasi, 3-uy\n"
    "🌐 Rasmiy sayt: https://raqobat.gov.uz/bog-lanish/\n\n"
    "Eslatma: bot orqali olingan javob rasmiy murojaat ro‘yxatdan o‘tganini anglatmaydi."
)

LAW_LINKS = (
    "📚 Rasmiy manbalar:\n"
    "• Qonunchilik hujjatlari bazasi: https://lex.uz/\n"
    "• Chakana savdo qoidalari: https://lex.uz/acts/-243235\n"
    "• Raqobat qo‘mitasi aloqa sahifasi: https://raqobat.gov.uz/bog-lanish/\n\n"
    "Qonun hujjatining amaldagi tahririni rasmiy manbadan tekshiring."
)

KEYBOARD = {
    "keyboard": [
        [{"text": "🛒 Muammom bor"}, {"text": "📝 Ariza tayyorlash"}],
        [{"text": "📚 Huquqlarim haqida"}, {"text": "📄 Kerakli hujjatlar"}],
        [{"text": "📞 Aloqa"}, {"text": "🔄 Qayta boshlash"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

SYSTEM_INSTRUCTIONS = """
Siz “Mening Huquqim” — O‘zbekiston iste’molchilariga dastlabki yo‘l-yo‘riq beruvchi
AI yordamchisiz. O‘zbek tilida, lotin yozuvida, sodda va hurmat bilan javob bering.

VAZIFA:
Iste’molchining holatini tahlil qiling, ehtimoliy huquqlarini tushuntiring, dalillarni
sanang va amaliy keyingi qadamlarni tavsiya qiling.

ASOSIY HUQUQIY YO‘NALISHLAR:
- “Iste’molchilarning huquqlarini himoya qilish to‘g‘risida”gi Qonun;
- chakana savdo qoidalari, jumladan Vazirlar Mahkamasining 75-son qarori va amaldagi tahriri;
- vaziyat talab qilsa, boshqa tegishli qonunchilik.
Rasmiy manbalar: https://lex.uz/ va https://raqobat.gov.uz/bog-lanish/

QAT’IY TALABLAR:
1. Qonun moddasi, bandi, muddat, jarima yoki vakolatni ishonchli bilmasangiz, raqamni taxmin
   qilmang. Amaldagi tahrirni LexUZ orqali tekshirish zarurligini ayting.
2. Foydalanuvchi bermagan faktlarni o‘ylab topmang. Dalillar yetishmasa, aniq ko‘rsating.
3. Yetarli ma’lumot bo‘lmasa, qat’iy xulosa emas, dastlabki baho bering.
4. Qo‘mita vakolatiga kirmaydigan masalani Qo‘mita albatta hal qiladi deb va’da bermang.
   Sud, ekspertiza yoki boshqa organ vakolati bo‘lsa, chegarani tushuntiring.
5. Javob rasmiy qaror, sud qarori, ekspertiza yoki advokat xulosasi o‘rnini bosmaydi.
6. Parol, SMS-kod, bank karta ma’lumoti yoki keraksiz shaxsiy ma’lumotlarni so‘ramang.
7. Tovar xavfli bo‘lishi mumkin bo‘lsa, foydalanishni vaqtincha to‘xtatishni va tegishli
   mutaxassis yoki organga murojaat qilishni tavsiya qiling. Masofadan xavfsizlikni kafolatlamang.
8. Qonun matniga bevosita kirish imkoningiz yo‘q bo‘lsa, manbani o‘qib tekshirdim deb da’vo qilmang.

JAVOB TUZILMASI:
1. Dastlabki baho
2. Huquqiy asos
3. Kerakli hujjat va dalillar
4. Tavsiya etiladigan keyingi qadamlar
5. Qayerga murojaat qilish

Faqat vaziyatga tegishli bo‘limlarni yozing. Kerak bo‘lsa, eng muhim 1–3 aniqlashtiruvchi
savol bering. O‘zingizni davlat organi deb ko‘rsatmang.
"""

# User sessions are kept in memory. They reset if the service restarts.
sessions = {}
seen_update_ids = set()


def telegram_call(method, payload):
    if not TELEGRAM_API:
        log.error("BOT_TOKEN is missing")
        return None
    try:
        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload,
            timeout=20,
        )
