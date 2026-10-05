import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# =========================
# SOZLAMALAR
# =========================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

openai_client = None

if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        print("OpenAI client muvaffaqiyatli ishga tushdi.")
    except Exception as e:
        print("OpenAI client xatosi:", repr(e))
else:
    print("OPENAI_API_KEY topilmadi.")


# =========================
# FOYDALANUVCHILAR
# =========================

users = {}


# =========================
# TELEGRAM YORDAMCHI FUNKSIYALAR
# =========================

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = keyboard

    try:
        r = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=data,
            timeout=30
        )

        print("Telegram:", r.status_code, r.text[:500])

        return r.json()

    except Exception as e:
        print("Telegram yuborish xatosi:", repr(e))
        return None


def main_keyboard():
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


def cancel_keyboard():
    return {
        "keyboard": [
            [{"text": "❌ Bekor qilish"}]
        ],
        "resize_keyboard": True
    }


# =========================
# AI UCHUN PROMPT
# =========================

AI_INSTRUCTIONS = """
Sen O‘zbekiston Respublikasida iste’molchilar huquqlarini himoya qilish
masalalari bo‘yicha yordam beruvchi AI maslahatchisan.

Sening vazifang:
- iste’molchining vaziyatini tushunarli tahlil qilish;
- O‘zbekiston Respublikasining iste’molchilar huquqlariga oid qonunchiligi
  asosida dastlabki huquqiy yo‘l-yo‘riq berish;
- iste’molchiga qanday hujjatlar kerakligini tushuntirish;
- sotuvchiga murojaat qilish tartibini ko‘rsatish;
- zarur bo‘lsa, Raqobat qo‘mitasi vakolatiga kirishi yoki kirmasligini
  tushuntirish;
- sud, ekspertiza yoki boshqa davlat organiga murojaat qilish zarur bo‘lsa,
  buni aniq aytish.

MUHIM:
- Aniq modda raqamini bilmasang, o‘ylab topma.
- Noto‘g‘ri huquqiy xulosa bermagin.
- Faqat foydalanuvchi bergan ma’lumotlarga tayan.
- Bu dastlabki maslahat ekanini ko‘rsat.
- Foydalanuvchiga amaliy qadamlarni aniq ber.
- Vaziyat Raqobat qo‘mitasi vakolatiga kirmasa, tegishli organga murojaat
  qilishni tavsiya qil.

Javob quyidagi tartibda bo‘lsin:

🔎 VAZIYAT XULOSASI

⚖️ DASTLABKI HUQUQIY BAHO

📎 MUHIM DALILLAR

🏛 VAKOLAT MASALASI

➡️ KEYINGI AMALIY QADAM

⚠️ MUHIM ESLATMA
"""


def build_case_prompt(user):
    evidence_count = len(user.get("evidence", []))

    return f"""
Iste’molchi murojaati:

Mahsulot: {user.get("product", "ko‘rsatilmagan")}
Xarid sanasi: {user.get("purchase_date", "ko‘rsatilmagan")}
Muammo: {user.get("problem", "ko‘rsatilmagan")}

Sotuvchiga murojaat qilganmi:
{user.get("seller_contacted", "ko‘rsatilmagan")}

Sotuvchining javobi:
{user.get("seller_response", "ko‘rsatilmagan")}

Servis markaziga murojaat qilganmi:
{user.get("service_contacted", "ko‘rsatilmagan")}

Servis javobi:
{user.get("service_response", "ko‘rsatilmagan")}

Chek yoki to‘lov hujjati:
{user.get("receipt", "ko‘rsatilmagan")}

Kafolat:
{user.get("warranty", "ko‘rsatilmagan")}

Bo‘lib-bo‘lib to‘lash yoki kredit:
{user.get("installment", "ko‘rsatilmagan")}

Shartnoma:
{user.get("contract", "ko‘rsatilmagan")}

Qo‘shimcha dalillar soni:
{evidence_count}

Shu ma’lumotlar asosida iste’molchiga amaliy va ehtiyotkor huquqiy
yo‘l-yo‘riq ber.
"""


# =========================
# AI TAHLIL
# =========================

def analyze_case_with_ai(user):
    if not openai_client:
        print("AI ishlamayapti: OpenAI client mavjud emas.")
        return None

    prompt = build_case_prompt(user)

    print("AI so‘rovi yuborilmoqda...")
    print("Model:", OPENAI_MODEL)

    try:
        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            instructions=AI_INSTRUCTIONS,
            input=prompt
        )

        result = getattr(response, "output_text", None)

        if result:
            print("AI javobi muvaffaqiyatli olindi.")
            return result.strip()

        print("AI javobi bo‘sh qaytdi.")
        return None

    except Exception as e:
        print("OPENAI API XATOSI:", repr(e))
        return None


# =========================
# MUROJAATNI YAKUNLASH
# =========================

def finish_case(chat_id):
    user = users.get(chat_id)

    if not user:
        send_message(
            chat_id,
            "Ma’lumotlar topilmadi. Iltimos, qaytadan boshlang.",
            main_keyboard()
        )
        return

    send_message(
        chat_id,
        "⏳ Murojaatingiz tahlil qilinmoqda..."
    )

    ai_result = analyze_case_with_ai(user)

    if ai_result:
        final_text = (
            "📋 MUROJAAT BO‘YICHA TAHLIL\n\n"
            + ai_result
        )
    else:
        final_text = f"""
📋 MUROJAAT BO‘YICHA DASTLABKI MA’LUMOT

🛒 Mahsulot:
{user.get("product", "-")}

📅 Xarid sanasi:
{user.get("purchase_date", "-")}

❗ Muammo:
{user.get("problem", "-")}

👤 Sotuvchiga murojaat:
{user.get("seller_contacted", "-")}

🔧 Servis markazi:
{user.get("service_contacted", "-")}

🧾 Chek:
{user.get("receipt", "-")}

🛡 Kafolat:
{user.get("warranty", "-")}

💳 Bo‘lib-bo‘lib to‘lash/kredit:
{user.get("installment", "-")}

📎 Qo‘shimcha dalillar:
{len(user.get("evidence", []))} ta

⚠️ AI tahlili vaqtincha ishga tushmadi.

Ma’lumotlaringiz saqlandi. Keyinchalik batafsil tahlil qilish mumkin.
"""

    send_message(
        chat_id,
        final_text,
        main_keyboard()
    )

    users.pop(chat_id, None)


# =========================
# SAVOL-BOSQICHLAR
# =========================

def start_product_case(chat_id):
    users[chat_id] = {
        "step": "product",
        "evidence": []
    }

    send_message(
        chat_id,
        "🛒 Mahsulot muammosi\n\n"
        "Muammo bo‘lgan mahsulot nomini yozing.\n\n"
        "Masalan: muzlatkich, televizor, telefon.",
        cancel_keyboard()
    )


def process_case(chat_id, text):
    user = users.get(chat_id)

    if not user:
        return False

    step = user.get("step")

    if text == "❌ Bekor qilish":
        users.pop(chat_id, None)

        send_message(
            chat_id,
            "❌ Murojaat bekor qilindi.",
            main_keyboard()
        )

        return True

    if step == "product":
        user["product"] = text
        user["step"] = "purchase_date"

        send_message(
            chat_id,
            "📅 Mahsulotni qachon sotib olgansiz?\n\n"
            "Masalan: 10.05.2026"
        )

        return True

    if step == "purchase_date":
        user["purchase_date"] = text
        user["step"] = "problem"

        send_message(
            chat_id,
            "❗ Mahsulotda qanday muammo yuzaga keldi?"
        )

        return True

    if step == "problem":
        user["problem"] = text
        user["step"] = "seller_contacted"

        send_message(
            chat_id,
            "👤 Sotuvchiga murojaat qilganmisiz?",
            {
                "keyboard": [
                    [{"text": "Ha"}, {"text": "Yo‘q"}],
                    [{"text": "❌ Bekor qilish"}]
                ],
                "resize_keyboard": True
            }
        )

        return True

    if step == "seller_contacted":
        user["seller_contacted"] = text

        if text == "Ha":
            user["step"] = "seller_response"

            send_message(
                chat_id,
                "👤 Sotuvchi sizga qanday javob berdi?"
            )
        else:
            user["seller_response"] = "-"
            user["step"] = "service_contacted"

            send_message(
                chat_id,
                "🔧 Servis markaziga murojaat qilganmisiz?",
                {
                    "keyboard": [
                        [{"text": "Ha"}, {"text": "Yo‘q"}],
                        [{"text": "❌ Bekor qilish"}]
                    ],
                    "resize_keyboard": True
                }
            )

        return True

    if step == "seller_response":
        user["seller_response"] = text
        user["step"] = "service_contacted"

        send_message(
            chat_id,
            "🔧 Servis markaziga murojaat qilganmisiz?",
            {
                "keyboard": [
                    [{"text": "Ha"}, {"text": "Yo‘q"}],
                    [{"text": "❌ Bekor qilish"}]
                ],
                "resize_keyboard": True
            }
        )

        return True

    if step == "service_contacted":
        user["service_contacted"] = text

        if text == "Ha":
            user["step"] = "service_response"

            send_message(
                chat_id,
                "🔧 Servis markazi qanday xulosa yoki javob berdi?"
            )
        else:
            user["service_response"] = "-"
            user["step"] = "receipt"

            send_message(
                chat_id,
                "🧾 Xarid cheki yoki to‘lovni tasdiqlovchi hujjat bormi?",
                {
                    "keyboard": [
                        [{"text": "Ha"}, {"text": "Yo‘q"}],
                        [{"text": "❌ Bekor qilish"}]
                    ],
                    "resize_keyboard": True
                }
            )

        return True

    if step == "service_response":
        user["service_response"] = text
        user["step"] = "receipt"

        send_message(
            chat_id,
            "🧾 Xarid cheki yoki to‘lovni tasdiqlovchi hujjat bormi?",
            {
                "keyboard": [
                    [{"text": "Ha"}, {"text": "Yo‘q"}],
                    [{"text": "❌ Bekor qilish"}]
                ],
                "resize_keyboard": True
            }
        )

        return True

    if step == "receipt":
        user["receipt"] = text
        user["step"] = "warranty"

        send_message(
            chat_id,
            "🛡 Mahsulotga kafolat berilganmi?",
            {
                "keyboard": [
                    [{"text": "Ha"}, {"text": "Yo‘q"}],
                    [{"text": "❌ Bekor qilish"}]
                ],
                "resize_keyboard": True
            }
        )

        return True

    if step == "warranty":
        user["warranty"] = text
        user["step"] = "installment"

        send_message(
            chat_id,
            "💳 Mahsulot bo‘lib-bo‘lib to‘lash yoki kredit asosida olinganmi?",
            {
                "keyboard": [
                    [{"text": "Ha"}, {"text": "Yo‘q"}],
                    [{"text": "❌ Bekor qilish"}]
                ],
                "resize_keyboard": True
            }
        )

        return True

    if step == "installment":
        user["installment"] = text
        user["step"] = "contract"

        send_message(
            chat_id,
            "📄 Shartnoma mavjudmi?",
            {
                "keyboard": [
                    [{"text": "Ha"}, {"text": "Yo‘q"}],
                    [{"text": "❌ Bekor qilish"}]
                ],
                "resize_keyboard": True
            }
        )

        return True

    if step == "contract":
        user["contract"] = text
        user["step"] = "evidence"

        send_message(
            chat_id,
            "📎 Qo‘shimcha dalillar bormi?\n\n"
            "Masalan: foto, video, servis xulosasi, yozishmalar.\n\n"
            "Bor bo‘lsa yozing. Bo‘lmasa: 0 deb yozing."
        )

        return True

    if step == "evidence":
        if text == "0":
            user["evidence"] = []
        else:
            user["evidence"] = [text]

        finish_case(chat_id)

        return True

    return False


# =========================
# START
# =========================

def handle_start(chat_id):
    users.pop(chat_id, None)

    text = """
👋 Assalomu alaykum!

🛡 MENING HUQUQIM botiga xush kelibsiz.

Bu bot iste’molchilarga o‘z huquqlarini tushunish,
muammoli vaziyat bo‘yicha dastlabki yo‘l-yo‘riq olish
va kerakli hujjatlarni tayyorlashda yordam beradi.

Kerakli bo‘limni tanlang:
"""

    send_message(
        chat_id,
        text,
        main_keyboard()
    )


# =========================
# TELEGRAM WEBHOOK
# =========================

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"ok": True})

        message = data.get("message")

        if not message:
            return jsonify({"ok": True})

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        text = message.get("text")

        if not chat_id or not text:
            return jsonify({"ok": True})

        print("Telegram xabar:", chat_id, text)

        # START
        if text == "/start":
            handle_start(chat_id)
            return jsonify({"ok": True})

        # MAHSULOT MUAMMOSI
        if text == "🛒 Mahsulot muammosi":
            start_product_case(chat_id)
            return jsonify({"ok": True})

        # ARIZA
        if text == "📝 Ariza tayyorlash":
            send_message(
                chat_id,
                "📝 Ariza tayyorlash bo‘limi hozir ishlab chiqilmoqda.\n\n"
                "Tez orada tayyor ariza shakllari qo‘shiladi.",
                main_keyboard()
            )
            return jsonify({"ok": True})

        # HUJJATLAR
        if text == "📚 Kerakli hujjatlar":
            send_message(
                chat_id,
                """
📚 KERAKLI HUJJATLAR

Odatda quyidagi hujjatlar foydali bo‘ladi:

🧾 Xarid cheki yoki to‘lov hujjati
📄 Shartnoma
🛡 Kafolat hujjati
🔧 Servis markazi xulosasi
📸 Foto va video dalillar
💬 Sotuvchi bilan yozishmalar

Vaziyatga qarab boshqa hujjatlar ham talab qilinishi mumkin.
""",
                main_keyboard()
            )
            return jsonify({"ok": True})

        # HUQUQLAR
        if text == "⚖️ Huquqlarim":
            send_message(
                chat_id,
                """
⚖️ ISTE’MOLCHINING ASOSIY HUQUQLARI

Iste’molchi tovar va xizmatlar haqida to‘liq va
ishonchli ma’lumot olish huquqiga ega.

Shuningdek, qonunchilikda belgilangan hollarda
sifatli va xavfsiz tovar olish, nuqsonli tovar
bo‘yicha o‘z qonuniy talablarini qo‘yish huquqlariga ega.

Aniq vaziyatingiz bo‘yicha huquqlaringizni bilish
uchun 🛒 Mahsulot muammosi bo‘limidan foydalaning.
""",
                main_keyboard()
            )
            return jsonify({"ok": True})

        # ALOQA
        if text == "📞 Biz bilan bog‘lanish":
            send_message(
                chat_id,
                """
📞 BIZ BILAN BOG‘LANISH

👤 Mutaxassis:
@Qul_Umidi

Savolingizni yozib qoldirishingiz mumkin.
""",
                main_keyboard()
            )
            return jsonify({"ok": True})

        # CASE PROCESS
        if chat_id in users:
            process_case(chat_id, text)
            return jsonify({"ok": True})

        # UNKNOWN
        send_message(
            chat_id,
            "Iltimos, menyudagi kerakli bo‘limni tanlang.",
            main_keyboard()
        )

        return jsonify({"ok": True})

    except Exception as e:
        print("WEBHOOK XATOSI:", repr(e))
        return jsonify({"ok": True})


# =========================
# HEALTH CHECK
# =========================

@app.route("/", methods=["GET"])
def home():
    return "Mening Huquqim bot ishlayapti!"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "openai": bool(openai_client),
        "model": OPENAI_MODEL
    })


# =========================
# WEBHOOK O‘RNATISH
# =========================

def set_webhook():
    if not BOT_TOKEN:
        print("BOT_TOKEN topilmadi.")
        return

    render_url = os.environ.get("RENDER_EXTERNAL_URL")

    if not render_url:
        print("RENDER_EXTERNAL_URL topilmadi.")
        return

    webhook_url = f"{render_url}/webhook"

    try:
        r = requests.post(
            f"{TELEGRAM_API}/setWebhook",
            json={"url": webhook_url},
            timeout=30
        )

        print("Webhook:", r.status_code, r.text)

    except Exception as e:
        print("Webhook xatosi:", repr(e))


# =========================
# ISHGA TUSHIRISH
# =========================

if __name__ == "__main__":
    set_webhook()

    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
