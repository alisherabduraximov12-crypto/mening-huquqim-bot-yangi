import os
import logging
import time
import requests
from flask import Flask, request, jsonify

# Mening Huquqim Telegram bot
# Render start command: gunicorn app:app
# Required environment variables: BOT_TOKEN, OPENAI_API_KEY
# Optional: OPENAI_MODEL, WEBHOOK_SECRET

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OPENAI_API = "https://api.openai.com/v1/responses"
HTTP_TIMEOUT = 35
MAX_SEEN_UPDATES = 3000

sessions = {}
seen_update_ids = set()

MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "🛒 Mahsulot muammosi"}, {"text": "📝 Ariza tayyorlash"}],
        [{"text": "📚 Kerakli hujjatlar"}, {"text": "⚖️ Huquqlarim haqida"}],
        [{"text": "☎️ Mutaxassis bilan aloqa"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

CANCEL_WORDS = {"bekor", "bekor qilish", "cancel", "orqaga", "menyu"}
STEP_ORDER = ["product", "purchase_date", "problem", "seller", "evidence"]
STEP_PROMPTS = {
    "product": "Qaysi mahsulot yoki xizmat bo‘yicha muammo yuz berdi?",
    "purchase_date": "Qachon xarid qilgansiz yoki xizmatdan foydalangansiz? Sanani bilmasangiz, taxminiy vaqtni yozing.",
    "problem": "Muammo nimada? Nima sodir bo‘lganini batafsilroq yozing.",
    "seller": "Sotuvchi yoki xizmat ko‘rsatuvchi tashkilot nomini yozing. Bilmasangiz, «bilmayman» deb yozing.",
    "evidence": "Qanday dalillaringiz bor? Masalan, chek, shartnoma, kafolat taloni, foto, video yoki yozishma. Bo‘lmasa, «yo‘q» deb yozing.",
}


def telegram_call(method, payload):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is missing")
        return None
    try:
        response = requests.post(
            f"{TELEGRAM_API}/{method}", json=payload, timeout=HTTP_TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            logger.warning("Telegram API error: %s", result.get("description", "unknown"))
        return result
    except requests.RequestException:
        logger.exception("Telegram API request failed")
        return None


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": str(text)[:4000]}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return telegram_call("sendMessage", payload)


def reset_session(chat_id):
    sessions.pop(str(chat_id), None)


def set_session(chat_id, flow, step="product", data=None):
    sessions[str(chat_id)] = {"flow": flow, "step": step, "data": data or {}, "updated_at": time.time()}


def get_session(chat_id):
    return sessions.get(str(chat_id))


def start_text():
    return (
        "Assalomu alaykum! Men — «Mening Huquqim» yordamchi botiman.\n\n"
        "Iste’molchi muammosini tushunish, kerakli ma’lumotlarni yig‘ish va murojaat loyihasini tayyorlashga yordam beraman.\n\n"
        "Eslatma: javoblar dastlabki yo‘l-yo‘riq bo‘lib, rasmiy qaror, ekspert xulosasi yoki sud qarori hisoblanmaydi. Masala vakolatimizga kirmasa, tegishli organga murojaat qilish tavsiya etiladi.\n\n"
        "Quyidagi menyudan bo‘limni tanlang."
    )


def call_openai(prompt):
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY environment variable is missing")
        import os
import logging
import time
import requests
from flask import Flask, request, jsonify

# Mening Huquqim Telegram bot
# Render start command: gunicorn app:app
# Required environment variables: BOT_TOKEN, OPENAI_API_KEY
# Optional: OPENAI_MODEL, WEBHOOK_SECRET

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)
app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OPENAI_API = "https://api.openai.com/v1/responses"
HTTP_TIMEOUT = 35
MAX_SEEN_UPDATES = 3000

sessions = {}
seen_update_ids = set()

MAIN_KEYBOARD = {
    "keyboard": [
        [{"text": "🛒 Mahsulot muammosi"}, {"text": "📝 Ariza tayyorlash"}],
        [{"text": "📚 Kerakli hujjatlar"}, {"text": "⚖️ Huquqlarim haqida"}],
        [{"text": "☎️ Mutaxassis bilan aloqa"}],
    ],
    "resize_keyboard": True,
    "is_persistent": True,
}

CANCEL_WORDS = {"bekor", "bekor qilish", "cancel", "orqaga", "menyu"}
STEP_ORDER = ["product", "purchase_date", "problem", "seller", "evidence"]
STEP_PROMPTS = {
    "product": "Qaysi mahsulot yoki xizmat bo‘yicha muammo yuz berdi?",
    "purchase_date": "Qachon xarid qilgansiz yoki xizmatdan foydalangansiz? Sanani bilmasangiz, taxminiy vaqtni yozing.",
    "problem": "Muammo nimada? Nima sodir bo‘lganini batafsilroq yozing.",
    "seller": "Sotuvchi yoki xizmat ko‘rsatuvchi tashkilot nomini yozing. Bilmasangiz, «bilmayman» deb yozing.",
    "evidence": "Qanday dalillaringiz bor? Masalan, chek, shartnoma, kafolat taloni, foto, video yoki yozishma. Bo‘lmasa, «yo‘q» deb yozing.",
}


def telegram_call(method, payload):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is missing")
        return None
    try:
        response = requests.post(
            f"{TELEGRAM_API}/{method}", json=payload, timeout=HTTP_TIMEOUT
        )
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            logger.warning("Telegram API error: %s", result.get("description", "unknown"))
        return result
    except requests.RequestException:
        logger.exception("Telegram API request failed")
        return None


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": str(text)[:4000]}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return telegram_call("sendMessage", payload)


def reset_session(chat_id):
    sessions.pop(str(chat_id), None)


def set_session(chat_id, flow, step="product", data=None):
    sessions[str(chat_id)] = {"flow": flow, "step": step, "data": data or {}, "updated_at": time.time()}


def get_session(chat_id):
    return sessions.get(str(chat_id))


def start_text():
    return (
        "Assalomu alaykum! Men — «Mening Huquqim» yordamchi botiman.\n\n"
        "Iste’molchi muammosini tushunish, kerakli ma’lumotlarni yig‘ish va murojaat loyihasini tayyorlashga yordam beraman.\n\n"
        "Eslatma: javoblar dastlabki yo‘l-yo‘riq bo‘lib, rasmiy qaror, ekspert xulosasi yoki sud qarori hisoblanmaydi. Masala vakolatimizga kirmasa, tegishli organga murojaat qilish tavsiya etiladi.\n\n"
        "Quyidagi menyudan bo‘limni tanlang."
    )


def call_openai(prompt):
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY environment variable is missing")
         reset_session(chat_id)
    if not answer:
        answer = (
            "Kechirasiz, hozir AI xizmatiga ulanishda xatolik yuz berdi. Ma’lumotlaringiz suhbat yakunida saqlanmaydi. "
            "Birozdan so‘ng qayta urinib ko‘ring. Agar xato davom etsa, Render loglarida OpenAI API xabarini tekshirish kerak."
        )
    send_message(chat_id, answer, MAIN_KEYBOARD)


def handle_message(message):
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()
    if not chat_id:
        return
    if not text:
        send_message(chat_id, "Iltimos, matnli xabar yuboring yoki menyudan bo‘lim tanlang.", MAIN_KEYBOARD)
        return

    lowered = text.casefold()
    if lowered in CANCEL_WORDS:
        reset_session(chat_id)
        send_message(chat_id, "Joriy amal bekor qilindi. Menyudan bo‘lim tanlang.", MAIN_KEYBOARD)
        return

    if lowered in {"/start", "/help", "start"}:
        reset_session(chat_id)
        send_message(chat_id, start_text(), MAIN_KEYBOARD)
        return

    if text == "🛒 Mahsulot muammosi" or lowered == "/muammo":
        start_intake(chat_id, "problem")
        return

    if text == "📝 Ariza tayyorlash" or lowered == "/ariza":
        start_intake(chat_id, "application")
        return

    if text == "📚 Kerakli hujjatlar" or lowered == "/hujjatlar":
        send_message(
            chat_id,
            "Murojaat turiga qarab quyidagilar foydali bo‘lishi mumkin:\n"
            "• xarid cheki yoki to‘lov hujjati;\n"
            "• shartnoma, buyurtma yoki kafolat taloni;\n"
            "• foto, video yoki yozishmalar;\n"
            "• sotuvchiga yuborilgan oldingi murojaat va javob;\n"
            "• mavjud bo‘lsa, servis yoki ekspertiza xulosasi.\n\n"
            "Faqat mavjud hujjatlarni ilova qiling va asl hujjatlarni o‘zingizda saqlang.",
            MAIN_KEYBOARD,
        )
        return

    if text == "⚖️ Huquqlarim haqida" or lowered == "/huquqim":
        send_message(
            chat_id,
            "Iste’molchi tovar yoki xizmat haqida to‘g‘ri ma’lumot olish, sifatga oid talablar buzilganda o‘z huquqlarini himoya qilish va tegishli tartibda murojaat qilish imkoniyatiga ega. Aniq talab vaziyat va amaldagi qonunchilikka bog‘liq.\n\n"
            "Muammoingizni «🛒 Mahsulot muammosi» bo‘limida yozing. Bot javobi dastlabki ma’lumotdir.",
            MAIN_KEYBOARD,
        )
        return

    if text == "☎️ Mutaxassis bilan aloqa" or lowered == "/aloqa":
        send_message(
            chat_id,
            "Mutaxassis bilan aloqa:\n"
            "• Telegram: @Qul_Umidi\n"
            "• Qo‘mita qisqa raqami: 1159\n\n"
            "Bog‘lanish ma’lumotlarini foydalanishdan oldin rasmiy manbadan tekshiring.",
            MAIN_KEYBOARD,
        )
        return

    session = get_session(chat_id)
    if session:
        process_intake_step(chat_id, text, session)
        return

    send_message(chat_id, "Menyudan bo‘lim tanlang yoki /start buyrug‘ini yuboring.", MAIN_KEYBOARD)


@app.get("/")
def index():
    return jsonify({"service": "Mening Huquqim Telegram bot", "status": "running"}), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.post("/webhook")
def webhook():
    if WEBHOOK_SECRET:
        provided_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if provided_secret != WEBHOOK_SECRET:
            return jsonify({"ok": False, "error": "unauthorized"}), 403

    update = request.get_json(silent=True) or {}
    update_id = update.get("update_id")
    if update_id is not None:
        if update_id in seen_update_ids:
            return jsonify({"ok": True, "duplicate": True}), 200
        seen_update_ids.add(update_id)
        if len(seen_update_ids) > MAX_SEEN_UPDATES:
            seen_update_ids.clear()
            seen_update_ids.add(update_id)

    try:
        message = update.get("message") or update.get("edited_message")
        if message:
            handle_message(message)
        return jsonify({"ok": True}), 200
    except Exception:
        logger.exception("Unhandled error processing Telegram update")
        # Return 200 to prevent endless Telegram retries for the same update.
        return jsonify({"ok": True}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
