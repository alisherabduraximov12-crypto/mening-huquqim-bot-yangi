import os
import requests
from flask import Flask, request, jsonify

# =========================================================
# SOZLAMALAR
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
OPENAI_API = "https://api.openai.com/v1/responses"

app = Flask(__name__)

# Foydalanuvchilar ma'lumotlari
users = {}


# =========================================================
# TELEGRAM YUBORISH
# =========================================================

def send_message(chat_id, text, reply_markup=None):
    if not BOT_TOKEN:
        print("BOT_TOKEN topilmadi.")
        return

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if reply_markup:
        data["reply_markup"] = reply_markup

    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=data,
            timeout=30
        )

        print("Telegram status:", response.status_code)

        if response.status_code != 200:
            print("Telegram xatosi:", response.text[:1000])

    except Exception as e:
        print("Telegram yuborish xatosi:", repr(e))


# =========================================================
# KLAVIATURALAR
# =========================================================

def main_menu():
    return {
        "keyboard": [
            [{"text": "🛒 Mahsulot muammosi"}],
            [{"text": "📝 Ariza tayyorlash"}],
            [{"text": "📚 Kerakli hujjatlar"}],
            [{"text": "⚖️ Huquqlarim"}],
            [{"text": "📞 Biz bilan bog‘lanish"}]
        ],
        "resize_keyboard": True
    }


def yes_no_keyboard():
    return {
        "keyboard": [
            [{"text": "✅ Ha"}, {"text": "❌ Yo‘q"}]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": True
    }


def back_keyboard():
    return {
        "keyboard": [
            [{"text": "🔙 Bosh menyu"}]
        ],
        "resize_keyboard": True
    }


# =========================================================
# START
# =========================================================

def start_user(chat_id):
    users[chat_id] = {
        "step": "menu",
        "case": {}
    }

    send_message(
        chat_id,
        """👋 Assalomu alaykum!

🛡 MENING HUQUQIM botiga xush kelibsiz.

Bu bot iste’molchilarga:
• o‘z huquqlarini tushunish;
• muammoli vaziyat bo‘yicha dastlabki yo‘l-yo‘riq olish;
• kerakli hujjatlarni aniqlash;
• murojaat va ariza tayyorlashda yordam beradi.

Kerakli bo‘limni tanlang:""",
        main_menu()
    )


# =========================================================
# YORDAMCHI
# =========================================================

def normalize_yes_no(text):
    text = text.strip().lower()

    if text in ["ha", "✅ ha", "yes"]:
        return "Ha"

    if text in ["yo‘q", "yo'q", "❌ yo‘q", "yoq", "no"]:
        return "Yo‘q"

    return None


def start_product_case(chat_id):
    users[chat_id] = {
        "step": "product_name",
        "case": {}
    }

    send_message(
        chat_id,
        """🛒 MAHSULOT MUAMMOSI

Muammo bo‘lgan mahsulot nomini yozing.

Masalan:
• muzlatkich
• televizor
• telefon
• kompyuter""",
        back_keyboard()
    )


# =========================================================
# MAHSULOT MUAMMOSI
# =========================================================

def process_case(chat_id, text):
    user = users.setdefault(
        chat_id,
        {
            "step": "menu",
            "case": {}
        }
    )

    step = user.get("step")
    case = user.setdefault("case", {})

    # -----------------------------------------------------
    # 1. MAHSULOT
    # -----------------------------------------------------

    if step == "product_name":
        case["product"] = text
        user["step"] = "purchase_date"

        send_message(
            chat_id,
            """📅 Mahsulotni qachon sotib olgansiz?

Masalan:
11.06.2026""",
            back_keyboard()
        )
        return

    # -----------------------------------------------------
    # 2. XARID SANASI
    # -----------------------------------------------------

    if step == "purchase_date":
        case["purchase_date"] = text
        user["step"] = "problem"

        send_message(
            chat_id,
            """❗ Mahsulotda qanday muammo yuzaga keldi?

Muammoni imkon qadar batafsil yozing.

Masalan:
“Kompyuter ishlayotgan vaqtda qotib qoladi va qayta ishga tushadi.”""",
            back_keyboard()
        )
        return

    # -----------------------------------------------------
    # 3. MUAMMO
    # -----------------------------------------------------

    if step == "problem":
        case["problem"] = text
        user["step"] = "seller_contacted"

        send_message(
            chat_id,
            "👤 Sotuvchiga murojaat qilganmisiz?",
            yes_no_keyboard()
        )
        return

    # -----------------------------------------------------
    # 4. SOTUVCHIGA MUROJAAT
    # -----------------------------------------------------

    if step == "seller_contacted":
        answer = normalize_yes_no(text)

        if not answer:
            send_message(
                chat_id,
                "Iltimos, tugmalardan birini tanlang:",
                yes_no_keyboard()
            )
            return

        case["seller_contacted"] = answer

        if answer == "Ha":
            user["step"] = "seller_response"

            send_message(
                chat_id,
                """👤 Sotuvchi sizga qanday javob berdi?

Javobini batafsil yozing.

Masalan:
“Servis markaziga murojaat qilishni aytdi.”
“Mahsulotni almashtirib berishni rad etdi.”
“Ta’mirlashga yuborishini aytdi.”""",
                back_keyboard()
            )
        else:
            user["step"] = "service_contacted"

            send_message(
                chat_id,
                "🔧 Servis markaziga murojaat qilganmisiz?",
                yes_no_keyboard()
            )

        return

    # -----------------------------------------------------
    # 5. SOTUVCHI JAVOBI
    # -----------------------------------------------------

    if step == "seller_response":
        case["seller_response"] = text
        user["step"] = "service_contacted"

        send_message(
            chat_id,
            "🔧 Servis markaziga murojaat qilganmisiz?",
            yes_no_keyboard()
        )
        return

    # -----------------------------------------------------
    # 6. SERVISGA MUROJAAT
    # -----------------------------------------------------

    if step == "service_contacted":
        answer = normalize_yes_no(text)

        if not answer:
            send_message(
                chat_id,
                "Iltimos, tugmalardan birini tanlang:",
                yes_no_keyboard()
            )
            return

        case["service_contacted"] = answer

        if answer == "Ha":
            user["step"] = "service_response"

            send_message(
                chat_id,
                """🔧 Servis markazi qanday xulosa yoki javob berdi?

Masalan:
“Nosozlik ishlab chiqarish nuqsoni ekanligi aniqlandi.”
“Ta’mirlash kerak.”
“Nosozlik aniqlanmadi.”

Agar javob bo‘lmagan bo‘lsa, shuni ham yozishingiz mumkin.""",
                back_keyboard()
            )
        else:
            user["step"] = "receipt"

            send_message(
                chat_id,
                "🧾 Xarid cheki yoki to‘lovni tasdiqlovchi hujjat bormi?",
                yes_no_keyboard()
            )

        return

    # -----------------------------------------------------
    # 7. SERVIS JAVOBI
    # -----------------------------------------------------

    if step == "service_response":
        case["service_response"] = text
        user["step"] = "receipt"

        send_message(
            chat_id,
            "🧾 Xarid cheki yoki to‘lovni tasdiqlovchi hujjat bormi?",
            yes_no_keyboard()
        )
        return

    # -----------------------------------------------------
    # 8. CHEK
    # -----------------------------------------------------

    if step == "receipt":
        answer = normalize_yes_no(text)

        if not answer:
            send_message(
                chat_id,
                "Iltimos, tugmalardan birini tanlang:",
                yes_no_keyboard()
            )
            return

        case["receipt"] = answer
        user["step"] = "warranty"

        send_message(
            chat_id,
            "🛡 Mahsulotga kafolat berilganmi?",
            yes_no_keyboard()
        )
        return

    # -----------------------------------------------------
    # 9. KAFOLAT
    # -----------------------------------------------------

    if step == "warranty":
        answer = normalize_yes_no(text)

        if not answer:
            send_message(
                chat_id,
                "Iltimos, tugmalardan birini tanlang:",
                yes_no_keyboard()
            )
            return

        case["warranty"] = answer
        user["step"] = "credit"

        send_message(
            chat_id,
            "💳 Mahsulot bo‘lib-bo‘lib to‘lash yoki kredit asosida olinganmi?",
            yes_no_keyboard()
        )
        return

    # -----------------------------------------------------
    # 10. KREDIT
    # -----------------------------------------------------

    if step == "credit":
        answer = normalize_yes_no(text)

        if not answer:
            send_message(
                chat_id,
                "Iltimos, tugmalardan birini tanlang:",
                yes_no_keyboard()
            )
            return

        case["credit"] = answer
        user["step"] = "contract"

        send_message(
            chat_id,
            "📄 Shartnoma mavjudmi?",
            yes_no_keyboard()
        )
        return

    # -----------------------------------------------------
    # 11. SHARTNOMA
    # -----------------------------------------------------

    if step == "contract":
        answer = normalize_yes_no(text)

        if not answer:
            send_message(
                chat_id,
                "Iltimos, tugmalardan birini tanlang:",
                yes_no_keyboard()
            )
            return

        case["contract"] = answer
        user["step"] = "evidence"

        send_message(
            chat_id,
            """📎 Qo‘shimcha dalillar bormi?

Masalan:
• foto
• video
• servis xulosasi
• sotuvchi bilan yozishmalar
• boshqa hujjatlar

Bor bo‘lsa yozing.
Bo‘lmasa: 0 deb yozing.""",
            back_keyboard()
        )
        return

    # -----------------------------------------------------
    # 12. DALILLAR
    # -----------------------------------------------------

    if step == "evidence":
        if text.strip() == "0":
            case["evidence"] = "Mavjud emas"
        else:
            case["evidence"] = text

        user["step"] = "finish"

        send_message(
            chat_id,
            "⏳ Murojaatingiz tahlil qilinmoqda...",
            back_keyboard()
        )

        result = analyze_case_with_ai(case)

        if result:
            send_message(chat_id, result, main_menu())
        else:
            send_message(
                chat_id,
                """⚠️ AI tahlili vaqtincha amalga oshmadi.

Siz kiritgan ma’lumotlar qabul qilindi.

🔄 Keyinroq qayta urinib ko‘rishingiz mumkin.""",
                main_menu()
            )

        user["step"] = "menu"
        return


# =========================================================
# AI PROMPT
# =========================================================

AI_INSTRUCTIONS = """
Siz O‘zbekiston Respublikasida iste’molchilar huquqlarini himoya qilish
bo‘yicha yordamchi ekspert sifatida ishlaysiz.

Sizning vazifangiz iste’molchi taqdim etgan vaziyatni dastlabki tahlil qilish.

Tahlilda:
1. Vaziyatni qisqacha tushuntiring.
2. Iste’molchining ehtimoliy huquqlarini ko‘rsating.
3. Sotuvchi yoki ijrochiga qanday talab qo‘yish mumkinligini tushuntiring.
4. Qanday hujjat va dalillar kerakligini ko‘rsating.
5. Keyingi amaliy qadamlarni tartib bilan yozing.
6. Agar masala Raqobat qo‘mitasi vakolatiga kirmasa,
   tegishli vakolatli organga murojaat qilish kerakligini ayting.
7. Sudga murojaat qilish zarur bo‘lishi mumkin bo‘lgan holatlarda
   buni aniq tushuntiring.

Javob o‘zbek tilida bo‘lsin.

Juda muhim:
- Qonun moddasini bilmasangiz, raqamni o‘ylab topmang.
- Noto‘g‘ri huquqiy xulosa bermang.
- “Aniq yutasiz”, “albatta pulingizni qaytarasiz” kabi kafolatli
  iboralarni ishlatmang.
- Bu dastlabki huquqiy yo‘l-yo‘riq ekanini ko‘rsating.
- Javob sodda, amaliy va tushunarli bo‘lsin.

Javob quyidagi tuzilishda bo‘lsin:

⚖️ MUROJAAT TAHLILI

📌 Vaziyat:
...

⚖️ Iste’molchi huquqi:
...

📋 Tavsiya:
1. ...
2. ...
3. ...

📎 Kerakli hujjatlar:
...

🏛 Keyingi murojaat:
...

⚠️ Muhim:
...
"""


def build_case_prompt(case):
    return f"""
Iste’molchi murojaati:

🛒 Mahsulot:
{case.get("product", "-")}

📅 Xarid sanasi:
{case.get("purchase_date", "-")}

❗ Muammo:
{case.get("problem", "-")}

👤 Sotuvchiga murojaat:
{case.get("seller_contacted", "-")}

👤 Sotuvchi javobi:
{case.get("seller_response", "Mavjud emas")}

🔧 Servis markaziga murojaat:
{case.get("service_contacted", "-")}

🔧 Servis javobi/xulosasi:
{case.get("service_response", "Mavjud emas")}

🧾 Chek yoki to‘lov hujjati:
{case.get("receipt", "-")}

🛡 Kafolat:
{case.get("warranty", "-")}

💳 Kredit/bo‘lib-bo‘lib to‘lash:
{case.get("credit", "-")}

📄 Shartnoma:
{case.get("contract", "-")}

📎 Qo‘shimcha dalillar:
{case.get("evidence", "-")}
"""


# =========================================================
# OPENAI AI TAHLIL
# =========================================================

def analyze_case_with_ai(case):
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY topilmadi.")
        return None

    prompt = build_case_prompt(case)

    print("AI so‘rovi yuborilmoqda...")
    print("Model:", OPENAI_MODEL)

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENAI_MODEL,
        "instructions": AI_INSTRUCTIONS,
        "input": prompt
    }

    try:
        response = requests.post(
            OPENAI_API,
            headers=headers,
            json=payload,
            timeout=60
        )

        print("OpenAI HTTP status:", response.status_code)

        if response.status_code != 200:
            print(
                "OPENAI HTTP XATOSI:",
                response.text[:2000]
            )
            return None

        data = response.json()

        # Oddiy output_text
        result = data.get("output_text")

        if result:
            return result.strip()

        # Responses API output strukturasini tekshirish
        for item in data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    text = content.get("text")

                    if text:
                        return text.strip()

        print(
            "OpenAI javobi olindi, lekin matn topilmadi:",
            str(data)[:3000]
        )

        return None

    except requests.exceptions.Timeout as e:
        print("OPENAI TIMEOUT XATOSI:", repr(e))
        return None

    except requests.exceptions.RequestException as e:
        print(
            "OPENAI CONNECTION/REQUEST XATOSI:",
            repr(e)
        )
        return None

    except Exception as e:
        print("OPENAI UMUMIY XATOSI:", repr(e))
        return None


# =========================================================
# ARIZA TAYYORLASH
# =========================================================

def prepare_application(chat_id):
    user = users.get(chat_id)

    if not user or not user.get("case"):
        send_message(
            chat_id,
            """📝 ARIZA TAYYORLASH

Avval 🛒 Mahsulot muammosi bo‘limida
murojaat ma’lumotlarini kiriting.

Shundan so‘ng arizani tayyorlash mumkin.""",
            main_menu()
        )
        return

    case = user["case"]

    application = f"""📝 ISTE’MOLCHI MUROJAATI

Kimga: ______________________________

Kimdan: _____________________________
Telefon: ____________________________

ARIZA

Men, _______________________________,
{case.get("purchase_date", "________")} kuni
{case.get("product", "________________")} mahsulotini xarid qilganman.

Mahsulotda quyidagi muammo yuzaga kelgan:

{case.get("problem", "________________________________")}

Mazkur masala yuzasidan sotuvchiga murojaat qilganman.

Sotuvchining javobi:
{case.get("seller_response", "________________________________")}

Servis markaziga murojaat qilingan:
{case.get("service_contacted", "________________")}

Servis markazi javobi:
{case.get("service_response", "________________________________")}

Xaridni tasdiqlovchi hujjat:
{case.get("receipt", "________________")}

Mahsulot kafolatlangan:
{case.get("warranty", "________________")}

Shu munosabat bilan amaldagi qonunchilikka muvofiq
murojaatimni ko‘rib chiqishingizni va qonuniy talabimni
qanoatlantirishingizni so‘rayman.

Talabim:
____________________________________
____________________________________

Ilova qilinadigan hujjatlar:
1. Xarid cheki/to‘lov hujjati;
2. Kafolat hujjati;
3. Servis xulosasi;
4. Shartnoma;
5. Boshqa dalillar.

Sana: _____________

Imzo: _____________
"""

    send_message(
        chat_id,
        application,
        main_menu()
    )


# =========================================================
# HUQUQLAR
# =========================================================

def rights_info(chat_id):
    send_message(
        chat_id,
        """⚖️ ISTE’MOLCHINING ASOSIY HUQUQLARI

Iste’molchi:

• tovar va xizmatlar haqida to‘liq va ishonchli
  ma’lumot olish;

• qonunchilikda belgilangan talablarga javob beradigan
  sifatli va xavfsiz tovar olish;

• nuqsonli tovar bo‘yicha qonunchilikda nazarda tutilgan
  talablarni qo‘yish;

• o‘z huquqlari buzilganda vakolatli organlarga va
  qonunchilikda belgilangan tartibda sudga murojaat qilish
  huquqiga ega.

Aniq vaziyatingiz bo‘yicha dastlabki tahlil olish uchun
🛒 Mahsulot muammosi bo‘limidan foydalaning.""",
        main_menu()
    )


# =========================================================
# HUJJATLAR
# =========================================================

def documents_info(chat_id):
    send_message(
        chat_id,
        """📚 KERAKLI HUJJATLAR

Vaziyatga qarab quyidagi hujjatlar foydali bo‘lishi mumkin:

🧾 Xarid cheki yoki to‘lov hujjati
📄 Shartnoma
🛡 Kafolat hujjati
🔧 Servis markazi xulosasi
📸 Foto va video dalillar
💬 Sotuvchi bilan yozishmalar
📑 Yozma murojaat va unga berilgan javob

⚠️ Qaysi hujjatlar kerakligi muammoning turiga qarab
farq qilishi mumkin.""",
        main_menu()
    )


# =========================================================
# ALOQA
# =========================================================

def contact_info(chat_id):
    send_message(
        chat_id,
        """📞 BIZ BILAN BOG‘LANISH

👤 Mutaxassis:
@Qul_Umidi

Savolingizni yozib qoldirishingiz mumkin.""",
        main_menu()
    )


# =========================================================
# TELEGRAM UPDATE
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return "Mening Huquqim bot ishlayapti."


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "telegram": bool(BOT_TOKEN),
        "openai": bool(OPENAI_API_KEY),
        "model": OPENAI_MODEL
    })


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(silent=True)

        if not update:
            return jsonify({"ok": True})

        message = update.get("message")

        if not message:
            return jsonify({"ok": True})

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        text = message.get("text", "").strip()

        if not chat_id:
            return jsonify({"ok": True})

        print(
            "Telegram xabar:",
            chat_id,
            text
        )

        # -------------------------------------------------
        # START
        # -------------------------------------------------

        if text == "/start":
            start_user(chat_id)
            return jsonify({"ok": True})

        # -------------------------------------------------
        # BOSH MENYU
        # -------------------------------------------------

        if text == "🔙 Bosh menyu":
            start_user(chat_id)
            return jsonify({"ok": True})

        # -------------------------------------------------
        # MAHSULOT MUAMMOSI
        # -------------------------------------------------

        if text == "🛒 Mahsulot muammosi":
            start_product_case(chat_id)
            return jsonify({"ok": True})

        # -------------------------------------------------
        # ARIZA
        # -------------------------------------------------

        if text == "📝 Ariza tayyorlash":
            prepare_application(chat_id)
            return jsonify({"ok": True})

        # -------------------------------------------------
        # HUJJATLAR
        # -------------------------------------------------

        if text == "📚 Kerakli hujjatlar":
            documents_info(chat_id)
            return jsonify({"ok": True})

        # -------------------------------------------------
        # HUQUQLAR
        # -------------------------------------------------

        if text == "⚖️ Huquqlarim":
            rights_info(chat_id)
            return jsonify({"ok": True})

        # -------------------------------------------------
        # ALOQA
        # -------------------------------------------------

        if text == "📞 Biz bilan bog‘lanish":
            contact_info(chat_id)
            return jsonify({"ok": True})

        # -------------------------------------------------
        # FOYDALANUVCHI MAVJUD BO‘LMASA
        # -------------------------------------------------

        if chat_id not in users:
            start_user(chat_id)
            return jsonify({"ok": True})

        # -------------------------------------------------
        # CASE PROCESS
        # -------------------------------------------------

        process_case(chat_id, text)

        return jsonify({"ok": True})

    except Exception as e:
        print("WEBHOOK XATOSI:", repr(e))

        return jsonify({
            "ok": False,
            "error": str(e)
        }), 200


# =========================================================
# WEBHOOKNI O‘RNATISH
# =========================================================

def set_webhook():
    if not BOT_TOKEN:
        print("BOT_TOKEN mavjud emas.")
        return

    render_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not render_url:
        print("RENDER_EXTERNAL_URL topilmadi.")
        return

    webhook_url = render_url.rstrip("/") + "/webhook"

    try:
        response = requests.post(
            f"{TELEGRAM_API}/setWebhook",
            json={"url": webhook_url},
            timeout=30
        )

        print(
            "Webhook o‘rnatish:",
            response.status_code,
            response.text[:1000]
        )

    except Exception as e:
        print(
            "Webhook o‘rnatish xatosi:",
            repr(e)
        )


# =========================================================
# ISHGA TUSHIRISH
# =========================================================

if __name__ == "__main__":
    print("======================================")
    print("MENING HUQUQIM BOT")
    print("======================================")
    print("BOT_TOKEN:", bool(BOT_TOKEN))
    print("OPENAI_API_KEY:", bool(OPENAI_API_KEY))
    print("OPENAI_MODEL:", OPENAI_MODEL)

    set_webhook()

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
