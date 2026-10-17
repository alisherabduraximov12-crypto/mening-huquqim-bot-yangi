    import os
import logging
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("mening-huquqim")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

TELEGRAM_API = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
    if BOT_TOKEN else ""
)
OPENAI_URL = "https://api.openai.com/v1/responses"

CONTACT_TEXT = (
    "📞 Raqobat qo‘mitasi Call-markazi: 1159\n"
    "✉️ Elektron pochta: info@raqobat.gov.uz\n"
    "📍 Manzil: 100128, Toshkent shahri, Labzak ko‘chasi, 3-uy\n"
    "🌐 Sayt: https://raqobat.gov.uz/bog-lanish/\n\n"
    "Eslatma: bot orqali olingan javob rasmiy murojaat "
    "ro‘yxatdan o‘tganini anglatmaydi."
)

LAW_LINKS = (
    "📚 Rasmiy manbalar:\n"
    "• LexUZ: https://lex.uz/\n"
    "• Chakana savdo qoidalari: https://lex.uz/acts/-243235\n"
    "• Raqobat qo‘mitasi: "
    "https://raqobat.gov.uz/bog-lanish/\n\n"
    "Qonunchilikning amaldagi tahririni rasmiy manbadan tekshiring."
)

KEYBOARD = {
    "keyboard": [
        [
            {"text": "🛒 Muammom bor"},
            {"text": "📝 Ariza tayyorlash"}
        ],
        [
            {"text": "📚 Huquqlarim haqida"},
            {"text": "📄 Kerakli hujjatlar"}
        ],
        [
            {"text": "📞 Aloqa"},
            {"text": "🔄 Qayta boshlash"}
        ]
    ],
    "resize_keyboard": True,
    "is_persistent": True
}

SYSTEM_INSTRUCTIONS = """
Siz Mening Huquqim nomli iste'molchi yordamchi botsiz.
O'zbek tilida, lotin yozuvida, sodda va hurmat bilan javob bering.

Asosiy yo'nalishlar:
- Iste'molchilarning huquqlarini himoya qilish to'g'risidagi qonun;
- chakana savdo qoidalari, jumladan VMning 75-son qarori;
- vaziyatga tegishli boshqa qonunchilik.

QAT'IY QOIDALAR:
1. Qonun moddasi, muddat, jarima yoki bandni bilmasangiz,
   raqamlarni taxmin qilmang.
2. Foydalanuvchi aytmagan faktlarni o'ylab topmang.
3. Yetarli dalil bo'lmasa, dastlabki baho bering.
4. Qo'mita vakolatidan tashqaridagi masalani Qo'mita
   hal qilib beradi deb va'da bermang.
5. Zaruratda sud, ekspertiza yoki boshqa vakolatli
   organga murojaat qilishni tushuntiring.
6. Javob rasmiy qaror yoki sud xulosasi o'rnini bosmaydi.
7. Parol, SMS-kod yoki bank karta ma'lumotlarini so'ramang.
8. Tovar xavfli bo'lishi mumkin bo'lsa, undan foydalanishni
   to'xtatish va mutaxassisga murojaat qilishni tavsiya qiling.
9. Qonunni tekshirmagan bo'lsangiz, tekshirdim demang.
10. Amaliy tavsiyalar va kerakli dalillarni ko'rsating.

Javobda vaziyatga mos ravishda:
- Dastlabki baho;
- Huquqiy yo'nalish;
- Kerakli hujjatlar;
- Keyingi qadamlar;
- Murojaat qilinadigan joyni tushuntiring.

Bot javobi rasmiy murojaat ro'yxatdan o'tganini anglatmaydi.
"""

# Foydalanuvchilarning vaqtinchalik suhbat ma'lumotlari
sessions = {}
seen_update_ids = set()


def telegram_call(method, payload):
    if not TELEGRAM_API:
        log.error("BOT_TOKEN sozlanmagan.")
        return None

    try:
        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload,
            timeout=(5, 20)
        )

        if not response.ok:
            log.error(
                "Telegram API xatosi: %s",
                response.status_code
            )
            return None

        result = response.json()

        if not result.get("ok"):
            log.error("Telegram so'rovi bajarilmadi.")
            return None

        return result.get("result")

    except requests.RequestException as exc:
        log.error(
            "Telegram ulanish xatosi: %s",
            type(exc).__name__
        )
        return None


def send_message(chat_id, text, show_keyboard=True):
    if not text:
        text = "Javob tayyorlanmadi. Qayta urinib ko'ring."

    # Telegram xabar uzunligi chegarasidan oshmaslik
    text = str(text)
    chunks = []

    while len(text) > 3900:
        split_at = text.rfind("\n", 0, 3900)

        if split_at < 500:
            split_at = 3900

        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()

    if text:
        chunks.append(text)

    for index, chunk in enumerate(chunks):
        payload = {
            "chat_id": chat_id,
            "text": chunk
        }

        if show_keyboard and index == len(chunks) - 1:
            payload["reply_markup"] = KEYBOARD

        telegram_call("sendMessage", payload)


def get_session(chat_id):
    key = str(chat_id)

    if key not in sessions:
        sessions[key] = {
            "mode": None,
            "step": None,
            "data": {}
        }

    return sessions[key]


def reset_session(chat_id):
    sessions[str(chat_id)] = {
        "mode": None,
        "step": None,
        "data": {}
    }


def call_openai(user_input):
    if not OPENAI_API_KEY:
        log.error("OPENAI_API_KEY sozlanmagan.")
        return None

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENAI_MODEL,
        "instructions": SYSTEM_INSTRUCTIONS,
        "input": user_input,
        "max_output_tokens": 1200
    }

    try:
        log.info("OpenAI so'rovi boshlandi. Model=%s", OPENAI_MODEL)

        response = requests.post(
            OPENAI_URL,
            headers=headers,
            json=payload,
            timeout=(10, 75)
        )

        if not response.ok:
            log.error(
                "OpenAI HTTP xatosi: status=%s, javob=%s",
                response.status_code,
                response.text[:300].replace(OPENAI_API_KEY, "[HIDDEN]")
            )
            return None

        result = response.json()
        parts = []

        for item in result.get("output", []):
            if item.get("type") != "message":
                continue

            for content in item.get("content", []):
                if (
                    content.get("type") == "output_text"
                    and content.get("text")
                ):
                    parts.append(content["text"])

        answer = "\n".join(parts).strip()

        if not answer:
            log.error("OpenAI javobida matn topilmadi.")
            return None

        return answer

    except requests.Timeout:
        log.error("OpenAI so'rovi vaqti tugadi.")

    except requests.ConnectionError:
        log.error("OpenAI serveriga ulanish amalga oshmadi.")

    except requests.RequestException as exc:
        log.error(
            "OpenAI tarmoq xatosi: %s",
            type(exc).__name__
        )

    except (ValueError, TypeError):
        log.error("OpenAI javobini o'qishda xato.")

    return None
    def analyze_consumer_problem(data):
    prompt = f"""
Quyidagi iste'molchi murojaatini dastlabki tahlil qiling.

Tovar yoki xizmat: {data.get('product', 'Ko‘rsatilmagan')}
Sotib olingan sana: {data.get('date', 'Ko‘rsatilmagan')}
Muammo: {data.get('problem', 'Ko‘rsatilmagan')}
Sotuvchi javobi: {data.get('seller', 'Ko‘rsatilmagan')}
Hujjatlar va dalillar: {data.get('evidence', 'Ko‘rsatilmagan')}

O'zbek lotin yozuvida javob bering.

Quyidagilarni tushuntiring:
1. Dastlabki baho.
2. Tegishli huquqiy yo'nalish.
3. Yetishmayotgan hujjat va dalillar.
4. Iste'molchining keyingi qadamlari.
5. Qayerga murojaat qilishi mumkinligi.

Qonun moddalari yoki muddatlarini taxmin qilmang.
Qo'mita vakolatidan tashqaridagi masalani ajrating.
Bu dastlabki ma'lumot ekanini eslating.
"""
    return call_openai(prompt)


def draft_consumer_application(data):
    prompt = f"""
Quyidagi ma'lumotlar asosida o'zbek lotin yozuvida
rasmiy ariza loyihasini tayyorlang.

Ariza kimga: {data.get('recipient', 'Ko‘rsatilmagan')}
Muammo: {data.get('problem', 'Ko‘rsatilmagan')}
Iste'molchining talabi: {data.get('request', 'Ko‘rsatilmagan')}
Dalillar: {data.get('evidence', 'Ko‘rsatilmagan')}

Talablar:
- Yetishmayotgan ma'lumotlarni [to'ldiriladi] deb yozing.
- Ism, manzil, sana yoki qonun moddasini o'ylab topmang.
- Rasmiy, xolis va tushunarli uslubdan foydalaning.
- Ariza oxirida ilovalar, sana va imzo uchun joy qoldiring.
- Bu ariza loyihasi ekanini eslating.
"""
    return call_openai(prompt)


def start_problem(chat_id):
    reset_session(chat_id)
    session = get_session(chat_id)

    session["mode"] = "problem"
    session["step"] = "product"

    send_message(
        chat_id,
        "🛒 Muammo bo'yicha dastlabki tahlilni boshlaymiz.\n\n"
        "1/5. Qaysi tovar yoki xizmat bo'yicha muammo yuz berdi?"
    )


def start_application(chat_id):
    reset_session(chat_id)
    session = get_session(chat_id)

    session["mode"] = "application"
    session["step"] = "recipient"

    send_message(
        chat_id,
        "📝 Ariza loyihasini tayyorlaymiz.\n\n"
        "1/4. Ariza kimga yuboriladi? Sotuvchi yoki tashkilot "
        "nomini yozing. Bilmasangiz, “bilmayman” deb yozing."
    )


def process_problem_step(chat_id, text, session):
    step = session["step"]
    data = session["data"]

    prompts = {
        "product": (
            "product",
            "2/5. Tovar qachon sotib olingan? Sanani yozing."
        ),
        "date": (
            "date",
            "3/5. Muammo nimada? Nima sodir bo'lganini tushuntiring."
        ),
        "problem": (
            "problem",
            "4/5. Sotuvchiga murojaat qildingizmi? U qanday javob berdi?"
        ),
        "seller": (
            "seller",
            "5/5. Qanday hujjat yoki dalillaringiz bor? "
            "Masalan, chek, shartnoma, foto yoki yozishma. "
            "Bo'lmasa, “yo'q” deb yozing."
        ),
        "evidence": (
            "evidence",
            None
        )
    }

    if step not in prompts:
        reset_session(chat_id)
        send_message(chat_id, "Suhbatda xatolik yuz berdi. Qaytadan boshlang.")
        return

    key, next_prompt = prompts[step]
    data[key] = text[:3000]

    if step == "seller":
        session["step"] = "evidence"
        send_message(chat_id, next_prompt, show_keyboard=False)
        return

    if step != "evidence":
        session["step"] = {
            "product": "date",
            "date": "problem",
            "problem": "seller"
        }[step]

        send_message(chat_id, next_prompt, show_keyboard=False)
        return

    send_message(
        chat_id,
        "⏳ Murojaatingiz AI yordamida tahlil qilinmoqda...",
        show_keyboard=False
    )

    answer = analyze_consumer_problem(data)

    if answer:
        send_message(
            chat_id,
            "🔎 DASTLABKI TAHLIL\n\n" + answer
        )
    else:
        send_message(
            chat_id,
            "⚠️ Hozir AI tahlilini olishning imkoni bo'lmadi.\n\n"
            "Birozdan keyin qayta urinib ko'ring. "
            "Xato davom etsa, bot administratori Render jurnalini tekshirishi kerak.\n\n"
            + LAW_LINKS
        )

    reset_session(chat_id)


def process_application_step(chat_id, text, session):
    step = session["step"]
    data = session["data"]

    if step == "recipient":
        data["recipient"] = text[:2000]
        session["step"] = "problem"

        send_message(
            chat_id,
            "2/4. Muammo qanday yuz berdi? Batafsil yozing.",
            show_keyboard=False
        )

    elif step == "problem":
        data["problem"] = text[:3000]
        session["step"] = "request"

        send_message(
            chat_id,
            "3/4. Tashkilotdan nimani talab qilmoqchisiz? "
            "Masalan, pulni qaytarish yoki tovarni almashtirish.",
            show_keyboard=False
        )

    elif step == "request":
        data["request"] = text[:2000]
        session["step"] = "evidence"

        send_message(
            chat_id,
            "4/4. Qanday hujjatlaringiz bor? Chek, shartnoma, "
            "kafolat taloni yoki yozishmalar. Bo'lmasa, “yo'q” deb yozing.",
            show_keyboard=False
        )

    elif step == "evidence":
        data["evidence"] = text[:3000]

        send_message(
            chat_id,
            "⏳ Ariza loyihasi tayyorlanmoqda...",
            show_keyboard=False
        )

        answer = draft_consumer_application(data)

        if answer:
            send_message(
                chat_id,
                "📝 ARIZA LOYIHASI\n\n"
                + answer
                + "\n\n⚠️ Yuborishdan oldin ma'lumotlarni tekshiring "
                "va [to'ldiriladi] joylarini to'ldiring."
            )
        else:
            send_message(
                chat_id,
                "⚠️ Hozir ariza loyihasini tayyorlab bo'lmadi. "
                "Birozdan keyin qayta urinib ko'ring.\n\n"
                + LAW_LINKS
            )

        reset_session(chat_id)
        def handle_message(message):
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return

    text = (message.get("text") or "").strip()

    if not text:
        send_message(
            chat_id,
            "Iltimos, hozircha muammo haqida matn ko'rinishida yozing."
        )
        return

    command = text.split()[0].split("@")[0].lower()

    if command in ("/start", "/help"):
        reset_session(chat_id)

        send_message(
            chat_id,
            "Assalomu alaykum! 👋\n\n"
            "Siz “Mening Huquqim” iste'molchi yordamchi botidasiz.\n\n"
            "🛒 Muammo bo'yicha dastlabki tahlil olish;\n"
            "📝 Ariza loyihasini tayyorlash;\n"
            "📚 Iste'molchi huquqlari haqida ma'lumot olish mumkin.\n\n"
            "Bot javobi rasmiy murojaat ro'yxatdan o'tganini anglatmaydi."
        )
        return

    if command == "/muammo" or text == "🛒 Muammom bor":
        start_problem(chat_id)
        return

    if command == "/ariza" or text == "📝 Ariza tayyorlash":
        start_application(chat_id)
        return

    if command == "/aloqa" or text == "📞 Aloqa":
        reset_session(chat_id)
        send_message(chat_id, CONTACT_TEXT)
        return

    if command == "/huquqim" or text == "📚 Huquqlarim haqida":
        reset_session(chat_id)

        send_message(
            chat_id,
            "📚 Iste'molchi huquqlari haqida\n\n"
            "Iste'molchi tovar va xizmatlar haqida to'g'ri ma'lumot "
            "olish, tegishli sifat va xavfsizlik talablariga rioya "
            "etilishini kutish hamda qonunda belgilangan hollarda "
            "o'z talablarini bildirish huquqiga ega.\n\n"
            "Aniq huquq va talab vaziyatga bog'liq.\n\n"
            + LAW_LINKS
        )
        return

    if command == "/hujjatlar" or text == "📄 Kerakli hujjatlar":
        reset_session(chat_id)

        send_message(
            chat_id,
            "📄 Odatda kerak bo'ladigan dalillar:\n\n"
            "• xarid cheki yoki to'lov hujjati;\n"
            "• shartnoma yoki kafolat taloni;\n"
            "• sotuvchi bilan yozishmalar;\n"
            "• muammoni ko'rsatuvchi foto yoki video;\n"
            "• sotuvchiga yuborilgan murojaat va javob;\n"
            "• mavjud bo'lsa, servis yoki ekspertiza xulosasi.\n\n"
            "Aniq hujjatlar ro'yxati muammoga bog'liq. "
            "Asl hujjatlarni saqlab qo'ying."
        )
        return

    if command == "/qayta" or text == "🔄 Qayta boshlash":
        reset_session(chat_id)
        send_message(chat_id, "Suhbat qayta boshlandi. Menyudan bo'limni tanlang.")
        return

    session = get_session(chat_id)

    if session["mode"] == "problem":
        process_problem_step(chat_id, text, session)

    elif session["mode"] == "application":
        process_application_step(chat_id, text, session)

    else:
        send_message(
            chat_id,
            "Kerakli bo'limni menyudan tanlang yoki /start buyrug'ini yuboring."
        )


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "service": "Mening Huquqim",
        "status": "ok",
        "telegram_configured": bool(BOT_TOKEN),
        "openai_configured": bool(OPENAI_API_KEY)
    }), 200


@app.route("/webhook", methods=["POST"])
def webhook():
    if WEBHOOK_SECRET:
        provided_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )

        if provided_secret != WEBHOOK_SECRET:
            return jsonify({"ok": False}), 401

    update = request.get_json(silent=True)

    if not isinstance(update, dict):
        return jsonify({"ok": True}), 200

    update_id = update.get("update_id")

    if update_id is not None:
        if update_id in seen_update_ids:
            return jsonify({"ok": True}), 200

        seen_update_ids.add(update_id)

        if len(seen_update_ids) > 3000:
            for old_id in sorted(seen_update_ids)[:1000]:
                seen_update_ids.discard(old_id)

    message = update.get("message") or update.get("edited_message")

    if message:
        try:
            handle_message(message)
        except Exception:
            log.exception("Xabarni qayta ishlashda xato yuz berdi.")

    return jsonify({"ok": True}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
