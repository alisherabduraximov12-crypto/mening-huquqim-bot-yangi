import os
import logging
import time
import requests
from flask import Flask, request, jsonify

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

sessions = {}
seen_update_ids = set()
MAX_SEEN_UPDATES = 3000

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

STEP_ORDER = [
    "product",
    "purchase_date",
    "problem",
    "seller",
    "evidence",
]

STEP_PROMPTS = {
    "product": "Qaysi mahsulot yoki xizmat bo‘yicha muammo yuz berdi?",
    "purchase_date": (
        "Qachon xarid qilgansiz yoki xizmatdan foydalangansiz? "
        "Taxminiy sanani ham yozishingiz mumkin."
    ),
    "problem": "Muammo nimada? Nima sodir bo‘lganini batafsil yozing.",
    "seller": (
        "Sotuvchi yoki xizmat ko‘rsatuvchi tashkilot nomini yozing. "
        "Bilmasangiz, «bilmayman» deb yozing."
    ),
    "evidence": (
        "Qanday dalillaringiz bor? Masalan, chek, shartnoma, "
        "kafolat taloni, foto, video yoki yozishma. "
        "Bo‘lmasa, «yo‘q» deb yozing."
    ),
}


def telegram_call(method, payload):
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN sozlanmagan")
        return None

    try:
        response = requests.post(
            f"{TELEGRAM_API}/{method}",
            json=payload,
            timeout=35,
        )
        response.raise_for_status()
        result = response.json()

        if not result.get("ok"):
            logger.error(
                "Telegram API xatosi: %s",
                result.get("description", "Noma'lum xato"),
            )

        return result

    except requests.RequestException:
        logger.exception("Telegram bilan bog‘lanishda xato")
        return None


def send_message(chat_id, text, reply_markup=None):
    text = str(text).strip() or "Kechirasiz, javob tayyorlanmadi."

    # Telegram xabar uzunligi chegarasidan ehtiyot bo‘lamiz.
    text = text[:4000]

    payload = {
        "chat_id": chat_id,
        "text": text,
    }

    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    return telegram_call("sendMessage", payload)


def reset_session(chat_id):
    sessions.pop(str(chat_id), None)


def set_session(chat_id, flow, step="product", data=None):
    sessions[str(chat_id)] = {
        "flow": flow,
        "step": step,
        "data": data or {},
        "updated_at": time.time(),
    }


def get_session(chat_id):
    return sessions.get(str(chat_id))


def start_text():
    return (
        "Assalomu alaykum! Men — «Mening Huquqim» yordamchi botiman.\n\n"
        "Iste’molchi muammosini tushunish, kerakli ma’lumotlarni yig‘ish "
        "va murojaat loyihasini tayyorlashga yordam beraman.\n\n"
        "Javoblar dastlabki yo‘l-yo‘riq hisoblanadi, rasmiy qaror, "
        "ekspert xulosasi yoki sud qarori emas.\n\n"
        "Quyidagi menyudan bo‘limni tanlang."
    )


def call_openai(prompt):
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY sozlanmagan")
        return None

    try:
        response = requests.post(
            OPENAI_API,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "input": prompt,
                "max_output_tokens": 1400,
            },
            timeout=70,
        )

        if not response.ok:
            logger.error(
                "OpenAI API xatosi: HTTP %s; %s",
                response.status_code,
                response.text[:1000],
            )
            return None

        result = response.json()

        # Responses API qaytargan matnni olish.
        for item in result.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    answer = content.get("text", "").strip()
                    if answer:
                        return answer

        logger.error("OpenAI javobida matn topilmadi")
        return None

    except requests.RequestException:
        logger.exception("OpenAI API bilan bog‘lanishda xato")
        return None
    except (ValueError, TypeError, KeyError):
        logger.exception("OpenAI javobini o‘qishda xato")
        return None


def start_intake(chat_id, flow):
    reset_session(chat_id)
    set_session(chat_id, flow)
    send_message(
        chat_id,
        "Ma’lumotlarni navbat bilan yuboring.\n"
        "Istalgan vaqtda «Bekor» deb yozib, menyuga qaytishingiz mumkin.\n\n"
        + STEP_PROMPTS["product"],
        MAIN_KEYBOARD,
    )


def build_prompt(flow, data):
    details = (
        f"Mahsulot yoki xizmat: {data.get('product', '')}\n"
        f"Xarid sanasi: {data.get('purchase_date', '')}\n"
        f"Muammo tafsilotlari: {data.get('problem', '')}\n"
        f"Sotuvchi yoki tashkilot: {data.get('seller', '')}\n"
        f"Mavjud dalillar: {data.get('evidence', '')}\n"
    )

    instructions = (
        "Siz O‘zbekiston iste’molchilariga dastlabki yo‘l-yo‘riq "
        "beruvchi «Mening Huquqim» yordamchi botisiz. O‘zbek tilida "
        "aniq va sodda javob bering.\n\n"
        "Faqat amaldagi qonunchilikka muvofiq, ehtiyotkor tavsiyalar "
        "bering. Qonun moddalarini ishonchli bilmasangiz, raqamlarini "
        "o‘ylab topmang. Dalillar yetarli bo‘lmasa, buni ochiq ayting. "
        "Qo‘mita vakolatiga kirmaydigan masalani tegishli vakolatli "
        "organga yo‘naltirish kerakligini tushuntiring. Sud, ekspertiza "
        "yoki rasmiy organning o‘rniga yakuniy qaror chiqarmang. "
        "Foydalanuvchiga asl hujjatlarni saqlash va dalillar nusxasini "
        "tayyorlashni tavsiya qiling. Shaxsiy ma’lumotlarni ortiqcha "
        "so‘ramang.\n\n"
    )

    if flow == "application":
        task = (
            "Quyidagi ma’lumotlar asosida sotuvchi yoki xizmat "
            "ko‘rsatuvchi tashkilotga berish uchun ariza loyihasini "
            "tuzing. Tashkilot nomi, sana yoki boshqa zarur ma’lumot "
            "noma’lum bo‘lsa, to‘ldiriladigan joy qoldiring. "
            "Talabni vaziyatga mos, qonuniy va aniq shakllantiring. "
            "Oxirida ilova qilinishi mumkin bo‘lgan hujjatlarni sanang. "
            "Ariza loyihasi avtomatik ravishda rasmiy yuborilmasligini "
            "eslatib o‘ting."
        )
    else:
        task = (
            "Iste’molchi muammosini dastlabki tahlil qiling. Javobni "
            "quyidagi tartibda bering: 1) vaziyat qisqacha; "
            "2) aniqlashtirilishi kerak bo‘lgan jihatlar; "
            "3) iste’molchining ehtimoliy huquqlari; "
            "4) amaliy keyingi qadamlar; 5) kerakli dalillar va "
            "hujjatlar; 6) masala boshqa organga yoki sudga tegishli "
            "bo‘lishi mumkinmi. Asossiz xulosa chiqarmang."
        )

    return (
        instructions
        + task
        + "\n\nFoydalanuvchi taqdim etgan ma’lumotlar:\n"
        + details
        + "\nBu ma’lumotlarni tekshirilgan fakt sifatida emas, "
        "foydalanuvchi bergan ma’lumot sifatida baholang."
    )


def process_intake_step(chat_id, text, session):
    step = session.get("step")
    data = session.get("data", {})
    flow = session.get("flow", "problem")

    if step not in STEP_ORDER:
        reset_session(chat_id)
        send_message(
            chat_id,
            "Suhbat holatida xato yuz berdi. Iltimos, qaytadan boshlang.",
            MAIN_KEYBOARD,
        )
        return

    data[step] = text.strip()
    current_index = STEP_ORDER.index(step)

    if current_index < len(STEP_ORDER) - 1:
        next_step = STEP_ORDER[current_index + 1]
        set_session(chat_id, flow, next_step, data)
        send_message(chat_id, STEP_PROMPTS[next_step], MAIN_KEYBOARD)
        return

    # Barcha javoblar yig‘ildi.
    reset_session(chat_id)
    send_message(
        chat_id,
        "Ma’lumotlaringiz qabul qilindi. Dastlabki javob tayyorlanmoqda...",
        MAIN_KEYBOARD,
    )

    answer = call_openai(build_prompt(flow, data))

    if not answer:
        answer = (
            "Kechirasiz, hozir AI xizmatiga ulanishda xatolik yuz berdi.\n\n"
            "Ma’lumotlaringiz ushbu botning vaqtinchalik suhbat xotirasida "
            "saqlangan bo‘lishi mumkin, ammo bu xotira doimiy emas. "
            "Birozdan so‘ng qayta urinib ko‘ring. Muhim ma’lumotlaringizni "
            "o‘zingizda ham saqlang."
        )

    send_message(chat_id, answer, MAIN_KEYBOARD)


def handle_message(message):
    chat_id = (message.get("chat") or {}).get("id")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return

    if not text:
        send_message(
            chat_id,
            "Iltimos, matnli xabar yuboring yoki menyudan bo‘lim tanlang.",
            MAIN_KEYBOARD,
        )
        return

    lowered = text.casefold()

    if lowered in CANCEL_WORDS:
        reset_session(chat_id)
        send_message(
            chat_id,
            "Joriy amal bekor qilindi. Menyudan bo‘lim tanlang.",
            MAIN_KEYBOARD,
        )
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
            "Murojaat turiga qarab quyidagi hujjatlar foydali bo‘lishi "
            "mumkin:\n"
            "• xarid cheki yoki to‘lov hujjati;\n"
            "• shartnoma, buyurtma yoki kafolat taloni;\n"
            "• foto, video yoki yozishmalar;\n"
            "• sotuvchiga yuborilgan murojaat va javob;\n"
            "• mavjud bo‘lsa, servis yoki ekspertiza xulosasi.\n\n"
            "Asl hujjatlarni o‘zingizda saqlang. Faqat mavjud "
            "hujjatlarni ilova qiling.",
            MAIN_KEYBOARD,
        )
        return

    if text == "⚖️ Huquqlarim haqida" or lowered == "/huquqim":
        send_message(
            chat_id,
            "Iste’molchi qonunchilikda belgilangan huquqlarga ega, "
            "jumladan tovar yoki xizmat haqida zarur ma’lumot olish "
            "va huquqlari buzilganda qonuniy tartibda murojaat qilish.\n\n"
            "Aniq talab vaziyatga va amaldagi qonunchilikka bog‘liq. "
            "Muammoingizni «🛒 Mahsulot muammosi» bo‘limida yozing. "
            "Bot javobi dastlabki ma’lumotdir.",
            MAIN_KEYBOARD,
        )
        return

    if text == "☎️ Mutaxassis bilan aloqa" or lowered == "/aloqa":
        send_message(
            chat_id,
            "Mutaxassis bilan aloqa:\n"
            "• Telegram: @Qul_Umidi\n"
            "• Qo‘mita qisqa raqami: 1159\n\n"
            "Rasmiy aloqa ma’lumotlarini foydalanishdan oldin tekshiring.",
            MAIN_KEYBOARD,
        )
        return

    session = get_session(chat_id)
    if session:
        process_intake_step(chat_id, text, session)
        return

    send_message(
        chat_id,
        "Menyudan bo‘lim tanlang yoki /start buyrug‘ini yuboring.",
        MAIN_KEYBOARD,
    )


@app.get("/")
def index():
    return jsonify({
        "service": "Mening Huquqim Telegram bot",
        "status": "running",
    }), 200


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.post("/webhook")
def webhook():
    if WEBHOOK_SECRET:
        provided_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token", ""
        )
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
        logger.exception("Telegram yangilanishini qayta ishlashda xato")
        return jsonify({"ok": True}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
