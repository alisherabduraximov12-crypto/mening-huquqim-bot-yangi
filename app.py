import os
import logging
import time
import threading
from datetime import datetime, date
from collections import deque

import requests
from flask import Flask, request, jsonify

# Mening Huquqim
# Bepul ishlaydi, OpenAI API talab qilmaydi.
# Render Start Command: gunicorn app:app
# Majburiy muhit o'zgaruvchisi: BOT_TOKEN
# Ixtiyoriy: WEBHOOK_SECRET, LOG_LEVEL

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TIMEOUT = 20

# Telegram yangilanishlarini bir vaqtda qayta ishlashdan saqlash.
UPDATE_LOCK = threading.RLock()
sessions = {}
seen_updates = set()
seen_order = deque()
SESSION_TTL = 1800

# Rasmiy hujjatlar havolalari. Joylashtirishdan oldin ochib tekshiring.
LAW_URL = "https://lex.uz/uz/acts/-4704"
RETAIL_URL = "https://lex.uz/uz/acts/-243235"
AD_URL = "https://lex.uz/uz/docs/-6052631"
COMPETITION_URL = "https://lex.uz/uz/docs/-6518381"
COMMITTEE_URL = "https://raqobat.gov.uz/"

MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "🛒 Mahsulot muammosi"}],
        [{"text": "📝 Ariza va talabnoma"}],
        [{"text": "📚 Qonunchilik kutubxonasi"}],
        [{"text": "⚖️ Huquqlarim haqida"}],
        [{"text": "☎️ Qo‘mita bilan aloqa"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

DOC_KEYBOARD = {
    "keyboard": [
        [{"text": "📝 Sotuvchiga talabnoma"}],
        [{"text": "🏛 Qo‘mitaga murojaat"}],
        [{"text": "⬅️ Asosiy menyu"}],
    ],
    "resize_keyboard": True,
}

LIBRARY_KEYBOARD = {
    "keyboard": [
        [{"text": "📕 Iste’molchi qonuni"}],
        [{"text": "📘 Chakana savdo qoidalari"}],
        [{"text": "📢 Reklama to‘g‘risidagi qonun"}],
        [{"text": "⚖️ Raqobat to‘g‘risidagi qonun"}],
        [{"text": "⬅️ Asosiy menyu"}],
    ],
    "resize_keyboard": True,
}

CANCEL_WORDS = {
    "bekor", "bekor qilish", "cancel", "orqaga", "to‘xtatish"
}

PRODUCT_PROMPTS = [
    ("product", "Qaysi mahsulot yoki xizmat bo‘yicha muammo yuz berdi?"),
    (
        "purchase_date",
        "Qachon xarid qilgansiz yoki xizmatdan foydalangansiz?\n"
        "Sanani kun.oy.yil shaklida yozing. Masalan: 15.09.2026.\n"
        "Aniq eslamasangiz, «bilmayman» deb yozing.",
    ),
    ("problem", "Muammo nimada? Nima sodir bo‘lganini tushuntiring."),
    (
        "seller",
        "Sotuvchi yoki xizmat ko‘rsatuvchi tashkilot nomini yozing. "
        "Bilmasangiz, «bilmayman» deb yozing.",
    ),
    (
        "evidence",
        "Qanday dalillaringiz bor? Masalan, chek, shartnoma, kafolat "
        "taloni, foto yoki yozishma. Bo‘lmasa, «yo‘q» deb yozing.",
    ),
]

AD_PROMPTS = [
    (
        "ad_place",
        "Reklamani qayerda ko‘rdingiz? Masalan, Telegram, Instagram, "
        "televideniye, internet sayti yoki do‘konda.",
    ),
    (
        "ad_date",
        "Reklamani qachon ko‘rdingiz yoki unga qachon duch keldingiz? "
        "Sanani kun.oy.yil shaklida yozing yoki «bilmayman» deb yozing.",
    ),
    (
        "ad_claim",
        "Reklamada nima va’da qilingan yoki qanday ma’lumot berilgan? "
        "Nimasi sizni chalg‘itganini tushuntiring.",
    ),
    (
        "advertiser",
        "Reklama beruvchi kompaniya, sotuvchi yoki mahsulot nomini yozing. "
        "Bilmasangiz, «bilmayman» deb yozing.",
    ),
    (
        "evidence",
        "Reklamaning skrinshoti, havolasi, videosi yoki boshqa dalilingiz bormi? "
        "Bo‘lmasa, «yo‘q» deb yozing.",
    ),
]


def telegram(method, payload):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN sozlanmagan")
        return None

    try:
        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()

        if not result.get("ok"):
            logger.error("Telegram API so‘rovni bajarmadi")
        return result

    except (requests.RequestException, ValueError):
        # Bot tokeni loglarga chiqib ketmasligi uchun xato matnini yozmaymiz.
        logger.error("Telegram bilan bog‘lanishda xato yuz berdi")
        return None


def send(chat_id, text, keyboard=MAIN_KEYBOARD):
    payload = {
        "chat_id": chat_id,
        "text": str(text)[:4000],
    }
    if keyboard:
        payload["reply_markup"] = keyboard
    return telegram("sendMessage", payload)


def reset(chat_id):
    sessions.pop(str(chat_id), None)


def clean_old_sessions():
    now = time.time()
    expired = [
        key for key, value in sessions.items()
        if now - value.get("updated", now) > SESSION_TTL
    ]
    for key in expired:
        sessions.pop(key, None)


def begin(chat_id, flow):
    reset(chat_id)

    prompts = AD_PROMPTS if flow == "advertising" else PRODUCT_PROMPTS

    sessions[str(chat_id)] = {
        "flow": flow,
        "step_index": 0,
        "data": {},
        "updated": time.time(),
    }

    send(
        chat_id,
        "Ma’lumotlarni navbat bilan yuboring.\n"
        "Suhbatni to‘xtatish uchun «Bekor» deb yozing.\n\n"
        + prompts[0][1],
    )


def welcome():
    return (
        "Assalomu alaykum! «Mening Huquqim» botiga xush kelibsiz.\n\n"
        "Bot iste’molchi muammosi bo‘yicha dastlabki yo‘l-yo‘riq beradi, "
        "kerakli hujjatlar ro‘yxatini ko‘rsatadi va ariza yoki talabnoma "
        "loyihasini tayyorlashga yordam beradi.\n\n"
        "Bot bepul ishlaydi va pullik AI API ishlatmaydi. Javoblar "
        "rasmiy qaror yoki yakuniy huquqiy xulosa hisoblanmaydi.\n\n"
        "Kerakli bo‘limni tanlang."
    )


def rights_text():
    return (
        "⚖️ ISTE’MOLCHI HUQUQLARI\n\n"
        "Iste’molchi qonunchilikda belgilangan shartlarda:\n"
        "• tovar yoki xizmat haqida to‘g‘ri va yetarli ma’lumot olish;\n"
        "• tovar sifati va xavfsizligiga doir huquqlarini himoya qilish;\n"
        "• nuqsonli tovar yoki sifatsiz xizmat bo‘yicha qonuniy talab qo‘yish;\n"
        "• sotuvchi yoki xizmat ko‘rsatuvchiga yozma murojaat qilish;\n"
        "• vakolatli organga yoki qonunda belgilangan tartibda sudga murojaat "
        "qilish huquqlariga ega bo‘lishi mumkin.\n\n"
        "Aniq huquq va talab tovar turi, vaziyat, dalillar va amaldagi "
        "qonunchilikka bog‘liq. Qonun matni: " + LAW_URL
    )


def contact_text():
    return (
        "☎️ RASMIY ALOQA\n\n"
        "Raqobatni rivojlantirish va iste’molchilar huquqlarini "
        "himoya qilish qo‘mitasi\n"
        "Call-markaz: 1159\n"
        "Rasmiy sayt: " + COMMITTEE_URL + "\n\n"
        "Elektron pochta va manzilni rasmiy saytdagi amaldagi "
        "ma’lumotlardan tekshiring."
    )


def valid_date(value):
    value = value.strip()

    if value.casefold() in {
        "bilmayman", "eslay olmayman", "aniq eslay olmayman"
    }:
        return True

    parsed = None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()
            break
        except ValueError:
            continue

    if parsed is None:
        return False

    return parsed <= date.today()


def is_advertising(text):
    value = text.casefold().replace("’", "'").replace("ʻ", "'")
    words = (
        "reklama", "reklamaga", "reklamada", "reklamani",
        "aldov reklama", "chalg'ituvchi reklama",
        "chalg‘ituvchi reklama", "reklama bo'yicha",
        "reklama bo‘yicha",
    )
    return any(word in value for word in words)


def documents_text():
    return (
        "📚 QONUNCHILIK KUTUBXONASI\n\n"
        "📕 1. Iste’molchilarning huquqlarini himoya qilish to‘g‘risidagi Qonun:\n"
        + LAW_URL
        + "\n\n📘 2. VMning 2003-yil 13-fevraldagi 75-son qarori "
        "— chakana savdo qoidalari:\n"
        + RETAIL_URL
        + "\n\n📢 3. Reklama to‘g‘risidagi Qonun:\n"
        + AD_URL
        + "\n\n⚖️ 4. Raqobat to‘g‘risidagi Qonun:\n"
        + COMPETITION_URL
        + "\n\nHujjatlarning amaldagi tahririni LexUZ orqali tekshiring."
    )


def build_guidance(data):
    # Siz ma’qullagan dastlabki yo‘l-yo‘riq matni saqlandi.
    product = data.get("product", "ko‘rsatilmagan")
    problem = data.get("problem", "ko‘rsatilmagan")

    safety_words = [
        "tutun", "yonib", "uchqun", "portlash", "tok ur",
        "gaz hidi", "qizib ket", "xavfli",
    ]
    safety = ""

    if any(
        word in (product + " " + problem).casefold()
        for word in safety_words
    ):
        safety = (
            "\n\n⚠️ XAVFSIZLIK: Mahsulot xavf tug‘dirayotgan bo‘lsa, undan "
            "foydalanishni to‘xtating. Xavfli qurilmani o‘zingiz ta’mirlashga "
            "urinmang va tegishli mutaxassis yoki favqulodda xizmatga murojaat qiling."
        )

    return (
        "📋 DASTLABKI YO‘L-YO‘RIQ\n\n"
        f"Mahsulot/xizmat: {product}\n"
        f"Muammo: {problem}\n\n"
        "1. Chek, to‘lov hujjati, shartnoma, kafolat taloni va yozishmalarni saqlang.\n"
        "2. Muammoni foto yoki videoga qayd eting, agar xavfsiz bo‘lsa.\n"
        "3. Sotuvchiga yozma murojaat qiling va murojaat yuborilganini tasdiqlovchi "
        "dalilni saqlang.\n"
        "4. Nuqsonli tovar bo‘yicha talab turi va imkoniyati tovar, nuqson, kafolat "
        "hamda qonuniy shartlarga bog‘liq. Aniq talabni hujjatlar asosida tekshiring.\n"
        "5. Muammo hal bo‘lmasa, Qo‘mita vakolatiga kirishini aniqlab, 1159 orqali "
        "maslahat oling yoki rasmiy saytga murojaat qiling: " + COMMITTEE_URL + "\n\n"
        "Kerakli hujjatlar: chek yoki boshqa to‘lov isboti, shartnoma/kafolat "
        "hujjati, foto-video, sotuvchiga murojaat va javob.\n\n"
        "Bu avtomatik dastlabki tavsiya, rasmiy huquqiy xulosa emas. "
        "Qonunchilik kutubxonasi: " + LAW_URL + safety
    )


def build_ad_guidance(data):
    place = data.get("ad_place", "ko‘rsatilmagan")
    claim = data.get("ad_claim", "ko‘rsatilmagan")
    advertiser = data.get("advertiser", "ko‘rsatilmagan")
    evidence = data.get("evidence", "ko‘rsatilmagan")

    return (
        "📋 REKLAMA BO‘YICHA DASTLABKI YO‘L-YO‘RIQ\n\n"
        f"Reklama joyi: {place}\n"
        f"Reklama mazmuni: {claim}\n"
        f"Reklama beruvchi: {advertiser}\n"
        f"Dalillar: {evidence}\n\n"
        "1. Reklamaning skrinshoti, videosi yoki havolasini saqlang. "
        "Reklama sanasi va manbasini qayd eting.\n"
        "2. Reklamada aynan qanday va’da yoki ma’lumot berilganini, "
        "uning nimasi haqiqatga mos emas yoki chalg‘ituvchi ekanini yozib oling.\n"
        "3. Agar reklama sabab mahsulot xarid qilgan bo‘lsangiz, chek, "
        "shartnoma, buyurtma va sotuvchi bilan yozishmalarni saqlang.\n"
        "4. Reklama qonunchiligi buzilgan deb hisoblasangiz, mavjud dalillar "
        "bilan Qo‘mitaga murojaat qilib, masalaning vakolatga taalluqliligini "
        "aniqlashtirishingiz mumkin.\n"
        "5. Call-markaz: 1159. Rasmiy sayt: " + COMMITTEE_URL + "\n\n"
        "Qonunchilik: " + AD_URL + "\n\n"
        "Bu dastlabki tavsiya. Reklamaning qonunga zidligi faqat ushbu "
        "ma’lumotlardan avtomatik ravishda tasdiqlanmaydi."
    )


def build_application(data, flow):
    if flow == "committee":
        recipient = (
            "Raqobatni rivojlantirish va iste’molchilar huquqlarini "
            "himoya qilish qo‘mitasiga"
        )
        title = "MUROJAAT"
        request_text = (
            "Murojaatimni ko‘rib chiqishingizni, masalaning Qo‘mita vakolatiga "
            "taalluqliligini baholashingizni va vakolat doirasida qonuniy "
            "chora ko‘rish masalasini hal etishingizni so‘rayman."
        )
    else:
        recipient = data.get("seller", "[sotuvchi nomi]")
        title = "TALABNOMA"
        request_text = (
            "Yuqoridagi holatni o‘rganib chiqishingizni va amaldagi "
            "qonunchilik doirasida muammoni hal etishingizni so‘rayman. "
            "Talabimni ko‘rib chiqib, menga yozma javob berishingizni so‘rayman."
        )

    return (
        "📝 HUJJAT LOYIHASI\n\n"
        f"Kimga: {recipient}\n"
        "Kimdan: [F.I.Sh., manzil va aloqa ma’lumotlari]\n\n"
        f"{title}\n\n"
        "Men quyidagi masala yuzasidan murojaat qilmoqdaman.\n\n"
        f"Mahsulot yoki xizmat: {data.get('product', '[to‘ldiriladi]')}\n"
        f"Xarid sanasi: {data.get('purchase_date', '[to‘ldiriladi]')}\n"
        f"Muammo: {data.get('problem', '[to‘ldiriladi]')}\n"
        f"Sotuvchi/tashkilot: {data.get('seller', '[to‘ldiriladi]')}\n\n"
        f"{request_text}\n\n"
        "Mavjud dalillar va ilovalar: "
        f"{data.get('evidence', 'ko‘rsatilmagan')}.\n\n"
        "Sana: [to‘ldiriladi]\n"
        "Imzo: [to‘ldiriladi]\n\n"
        "ESLATMA: Bu namuna. Yuborishdan oldin shaxsiy ma’lumotlarni, "
        "aniq talabni va ilovalarni to‘ldiring. Faqat mavjud hujjatlarni "
        "ilova qiling. Qo‘mitaga murojaat loyihasi masalaning Qo‘mita "
        "vakolatiga kirishini avtomatik tasdiqlamaydi."
    )


def process_step(chat_id, text, session):
    flow = session["flow"]

    if flow == "advertising":
        prompts = AD_PROMPTS
    else:
        prompts = PRODUCT_PROMPTS

    index = session["step_index"]
    key = prompts[index][0]

    if key in {"purchase_date", "ad_date"} and not valid_date(text):
        send(
            chat_id,
            "Sana noto‘g‘ri kiritildi yoki kelajakdagi sana ko‘rsatildi.\n"
            "Sanani kun.oy.yil shaklida yozing. Masalan: 15.09.2026.\n"
            "Aniq eslamasangiz, «bilmayman» deb yozing.",
        )
        return

    session["data"][key] = text
    session["updated"] = time.time()

    next_index = index + 1
    if next_index < len(prompts):
        session["step_index"] = next_index
        send(chat_id, prompts[next_index][1])
        return

    data = session["data"]
    reset(chat_id)

    if flow == "advertising":
        answer = build_ad_guidance(data)
    elif flow in {"seller_claim", "committee"}:
        answer = build_application(data, flow)
    else:
        answer = build_guidance(data)

    send(chat_id, answer)


def handle_message(message):
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return

    if not text:
        send(chat_id, "Iltimos, matnli xabar yuboring yoki menyudan bo‘lim tanlang.")
        return

    lower = text.casefold()
    normalized = lower.replace("’", "'").replace("ʻ", "'")

    clean_old_sessions()

    # 1. Asosiy buyruqlar doim birinchi tekshiriladi.
    if lower in {"/start", "/help", "start"}:
        reset(chat_id)
        send(chat_id, welcome(), MAIN_KEYBOARD)
        return

    if lower in CANCEL_WORDS or text == "⬅️ Asosiy menyu":
        reset(chat_id)
        send(chat_id, "Asosiy menyu.", MAIN_KEYBOARD)
        return

    # 2. Menyu tugmalari va oddiy buyruqlar.
    if text == "🛒 Mahsulot muammosi" or lower == "/muammo":
        begin(chat_id, "problem")
        return

    if text == "📝 Ariza va talabnoma" or lower in {
        "/ariza", "ariza", "ariza va talabnoma"
    }:
        reset(chat_id)
        send(chat_id, "Qaysi hujjatni tayyorlaymiz?", DOC_KEYBOARD)
        return

    if normalized in {
        "talabnoma yozib ber", "talabnoma yoz", "sotuvchiga talabnoma"
    }:
        begin(chat_id, "seller_claim")
        return

    if normalized in {
        "ariza yozib ber", "qo'mitaga ariza", "qo'mitaga murojaat"
    }:
        begin(chat_id, "committee")
        return

    if text == "📝 Sotuvchiga talabnoma":
        begin(chat_id, "seller_claim")
        return

    if text == "🏛 Qo‘mitaga murojaat":
        begin(chat_id, "committee")
        return

    if text == "📚 Qonunchilik kutubxonasi" or lower in {
        "/qonun", "/hujjatlar", "qonunchilik", "kutubxona"
    }:
        reset(chat_id)
        send(chat_id, "Qaysi hujjatni ko‘rmoqchisiz?", LIBRARY_KEYBOARD)
        return

    # 3. Kutubxona oddiy matnni ham taniydi.
    if text == "📕 Iste’molchi qonuni" or normalized in {
        "iste'molchi qonuni", "istemolchi qonuni", "istemol",
        "iste'mol", "iste'molchi", "iste'molchilar qonuni"
    }:
        reset(chat_id)
        send(
            chat_id,
            "📕 Iste’molchilarning huquqlarini himoya qilish to‘g‘risidagi Qonun:\n"
            + LAW_URL + "\n\nLexUZ’dagi amaldagi tahririni tekshiring.",
            LIBRARY_KEYBOARD,
        )
        return

    if text == "📘 Chakana savdo qoidalari" or normalized in {
        "75-son qaror", "75 qaror", "chakana savdo", "chakana savdo qoidalari"
    }:
        reset(chat_id)
        send(
            chat_id,
            "📘 VMning 2003-yil 13-fevraldagi 75-son qarori — "
            "chakana savdo qoidalari:\n"
            + RETAIL_URL + "\n\nLexUZ’dagi amaldagi tahririni tekshiring.",
            LIBRARY_KEYBOARD,
        )
        return

    if text == "📢 Reklama to‘g‘risidagi qonun" or normalized in {
        "reklama", "reklama qonuni", "reklama to'g'risida"
    }:
        reset(chat_id)
        send(
            chat_id,
            "📢 Reklama to‘g‘risidagi Qonun:\n"
            + AD_URL + "\n\nLexUZ’dagi amaldagi tahririni tekshiring.",
            LIBRARY_KEYBOARD,
        )
        return

    if text == "⚖️ Raqobat to‘g‘risidagi qonun" or normalized in {
        "raqobat", "raqobat qonuni", "raqobat to'g'risida"
    }:
        reset(chat_id)
        send(
            chat_id,
            "⚖️ Raqobat to‘g‘risidagi Qonun:\n"
            + COMPETITION_URL + "\n\nLexUZ’dagi amaldagi tahririni tekshiring.",
            LIBRARY_KEYBOARD,
        )
        return

    if text == "⚖️ Huquqlarim haqida" or lower == "/huquqim":
        reset(chat_id)
        send(chat_id, rights_text(), MAIN_KEYBOARD)
        return

    if text == "☎️ Qo‘mita bilan aloqa" or lower == "/aloqa":
        reset(chat_id)
        send(chat_id, contact_text(), MAIN_KEYBOARD)
        return

    # 4. Faol suhbat ichida reklama haqida yozilsa, reklama savollariga o'tadi.
    session = sessions.get(str(chat_id))

    if session and session["flow"] == "problem":
        if session["step_index"] == 0 and is_advertising(text):
            reset(chat_id)
            begin(chat_id, "advertising")
            return

    # 5. Faol suhbat bo'lsa, navbatdagi savolni qayta ishlash.
    session = sessions.get(str(chat_id))
    if session:
        process_step(chat_id, text, session)
        return

    # 6. Suhbat yo'q bo'lsa, ayrim erkin so'rovlarni tushunish.
    if is_advertising(text):
        begin(chat_id, "advertising")
        return

    send(
        chat_id,
        "Menyudan bo‘lim tanlang yoki /start buyrug‘ini yuboring.",
        MAIN_KEYBOARD,
    )


@app.get("/")
def index():
    return jsonify({
        "service": "Mening Huquqim",
        "status": "running",
        "mode": "free_no_paid_ai_api",
    }), 200


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "bot_token_configured": bool(BOT_TOKEN),
        "mode": "free_no_paid_ai_api",
    }), 200


@app.post("/webhook")
def webhook():
    if WEBHOOK_SECRET:
        supplied = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )
        if supplied != WEBHOOK_SECRET:
            return jsonify({"ok": False, "error": "unauthorized"}), 403

    update = request.get_json(silent=True) or {}
    update_id = update.get("update_id")

    with UPDATE_LOCK:
        if update_id is not None:
            if update_id in seen_updates:
                return jsonify({"ok": True, "duplicate": True}), 200

            seen_updates.add(update_id)
            seen_order.append(update_id)

            while len(seen_order) > 5000:
                old_id = seen_order.popleft()
                seen_updates.discard(old_id)

        try:
            message = update.get("message") or update.get("edited_message") or {}
            if message:
                handle_message(message)
        except Exception:
            logger.exception("Yangilanishni qayta ishlashda xato")

    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
    )
