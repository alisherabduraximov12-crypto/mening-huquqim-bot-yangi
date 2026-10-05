import os
import requests
from flask import Flask, request, jsonify

# =========================
# SOZLAMALAR
# =========================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# OpenAI modeli
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")

# Render'dagi aniq webhook manzili
WEBHOOK_URL = "https://mening-huquqim-bot-yangi.onrender.com/webhook"

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OPENAI_API = "https://api.openai.com/v1/responses"

app = Flask(__name__)

# Foydalanuvchi ma'lumotlari
users = {}


# =========================
# TELEGRAM FUNKSIYALAR
# =========================

def send_message(chat_id, text, keyboard=None):
    if not BOT_TOKEN:
        print("BOT_TOKEN topilmadi.")
        return

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True
        }

    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=data,
            timeout=30
        )

        print(
            "Telegram javobi:",
            response.status_code,
            response.text[:500]
        )

    except Exception as e:
        print("Telegram xatosi:", repr(e))


def set_webhook():
    if not BOT_TOKEN:
        print("BOT_TOKEN mavjud emas.")
        return

    try:
        response = requests.post(
            f"{TELEGRAM_API}/setWebhook",
            json={
                "url": WEBHOOK_URL
            },
            timeout=30
        )

        print(
            "WEBHOOK O‘RNATISH:",
            response.status_code,
            response.text[:2000]
        )

        # Webhook holatini tekshiramiz
        info = requests.get(
            f"{TELEGRAM_API}/getWebhookInfo",
            timeout=30
        )

        print(
            "WEBHOOK INFO:",
            info.status_code,
            info.text[:3000]
        )

    except Exception as e:
        print("Webhook xatosi:", repr(e))


# =========================
# KEYBOARD
# =========================

MAIN_KEYBOARD = [
    ["🛒 Mahsulot muammosi"],
    ["📝 Ariza tayyorlash"],
    ["📚 Kerakli hujjatlar"],
    ["⚖️ Huquqlarim"],
    ["📞 Biz bilan bog‘lanish"]
]

YES_NO_KEYBOARD = [
    ["✅ Ha", "❌ Yo‘q"]
]

SERVICE_KEYBOARD = [
    ["✅ Ha", "❌ Yo‘q"],
    ["⏭ O‘tkazib yuborish"]
]


# =========================
# START
# =========================

def start_command(chat_id):
    users[chat_id] = {
        "step": None,
        "case": {}
    }

    send_message(
        chat_id,
        "👋 Assalomu alaykum!\n\n"
        "🛡 Mening Huquqim botiga xush kelibsiz.\n\n"
        "Men iste’molchi huquqlari bo‘yicha "
        "muammoingizni tushunishga, kerakli hujjatlarni "
        "aniqlashga va murojaat tayyorlashga yordam beraman.\n\n"
        "Quyidagi bo‘limlardan birini tanlang:",
        MAIN_KEYBOARD
    )


# =========================
# MUAMMO BOSHLASH
# =========================

def start_case(chat_id):
    users[chat_id] = {
        "step": "product",
        "case": {}
    }

    send_message(
        chat_id,
        "🛒 MUAMMOINGIZNI ANIQLAYMIZ\n\n"
        "Avvalo muammoingizni batafsil yozing.\n\n"
        "Masalan:\n"
        "“Do‘kondan televizor sotib oldim. "
        "3 kundan keyin ishlamay qoldi. "
        "Sotuvchi pulimni qaytarmayapti.”",
        MAIN_KEYBOARD
    )


# =========================
# HUQUQLAR
# =========================

def show_rights(chat_id):
    send_message(
        chat_id,
        "⚖️ ISTE’MOLCHINING ASOSIY HUQUQLARI\n\n"
        "1️⃣ Tovar haqida to‘liq va ishonchli ma’lumot olish.\n\n"
        "2️⃣ Sifatli va xavfsiz tovar sotib olish.\n\n"
        "3️⃣ Nuqsonli tovar bo‘yicha qonunda nazarda "
        "tutilgan talablarni qo‘yish.\n\n"
        "4️⃣ Yetkazilgan zarar qoplanishini talab qilish.\n\n"
        "5️⃣ O‘z huquqlarini himoya qilish uchun vakolatli "
        "organlarga yoki sudga murojaat qilish.\n\n"
        "6️⃣ Tovar va xizmatlar bo‘yicha zarur hujjatlarni "
        "talab qilish.\n\n"
        "⚠️ Aniq huquqiy baho muammoning holatiga va "
        "mavjud hujjatlarga qarab beriladi.",
        MAIN_KEYBOARD
    )


# =========================
# HUJJATLAR
# =========================

def show_documents(chat_id):
    send_message(
        chat_id,
        "📚 KERAKLI HUJJATLAR\n\n"
        "Muammo turiga qarab quyidagi hujjatlar kerak bo‘lishi mumkin:\n\n"
        "🧾 Chek yoki to‘lovni tasdiqlovchi hujjat\n"
        "📄 Shartnoma\n"
        "📦 Tovar hujjatlari\n"
        "🛠 Kafolat taloni\n"
        "📸 Foto va videolar\n"
        "💬 Sotuvchi bilan yozishmalar\n"
        "📑 Ekspertiza xulosasi\n"
        "📝 Oldingi murojaatlar nusxasi\n\n"
        "Hujjatlar qanchalik to‘liq bo‘lsa, murojaatni "
        "o‘rganish shunchalik oson bo‘ladi.",
        MAIN_KEYBOARD
    )


# =========================
# ALOQA
# =========================

def show_contact(chat_id):
    send_message(
        chat_id,
        "📞 BIZ BILAN BOG‘LANISH\n\n"
        "👨‍💼 Mutaxassis bilan aloqa:\n"
        "@Qul_Umidi\n\n"
        "📌 Murojaatingizda muammoingizni aniq yozing "
        "va mavjud hujjatlarni saqlab qo‘ying.",
        MAIN_KEYBOARD
    )


# =========================
# OPENAI PROMPT
# =========================

AI_INSTRUCTIONS = """
Siz O‘zbekiston Respublikasida iste’molchilar huquqlarini
himoya qilish bo‘yicha yordamchi AI mutaxassissiz.

Vazifangiz:
- iste’molchi murojaatini tushunish;
- muammoning mohiyatini aniqlash;
- iste’molchining ehtimoliy huquqlarini tushuntirish;
- qanday hujjatlar kerakligini ko‘rsatish;
- sotuvchiga qanday talab qo‘yish mumkinligini tushuntirish;
- Raqobat va iste’molchilar huquqlarini himoya qilish
  qo‘mitasi vakolatiga kirishi yoki kirmasligini ehtiyotkorlik
  bilan tushuntirish;
- zarur hollarda sudga, ekspertizaga yoki boshqa vakolatli
  organga murojaat qilish kerakligini aytish.

Javobni o‘zbek tilida yozing.

Muhim:
Aniq bo‘lmagan ma’lumotni fakt sifatida yozmang.
Qonun moddasini ishonchingiz komil bo‘lmasa raqamini
o‘ylab topmang.

Javob quyidagi tartibda bo‘lsin:

🔎 MUAMMO TAHLILI
⚖️ ISTE’MOLCHINING HUQUQI
📄 KERAKLI HUJJATLAR
📝 QANDAY HARAKAT QILISH KERAK
🏛 QAYERGA MUROJAAT QILISH MUMKIN

Javob sodda, amaliy va tushunarli bo‘lsin.
"""


def build_case_prompt(case):
    return f"""
Iste’molchi murojaati:

Muammo:
{case.get("product", "")}

Sotuvchiga murojaat qilinganmi:
{case.get("seller_contact", "")}

Sotuvchining javobi:
{case.get("seller_answer", "")}

Xizmat ko‘rsatuvchi yoki boshqa tashkilotga
murojaat qilinganmi:
{case.get("service_contact", "")}

Qo‘shimcha ma’lumot:
{case.get("extra", "")}

Yuqoridagi ma’lumotlar asosida iste’molchiga
amaliy va huquqiy yo‘nalish bering.
"""


# =========================
# AI TAHLIL
# =========================

def analyze_case_with_ai(case):
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY topilmadi.")
        return None

    prompt = build_case_prompt(case)

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENAI_MODEL,
        "instructions": AI_INSTRUCTIONS,
        "input": prompt
    }

    print("================================")
    print("AI SO‘ROVI YUBORILMOQDA")
    print("Model:", OPENAI_MODEL)
    print("================================")

    try:
        response = requests.post(
            OPENAI_API,
            headers=headers,
            json=payload,
            timeout=90
        )

        print(
            "OPENAI HTTP STATUS:",
            response.status_code
        )

        print(
            "OPENAI JAVOB:",
            response.text[:3000]
        )

        if response.status_code != 200:
            return None

        data = response.json()

        # output_text mavjud bo‘lsa
        result = data.get("output_text")

        if result:
            return result.strip()

        # output ichidan olish
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content.get("text")

                    if text:
                        return text.strip()

        print("AI matni topilmadi.")

        return None

    except requests.exceptions.Timeout as e:
        print("OPENAI TIMEOUT:", repr(e))
        return None

    except requests.exceptions.RequestException as e:
        print("OPENAI REQUEST XATOSI:", repr(e))
        return None

    except Exception as e:
        print("OPENAI UMUMIY XATO:", repr(e))
        return None


# =========================
# ARIZA
# =========================

def create_application(chat_id):
    user = users.get(chat_id)

    if not user or not user.get("case"):
        send_message(
            chat_id,
            "📝 ARIZA TAYYORLASH\n\n"
            "Avval 🛒 Mahsulot muammosi bo‘limiga kirib, "
            "muammoingiz haqidagi ma’lumotlarni kiriting.\n\n"
            "Shundan so‘ng siz uchun ariza shaklini "
            "tayyorlashga harakat qilaman.",
            MAIN_KEYBOARD
        )
        return

    case = user["case"]

    application = f"""
📝 ISTE’MOLCHI MUROJAATI

Kimga: ______________________________

Kimdan: _____________________________
Telefon: ____________________________

ARIZA

Men quyidagi masala yuzasidan murojaat qilmoqdaman:

{case.get("product", "")}

Mazkur holat yuzasidan sotuvchi/tadbirkorga
murojaat qilganman:

{case.get("seller_contact", "")}

Sotuvchi/tadbirkorning javobi:

{case.get("seller_answer", "")}

Qo‘shimcha ma’lumot:

{case.get("extra", "")}

Yuqoridagilarni inobatga olib, murojaatimni
belgilangan tartibda ko‘rib chiqishingizni va
qonunchilikka muvofiq huquqlarimni tiklashda
amaliy yordam berishingizni so‘rayman.

Sana: ______________

Imzo: ______________
"""

    send_message(
        chat_id,
        application,
        MAIN_KEYBOARD
    )


# =========================
# USER XABARINI QAYTA ISHLASH
# =========================

def handle_text(chat_id, text):

    # START
    if text == "/start":
        start_command(chat_id)
        return

    # MAIN MENU
    if text == "🛒 Mahsulot muammosi":
        start_case(chat_id)
        return

    if text == "📚 Kerakli hujjatlar":
        show_documents(chat_id)
        return

    if text == "⚖️ Huquqlarim":
        show_rights(chat_id)
        return

    if text == "📞 Biz bilan bog‘lanish":
        show_contact(chat_id)
        return

    if text == "📝 Ariza tayyorlash":
        create_application(chat_id)
        return

    # USER MA'LUMOTI
    if chat_id not in users:
        start_command(chat_id)
        return

    user = users[chat_id]
    step = user.get("step")
    case = user.setdefault("case", {})

    # 1. MUAMMO
    if step == "product":

        case["product"] = text
        user["step"] = "seller_contact"

        send_message(
            chat_id,
            "📌 Sotuvchiga yoki do‘konga murojaat qildingizmi?",
            YES_NO_KEYBOARD
        )

        return

    # 2. SOTUVCHIGA MUROJAAT
    if step == "seller_contact":

        case["seller_contact"] = text
        user["step"] = "seller_answer"

        send_message(
            chat_id,
            "📌 Sotuvchi yoki do‘kon sizga qanday javob berdi?\n\n"
            "Javobini yozing.\n\n"
            "Agar javob bermagan bo‘lsa, "
            "“Javob bermadi” deb yozing."
        )

        return

    # 3. SOTUVCHI JAVOBI
    if step == "seller_answer":

        case["seller_answer"] = text
        user["step"] = "extra"

        send_message(
            chat_id,
            "📌 Qo‘shimcha ma’lumot bormi?\n\n"
            "Masalan:\n"
            "- chek bor;\n"
            "- kafolat taloni bor;\n"
            "- foto/video bor;\n"
            "- ekspertiza xulosasi bor;\n"
            "- yoki boshqa muhim ma’lumot.\n\n"
            "Agar qo‘shimcha ma’lumot bo‘lmasa, "
            "“Yo‘q” deb yozing."
        )

        return

    # 4. QO‘SHIMCHA MA'LUMOT
    if step == "extra":

        case["extra"] = text
        user["step"] = "completed"

        send_message(
            chat_id,
            "⏳ Murojaatingiz tahlil qilinmoqda..."
        )

        result = analyze_case_with_ai(case)

        if result:

            send_message(
                chat_id,
                "🤖 AI TAHLILI\n\n" + result,
                MAIN_KEYBOARD
            )

            send_message(
                chat_id,
                "📝 Murojaatingiz asosida ariza ham "
                "tayyorlashingiz mumkin.\n\n"
                "Quyidagi tugmani bosing:",
                MAIN_KEYBOARD
            )

        else:

            send_message(
                chat_id,
                "⚠️ AI tahlili vaqtincha amalga oshmadi.\n\n"
                "Siz kiritgan ma’lumotlar qabul qilindi.\n\n"
                "🔄 Keyinroq qayta urinib ko‘rishingiz mumkin.",
                MAIN_KEYBOARD
            )

        return

    # Agar tushunarsiz xabar bo‘lsa
    send_message(
        chat_id,
        "Iltimos, quyidagi bo‘limlardan birini tanlang:",
        MAIN_KEYBOARD
    )


# =========================
# WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():

    try:
        update = request.get_json(force=True)

        print("================================")
        print("TELEGRAM UPDATE:")
        print(update)
        print("================================")

        message = update.get("message")

        if not message:
            return jsonify({"ok": True})

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        text = message.get("text")

        if chat_id and text:
            handle_text(chat_id, text)

        return jsonify({"ok": True})

    except Exception as e:

        print("WEBHOOK XATOSI:", repr(e))

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 200


# =========================
# HEALTH
# =========================

@app.route("/", methods=["GET"])
def home():
    return "Mening Huquqim bot ishlayapti."


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "bot_token": bool(BOT_TOKEN),
        "openai_key": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL,
        "webhook": WEBHOOK_URL
    })


# =========================
# ISHGA TUSHISH
# =========================

if __name__ == "__main__":

    print("================================")
    print("MENING HUQUQIM BOT")
    print("================================")

    print("BOT_TOKEN mavjud:", bool(BOT_TOKEN))
    print("OPENAI_API_KEY mavjud:", bool(OPENAI_API_KEY))
    print("OPENAI_MODEL:", OPENAI_MODEL)
    print("WEBHOOK_URL:", WEBHOOK_URL)

    # Webhook o‘rnatish
    set_webhook()

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
