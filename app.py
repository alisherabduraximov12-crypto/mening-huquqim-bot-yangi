import os
import requests
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)

# =========================================================
# SOZLAMALAR
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Kerak bo'lsa Render Environment Variables orqali o'zgartirish mumkin
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-6-luna")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

WEBHOOK_URL = (
    "https://mening-huquqim-bot-yangi.onrender.com/webhook"
)

# OpenAI client
openai_client = None

if OPENAI_API_KEY:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print("OpenAI client xatosi:", e)


# =========================================================
# FOYDALANUVCHILAR HOLATI
# =========================================================

USERS = {}


def new_user():
    return {
        "step": "main",

        "product": "",
        "purchase_date": "",
        "problem": "",

        "seller_contacted": "",
        "seller_response": "",

        "service_contacted": "",
        "service_response": "",

        "receipt": "",
        "warranty": "",

        "installment": "",
        "contract_file_id": "",

        "evidence_files": [],

        "case_finished": False,
    }


def get_user(chat_id):
    if chat_id not in USERS:
        USERS[chat_id] = new_user()

    return USERS[chat_id]


def reset_user(chat_id):
    USERS[chat_id] = new_user()
    return USERS[chat_id]


# =========================================================
# TELEGRAM FUNKSIYALARI
# =========================================================

def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text,
    }

    if keyboard:
        data["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True,
        }

    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=data,
            timeout=20,
        )

        print("Telegram:", response.text)

        return response.json()

    except Exception as e:
        print("send_message xatosi:", e)
        return None


def send_long_message(chat_id, text, keyboard=None):
    """
    Telegram xabar uzunligi chegarasidan oshmasligi uchun
    uzun AI javoblarini bo'lib yuboradi.
    """

    max_length = 3800

    if len(text) <= max_length:
        return send_message(chat_id, text, keyboard)

    parts = []

    while len(text) > max_length:
        split_at = text.rfind("\n", 0, max_length)

        if split_at < 1000:
            split_at = max_length

        parts.append(text[:split_at])
        text = text[split_at:].lstrip()

    if text:
        parts.append(text)

    for index, part in enumerate(parts):
        if index == len(parts) - 1:
            send_message(chat_id, part, keyboard)
        else:
            send_message(chat_id, part)

    return None


def answer_callback(callback_query_id, text=""):
    try:
        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={
                "callback_query_id": callback_query_id,
                "text": text,
            },
            timeout=10,
        )
    except Exception as e:
        print("callback xatosi:", e)


# =========================================================
# KLAVIATURALAR
# =========================================================

def main_keyboard():
    return [
        ["🛒 Mahsulot muammosi"],
        ["💰 Pulni qaytarish", "🛠 Kafolat"],
        ["📎 Kerakli hujjatlar", "⚖️ Huquqlarim"],
        ["📞 Aloqa"],
        ["💼 Qo‘shimcha xizmatlar"],
    ]


def yes_no_keyboard():
    return [
        ["✅ Ha", "❌ Yo‘q"],
        ["⬅️ Orqaga"],
    ]


def back_keyboard():
    return [
        ["⬅️ Orqaga"],
        ["🏠 Bosh menyu"],
    ]


def skip_keyboard():
    return [
        ["⏭ O‘tkazib yuborish"],
        ["⬅️ Orqaga"],
    ]


def evidence_keyboard():
    return [
        ["⏭ O‘tkazib yuborish"],
        ["⬅️ Orqaga"],
    ]


def paid_keyboard():
    return [
        ["📝 Ariza tayyorlash"],
        ["📑 Hujjat tahlili"],
        ["🧭 Individual yo‘l xaritasi"],
        ["📄 Shartnoma tekshiruvi"],
        ["📂 Murojaat paketi"],
        ["👨‍💼 Mutaxassis bilan aloqa"],
        ["⬅️ Orqaga"],
    ]


# =========================================================
# START
# =========================================================

def start_bot(chat_id):
    reset_user(chat_id)

    text = (
        "👋 Assalomu alaykum!\n\n"
        "Siz «Mening Huquqim» botidasiz.\n\n"
        "Bu bot iste’molchi muammosini tushunish, "
        "zarur ma’lumot va dalillarni yig‘ish hamda "
        "dastlabki huquqiy yo‘l-yo‘riq berishga yordam beradi.\n\n"
        "⚠️ Bot yakuniy sud yoki ekspert xulosasini bermaydi. "
        "AI tahlili taqdim etilgan ma’lumotlarga asoslangan "
        "dastlabki yo‘l-yo‘riq hisoblanadi.\n\n"
        "Kerakli bo‘limni tanlang:"
    )

    send_message(chat_id, text, main_keyboard())


# =========================================================
# MAHSULOT MUAMMOSI
# =========================================================

def start_product_case(chat_id):
    user = reset_user(chat_id)

    user["step"] = "product"

    send_message(
        chat_id,
        "🛒 Mahsulot muammosi\n\n"
        "Avvalo, qanday mahsulot sotib olganingizni yozing.\n\n"
        "Masalan: muzlatkich, televizor, telefon, "
        "kir yuvish mashinasi va hokazo.",
        back_keyboard(),
    )


def show_product_step(chat_id):
    user = get_user(chat_id)
    step = user["step"]

    if step == "product":
        send_message(
            chat_id,
            "🛒 Qanday mahsulot sotib oldingiz?",
            back_keyboard(),
        )

    elif step == "purchase_date":
        send_message(
            chat_id,
            "📅 Mahsulotni qachon sotib oldingiz?",
            back_keyboard(),
        )

    elif step == "problem":
        send_message(
            chat_id,
            "⚠️ Mahsulotda qanday muammo yoki nuqson yuzaga keldi?",
            back_keyboard(),
        )

    elif step == "seller_contacted":
        send_message(
            chat_id,
            "🏪 Savdo tashkiloti yoki sotuvchiga murojaat qildingizmi?",
            yes_no_keyboard(),
        )

    elif step == "seller_response":
        send_message(
            chat_id,
            "🏪 Sotuvchi sizga qanday javob berdi?\n\n"
            "Javobni imkon qadar batafsil yozing.",
            back_keyboard(),
        )

    elif step == "service_contacted":
        send_message(
            chat_id,
            "🔧 Ishlab chiqaruvchi yoki servis xizmatiga "
            "murojaat qildingizmi?",
            yes_no_keyboard(),
        )

    elif step == "service_response":
        send_message(
            chat_id,
            "🔧 Servis yoki ishlab chiqaruvchi qanday "
            "xulosa/javob berdi?",
            back_keyboard(),
        )

    elif step == "receipt":
        send_message(
            chat_id,
            "🧾 Kassa yoki tovar cheki mavjudmi?\n\n"
            "Agar boshqa xaridni tasdiqlovchi dalil bo‘lsa, "
            "keyinchalik uni ham ko‘rsatishingiz mumkin.",
            yes_no_keyboard(),
        )

    elif step == "warranty":
        send_message(
            chat_id,
            "🛠 Kafolat taloni yoki kafolat muddati "
            "ko‘rsatilgan texnik hujjat mavjudmi?",
            yes_no_keyboard(),
        )

    elif step == "installment":
        send_message(
            chat_id,
            "💳 Mahsulot muddatli to‘lov yoki kredit "
            "asosida sotib olinganmi?",
            yes_no_keyboard(),
        )

    elif step == "contract":
        send_message(
            chat_id,
            "📄 Agar muddatli to‘lov yoki kredit bo‘lsa, "
            "shartnoma nusxasini yuborishingiz mumkin.\n\n"
            "Mavjud bo‘lmasa, «O‘tkazib yuborish»ni bosing.",
            skip_keyboard(),
        )

    elif step == "evidence":
        send_message(
            chat_id,
            "📎 Qo‘shimcha dalillarni yuborishingiz mumkin.\n\n"
            "Masalan:\n"
            "• chek\n"
            "• kafolat taloni\n"
            "• servis xulosasi\n"
            "• sotuvchi javobi\n"
            "• foto/video\n"
            "• boshqa tegishli hujjatlar\n\n"
            "Mavjud bo‘lmasa, «O‘tkazib yuborish»ni bosing.",
            evidence_keyboard(),
        )


# =========================================================
# ORQAGA
# =========================================================

def go_back(chat_id):
    user = get_user(chat_id)
    step = user["step"]

    previous = {
        "product": "main",

        "purchase_date": "product",
        "problem": "purchase_date",

        "seller_contacted": "problem",
        "seller_response": "seller_contacted",

        "service_contacted": "seller_response",
        "service_response": "service_contacted",

        "receipt": "service_response",
        "warranty": "receipt",

        "installment": "warranty",
        "contract": "installment",

        "evidence": "contract",
    }

    if step not in previous:
        send_message(chat_id, "Bosh menyuga qaytdingiz.", main_keyboard())
        user["step"] = "main"
        return

    previous_step = previous[step]

    if previous_step == "main":
        user["step"] = "main"
        send_message(chat_id, "🏠 Bosh menyu", main_keyboard())
        return

    user["step"] = previous_step
    show_product_step(chat_id)


# =========================================================
# SAVOL JAVOBLARI
# =========================================================

def product_question(chat_id, text):
    user = get_user(chat_id)
    step = user["step"]

    # -----------------------------------------
    # MAHSULOT
    # -----------------------------------------

    if step == "product":
        user["product"] = text.strip()
        user["step"] = "purchase_date"
        show_product_step(chat_id)
        return

    # -----------------------------------------
    # SANA
    # -----------------------------------------

    if step == "purchase_date":
        user["purchase_date"] = text.strip()
        user["step"] = "problem"
        show_product_step(chat_id)
        return

    # -----------------------------------------
    # MUAMMO
    # -----------------------------------------

    if step == "problem":
        user["problem"] = text.strip()
        user["step"] = "seller_contacted"
        show_product_step(chat_id)
        return

    # -----------------------------------------
    # SOTUVCHIGA MUROJAAT
    # -----------------------------------------

    if step == "seller_contacted":

        if text == "✅ Ha":
            user["seller_contacted"] = "Ha"
            user["step"] = "seller_response"
            show_product_step(chat_id)
            return

        if text == "❌ Yo‘q":
            user["seller_contacted"] = "Yo‘q"
            user["seller_response"] = ""
            user["step"] = "service_contacted"
            show_product_step(chat_id)
            return

        send_message(
            chat_id,
            "Iltimos, «Ha» yoki «Yo‘q» tugmasini tanlang.",
            yes_no_keyboard(),
        )
        return

    # -----------------------------------------
    # SOTUVCHI JAVOBI
    # -----------------------------------------

    if step == "seller_response":
        user["seller_response"] = text.strip()
        user["step"] = "service_contacted"
        show_product_step(chat_id)
        return

    # -----------------------------------------
    # SERVISGA MUROJAAT
    # -----------------------------------------

    if step == "service_contacted":

        if text == "✅ Ha":
            user["service_contacted"] = "Ha"
            user["step"] = "service_response"
            show_product_step(chat_id)
            return

        if text == "❌ Yo‘q":
            user["service_contacted"] = "Yo‘q"
            user["service_response"] = ""
            user["step"] = "receipt"
            show_product_step(chat_id)
            return

        send_message(
            chat_id,
            "Iltimos, «Ha» yoki «Yo‘q» tugmasini tanlang.",
            yes_no_keyboard(),
        )
        return

    # -----------------------------------------
    # SERVIS JAVOBI
    # -----------------------------------------

    if step == "service_response":
        user["service_response"] = text.strip()
        user["step"] = "receipt"
        show_product_step(chat_id)
        return

    # -----------------------------------------
    # CHEK
    # -----------------------------------------

    if step == "receipt":

        if text == "✅ Ha":
            user["receipt"] = "Ha"
            user["step"] = "warranty"
            show_product_step(chat_id)
            return

        if text == "❌ Yo‘q":
            user["receipt"] = "Yo‘q"
            user["step"] = "warranty"
            show_product_step(chat_id)
            return

        send_message(
            chat_id,
            "Iltimos, «Ha» yoki «Yo‘q» tugmasini tanlang.",
            yes_no_keyboard(),
        )
        return

    # -----------------------------------------
    # KAFOLAT
    # -----------------------------------------

    if step == "warranty":

        if text == "✅ Ha":
            user["warranty"] = "Ha"
            user["step"] = "installment"
            show_product_step(chat_id)
            return

        if text == "❌ Yo‘q":
            user["warranty"] = "Yo‘q"
            user["step"] = "installment"
            show_product_step(chat_id)
            return

        send_message(
            chat_id,
            "Iltimos, «Ha» yoki «Yo‘q» tugmasini tanlang.",
            yes_no_keyboard(),
        )
        return

    # -----------------------------------------
    # MUDDATLI TO‘LOV
    # -----------------------------------------

    if step == "installment":

        if text == "✅ Ha":
            user["installment"] = "Ha"
            user["step"] = "contract"
            show_product_step(chat_id)
            return

        if text == "❌ Yo‘q":
            user["installment"] = "Yo‘q"
            user["step"] = "evidence"
            show_product_step(chat_id)
            return

        send_message(
            chat_id,
            "Iltimos, «Ha» yoki «Yo‘q» tugmasini tanlang.",
            yes_no_keyboard(),
        )
        return

    # -----------------------------------------
    # SHARTNOMA
    # -----------------------------------------

    if step == "contract":

        if text == "⏭ O‘tkazib yuborish":
            user["step"] = "evidence"
            show_product_step(chat_id)
            return

        user["step"] = "evidence"
        show_product_step(chat_id)
        return

    # -----------------------------------------
    # DALILLAR
    # -----------------------------------------

    if step == "evidence":

        if text == "⏭ O‘tkazib yuborish":
            finish_case(chat_id)
            return

        user["evidence_files"].append({
            "type": "text",
            "value": text[:1000],
        })

        finish_case(chat_id)
        return


# =========================================================
# AI TAHLILI
# =========================================================

AI_INSTRUCTIONS = """
Siz “Mening Huquqim” nomli iste’molchilar uchun amaliy
huquqiy yo‘l-yo‘riq beruvchi AI yordamchisiz.

Siz O‘zbekiston Respublikasidagi iste’molchi huquqlari
bilan bog‘liq vaziyatlarni dastlabki tahlil qilasiz.

ASOSIY QOIDALAR:

1. Faqat foydalanuvchi taqdim etgan faktlarga tayaning.

2. Faktlar yetarli bo‘lmasa, ularni o‘ylab topmang.

3. “Iste’molchi albatta haq”, “sotuvchi aniq qonunni buzgan”
   kabi qat’iy xulosalarni dalilsiz bermang.

4. Tahlilni “taqdim etilgan ma’lumotlarga ko‘ra”,
   “dastlabki baholash sifatida” kabi ehtiyotkor shaklda bering.

5. Sizga amaldagi normativ-huquqiy hujjatlarning to‘liq
   matni berilmagan bo‘lsa, aniq modda yoki band raqamini
   taxmin qilmang.

6. Aniq modda/band raqami bo‘yicha ishonch bo‘lmasa:
   “amaldagi LexUZ matni bilan tekshirish zarur”
   deb ko‘rsating.

7. Iste’molchilarning huquqlarini himoya qilish to‘g‘risidagi
   qonunchilik va chakana savdo qoidalari doirasida
   fikr yuriting.

8. Qo‘mita vakolatiga masalani avtomatik ravishda kiritmang.
   Masalan, sud, ekspertiza, jinoyat alomatlari, ayrim
   maxsus tartibga solinadigan sohalar yoki boshqa organning
   vakolatiga oid masalalar bo‘lishi mumkin.

9. Vakolat bo‘yicha:
   - “Qo‘mita vakolatiga kirishi mumkin”
   - “Qo‘mita vakolatiga kirmasligi mumkin”
   - “qo‘shimcha ma’lumot kerak”
   kabi ehtiyotkor iboralardan foydalaning.

10. Foydalanuvchiga amaliy keyingi qadamlarni aniq yozing.

11. Hujjatlar bo‘yicha “mavjud bo‘lsa” tamoyilini saqlang.
    Hujjat mavjud emasligini avtomatik ravishda huquq yo‘qolishi
    deb talqin qilmang.

12. Sudga murojaat qilish zarur bo‘lishi mumkin bo‘lgan
    holatlarda buni tushuntiring, lekin sud natijasini
    oldindan va’da qilmang.

JAVOB FORMATI:

🔎 VAZIYAT XULOSASI

⚖️ DASTLABKI HUQUQIY BAHO

📎 MUHIM DALILLAR

🏛 VAKOLAT MASALASI

➡️ KEYINGI AMALIY QADAM

⚠️ MUHIM ESLATMA

Javob tushunarli, qisqa, amaliy va o‘zbek tilida bo‘lsin.
Keraksiz murakkab yuridik iboralardan foydalanmang.
"""


def build_case_prompt(user):
    evidence_count = len(user.get("evidence_files", []))

    contract_exists = (
        "Ha"
        if user.get("contract_file_id")
        else "Yo‘q"
    )

    prompt = f"""
Quyidagi iste’molchi murojaatini dastlabki tahlil qiling.

MAHSULOT:
{user.get("product") or "Ko‘rsatilmagan"}

SOTIB OLINGAN SANA:
{user.get("purchase_date") or "Ko‘rsatilmagan"}

MUAMMO / NUQSON:
{user.get("problem") or "Ko‘rsatilmagan"}

SOTUVCHIGA MUROJAAT:
{user.get("seller_contacted") or "Ko‘rsatilmagan"}

SOTUVCHI JAVOBI:
{user.get("seller_response") or "Murojaat qilinmagan yoki javob ko‘rsatilmagan"}

SERVIS / ISHLAB CHIQARUVCHIGA MUROJAAT:
{user.get("service_contacted") or "Ko‘rsatilmagan"}

SERVIS JAVOBI:
{user.get("service_response") or "Murojaat qilinmagan yoki javob ko‘rsatilmagan"}

CHEK:
{user.get("receipt") or "Ko‘rsatilmagan"}

KAFOLAT:
{user.get("warranty") or "Ko‘rsatilmagan"}

MUDDATLI TO‘LOV / KREDIT:
{user.get("installment") or "Ko‘rsatilmagan"}

SHARTNOMA FAYLI:
{contract_exists}

QO‘SHIMCHA DALILLAR SONI:
{evidence_count}

MUHIM:
Yuklangan fayllarning mazmuni hozircha AIga uzatilmagan.
Shuning uchun faqat ularning mavjudligi haqida xulosa qiling,
fayl ichidagi ma’lumotlarni o‘ylab topmang.

Yuqoridagi faktlarga asoslanib dastlabki huquqiy
yo‘l-yo‘riq bering.
"""

    return prompt


def analyze_case_with_ai(user):
    if not openai_client:
        return None

    prompt = build_case_prompt(user)

    try:
        response = openai_client.responses.create(
            model=OPENAI_MODEL,
            instructions=AI_INSTRUCTIONS,
            input=prompt,
        )

        result = getattr(response, "output_text", None)

        if result:
            return result.strip()

        return None

    except Exception as e:
        print("OpenAI API xatosi:", repr(e))
        return None


# =========================================================
# CASE YAKUNI
# =========================================================

def fallback_case_analysis(user):
    evidence_count = len(user.get("evidence_files", []))

    text = (
        "📋 MUROJAAT BO‘YICHA DASTLABKI MA’LUMOT\n\n"
        f"🛒 Mahsulot: {user.get('product') or 'ko‘rsatilmagan'}\n"
        f"📅 Xarid sanasi: {user.get('purchase_date') or 'ko‘rsatilmagan'}\n"
        f"⚠️ Muammo: {user.get('problem') or 'ko‘rsatilmagan'}\n\n"
        f"🏪 Sotuvchiga murojaat: "
        f"{user.get('seller_contacted') or 'ko‘rsatilmagan'}\n"
        f"🔧 Servisga murojaat: "
        f"{user.get('service_contacted') or 'ko‘rsatilmagan'}\n"
        f"🧾 Chek: {user.get('receipt') or 'ko‘rsatilmagan'}\n"
        f"🛠 Kafolat: {user.get('warranty') or 'ko‘rsatilmagan'}\n"
        f"💳 Muddatli to‘lov/kredit: "
        f"{user.get('installment') or 'ko‘rsatilmagan'}\n"
        f"📎 Qo‘shimcha dalillar: {evidence_count} ta\n\n"
        "➡️ Keyingi bosqichda taqdim etilgan hujjatlar va "
        "dalillarni batafsil tekshirish hamda amaldagi "
        "qonunchilik bilan solishtirish tavsiya etiladi."
    )

    return text


def finish_case(chat_id):
    user = get_user(chat_id)

    user["step"] = "finish"
    user["case_finished"] = True

    send_message(
        chat_id,
        "🔎 Ma’lumotlaringiz qabul qilindi.\n\n"
        "🤖 Endi vaziyat bo‘yicha dastlabki AI tahlil "
        "tayyorlanmoqda..."
    )

    ai_result = analyze_case_with_ai(user)

    if ai_result:
        final_text = (
            "🤖 Mening Huquqim — dastlabki AI tahlili\n\n"
            + ai_result
            + "\n\n"
            "⚠️ Ushbu tahlil taqdim etilgan ma’lumotlarga "
            "asoslangan dastlabki yo‘l-yo‘riqdir. "
            "Yakuniy huquqiy xulosa hujjatlar, ekspertiza "
            "va amaldagi qonunchilikni to‘liq tekshirishni "
            "talab qilishi mumkin."
        )
    else:
        final_text = (
            fallback_case_analysis(user)
            + "\n\n"
            "⚠️ AI tahlili hozircha ishga tushmadi. "
            "Ma’lumotlaringiz saqlandi. Keyinchalik "
            "batafsil tahlil qilish mumkin."
        )

    send_long_message(
        chat_id,
        final_text,
        main_keyboard(),
    )


# =========================================================
# HUQUQLAR
# =========================================================

def show_rights(chat_id):
    text = (
        "⚖️ HUQUQLARINGIZ\n\n"
        "Iste’molchi sifatida mahsulot yoki xizmatdan "
        "foydalanishda qonunchilikda belgilangan "
        "huquqlaringiz mavjud.\n\n"
        "Jumladan, muammo yuzaga kelganda:\n"
        "• sotuvchiga murojaat qilish;\n"
        "• mavjud hujjat va dalillarni taqdim etish;\n"
        "• mahsulotning kafolat va sifat masalalari bo‘yicha "
        "talab qo‘yish;\n"
        "• zarur hollarda vakolatli organlarga yoki sudga "
        "murojaat qilish mumkin.\n\n"
        "⚠️ Har bir holat alohida baholanadi. "
        "Aniq huquq va talablar mahsulot turi, xarid shartlari, "
        "kafolat, nuqson va mavjud dalillarga bog‘liq."
    )

    send_message(chat_id, text, back_keyboard())


# =========================================================
# HUJJATLAR
# =========================================================

def show_documents(chat_id):
    text = (
        "📎 KERAKLI HUJJATLAR\n\n"
        "Muammoga qarab quyidagi hujjatlar foydali bo‘lishi mumkin:\n\n"
        "🧾 Kassa yoki tovar cheki — mavjud bo‘lsa\n"
        "🛠 Kafolat taloni — mavjud bo‘lsa\n"
        "📄 Shartnoma — kredit/muddatli to‘lov bo‘lsa\n"
        "🔧 Servis xulosasi — mavjud bo‘lsa\n"
        "🏪 Sotuvchining yozma javobi — mavjud bo‘lsa\n"
        "📷 Foto/video — nuqsonni tasdiqlasa\n"
        "📑 Boshqa tegishli hujjatlar\n\n"
        "Hujjat mavjud emasligi holatning barcha "
        "huquqiy jihatlari avtomatik ravishda yo‘qoladi "
        "degan ma’noni anglatmaydi."
    )

    send_message(chat_id, text, back_keyboard())


# =========================================================
# PULNI QAYTARISH
# =========================================================

def show_refund(chat_id):
    text = (
        "💰 PULNI QAYTARISH\n\n"
        "Pulni qaytarish masalasi mahsulotning holati, "
        "nuqsoni, xarid sanasi, kafolat shartlari, "
        "sotuvchi bilan muloqot va boshqa dalillarga bog‘liq.\n\n"
        "Agar mahsulot bilan muammo yuzaga kelgan bo‘lsa, "
        "avval «🛒 Mahsulot muammosi» bo‘limida "
        "holatingizni batafsil kiriting."
    )

    send_message(chat_id, text, back_keyboard())


# =========================================================
# KAFOLAT
# =========================================================

def show_warranty(chat_id):
    text = (
        "🛠 KAFOLAT\n\n"
        "Kafolat masalasi mahsulot turi, kafolat muddati, "
        "nuqsonning xususiyati va sotib olish shartlariga "
        "qarab baholanadi.\n\n"
        "Kafolat taloni yoki texnik hujjatlar mavjud bo‘lsa, "
        "ularni saqlab qo‘yish tavsiya etiladi.\n\n"
        "Muammo bo‘lsa, «🛒 Mahsulot muammosi» bo‘limi orqali "
        "batafsil ma’lumot kiriting."
    )

    send_message(chat_id, text, back_keyboard())


# =========================================================
# ALOQA
# =========================================================

def show_contact(chat_id):
    text = (
        "📞 ALOQA\n\n"
        "«Mening Huquqim» loyihasi bo‘yicha aloqa:\n\n"
        "Telegram: @Qul_Umidi\n\n"
        "⚠️ «Mening Huquqim» mustaqil axborot yordamchi "
        "loyihasi bo‘lib, davlat organining rasmiy boti "
        "sifatida qaralmaydi."
    )

    send_message(chat_id, text, back_keyboard())


# =========================================================
# QO‘SHIMCHA XIZMATLAR
# =========================================================

def show_paid_services(chat_id):
    text = (
        "💼 QO‘SHIMCHA XIZMATLAR\n\n"
        "Muammo bo‘yicha chuqurroq yordam kerak bo‘lsa, "
        "quyidagi xizmatlar mavjud:\n\n"
        "📝 Ariza tayyorlash\n"
        "📑 Hujjat tahlili\n"
        "🧭 Individual yo‘l xaritasi\n"
        "📄 Shartnoma tekshiruvi\n"
        "📂 Murojaat paketi\n"
        "👨‍💼 Mutaxassis bilan aloqa\n\n"
        "Kerakli xizmatni tanlang."
    )

    send_message(chat_id, text, paid_keyboard())


def paid_service_info(chat_id, service):
    descriptions = {
        "📝 Ariza tayyorlash": (
            "📝 ARIZA TAYYORLASH\n\n"
            "Siz taqdim etgan ma’lumotlar asosida "
            "murojaat/ariza loyihasini tayyorlashga yordam beriladi."
        ),

        "📑 Hujjat tahlili": (
            "📑 HUJJAT TAHLILI\n\n"
            "Shartnoma, javob xati yoki boshqa hujjatni "
            "mazmunan tahlil qilish va muhim jihatlarni "
            "ajratishga yordam beriladi."
        ),

        "🧭 Individual yo‘l xaritasi": (
            "🧭 INDIVIDUAL YO‘L XARITASI\n\n"
            "Muammo bo‘yicha qaysi bosqichda kimga, "
            "qanday hujjatlar bilan va qanday tartibda "
            "murojaat qilish mumkinligini tizimlashtirish."
        ),

        "📄 Shartnoma tekshiruvi": (
            "📄 SHARTNOMA TEKSHIRUVI\n\n"
            "Shartnomadagi muhim shartlar, majburiyatlar, "
            "xavfli yoki e’tibor talab qiladigan bandlarni "
            "aniqlashga yordam beriladi."
        ),

        "📂 Murojaat paketi": (
            "📂 MUROJAAT PAKETI\n\n"
            "Murojaat uchun zarur ma’lumot va hujjatlarni "
            "tizimlashtirishga yordam beriladi."
        ),

        "👨‍💼 Mutaxassis bilan aloqa": (
            "👨‍💼 MUTAXASSIS BILAN ALOQA\n\n"
            "Murakkab masalalarda mutaxassis bilan "
            "bog‘lanish imkoniyati."
        ),
    }

    text = descriptions.get(
        service,
        "Xizmat ma’lumoti topilmadi."
    )

    text += (
        "\n\n📞 Batafsil ma’lumot uchun: @Qul_Umidi"
    )

    send_message(chat_id, text, back_keyboard())


# =========================================================
# HUJJAT QABUL QILISH
# =========================================================

def handle_document(chat_id, document):
    user = get_user(chat_id)
    step = user["step"]

    file_id = document.get("file_id")

    if not file_id:
        return

    # SHARTNOMA BOSQICHI
    if step == "contract":
        user["contract_file_id"] = file_id

        send_message(
            chat_id,
            "✅ Shartnoma fayli qabul qilindi.\n\n"
            "Endi qo‘shimcha dalillar bo‘lsa yuborishingiz mumkin.",
            evidence_keyboard(),
        )

        user["step"] = "evidence"
        return

    # DALILLAR BOSQICHI
    if step == "evidence":
        user["evidence_files"].append({
            "type": "document",
            "file_id": file_id,
            "name": document.get("file_name", ""),
        })

        send_message(
            chat_id,
            "✅ Hujjat qabul qilindi.\n\n"
            "Yana hujjat/foto yuborishingiz mumkin yoki "
            "«O‘tkazib yuborish»ni bosing.",
            evidence_keyboard(),
        )
        return

    send_message(
        chat_id,
        "📎 Hozircha hujjat yuborish bosqichi emas.\n\n"
        "Kerakli bosqichga yetganimizda hujjatni qabul qilaman.",
    )


# =========================================================
# FOTO QABUL QILISH
# =========================================================

def handle_photo(chat_id, photo):
    user = get_user(chat_id)

    if user["step"] != "evidence":
        send_message(
            chat_id,
            "📷 Foto hozircha kerak emas.\n\n"
            "Dalillarni yuborish bosqichiga yetganimizda "
            "foto yuborishingiz mumkin.",
        )
        return

    if not photo:
        return

    largest_photo = photo[-1]
    file_id = largest_photo.get("file_id")

    if file_id:
        user["evidence_files"].append({
            "type": "photo",
            "file_id": file_id,
        })

    send_message(
        chat_id,
        "✅ Foto qabul qilindi.\n\n"
        "Yana dalil yuborishingiz mumkin yoki "
        "«O‘tkazib yuborish»ni bosing.",
        evidence_keyboard(),
    )


# =========================================================
# ASOSIY MATN HANDLER
# =========================================================

def handle_text(chat_id, text):
    user = get_user(chat_id)

    # -----------------------------------------
    # COMMANDS
    # -----------------------------------------

    if text.startswith("/start"):
        start_bot(chat_id)
        return

    if text == "/muammo":
        start_product_case(chat_id)
        return

    if text == "/ariza":
        paid_service_info(chat_id, "📝 Ariza tayyorlash")
        return

    if text == "/hujjatlar":
        show_documents(chat_id)
        return

    if text == "/huquqim":
        show_rights(chat_id)
        return

    if text == "/aloqa":
        show_contact(chat_id)
        return

    # -----------------------------------------
    # UNIVERSAL ORQAGA
    # -----------------------------------------

    if text == "⬅️ Orqaga":
        go_back(chat_id)
        return

    # -----------------------------------------
    # BOSH MENYU
    # -----------------------------------------

    if text == "🏠 Bosh menyu":
        user["step"] = "main"
        send_message(chat_id, "🏠 Bosh menyu", main_keyboard())
        return

    # -----------------------------------------
    # ASOSIY MENYU
    # -----------------------------------------

    if text == "🛒 Mahsulot muammosi":
        start_product_case(chat_id)
        return

    if text == "💰 Pulni qaytarish":
        show_refund(chat_id)
        return

    if text == "🛠 Kafolat":
        show_warranty(chat_id)
        return

    if text == "📎 Kerakli hujjatlar":
        show_documents(chat_id)
        return

    if text == "⚖️ Huquqlarim":
        show_rights(chat_id)
        return

    if text == "📞 Aloqa":
        show_contact(chat_id)
        return

    if text == "💼 Qo‘shimcha xizmatlar":
        show_paid_services(chat_id)
        return

    # -----------------------------------------
    # PAID SERVICES
    # -----------------------------------------

    paid_services = {
        "📝 Ariza tayyorlash",
        "📑 Hujjat tahlili",
        "🧭 Individual yo‘l xaritasi",
        "📄 Shartnoma tekshiruvi",
        "📂 Murojaat paketi",
        "👨‍💼 Mutaxassis bilan aloqa",
    }

    if text in paid_services:
        paid_service_info(chat_id, text)
        return

    # -----------------------------------------
    # O‘TKAZIB YUBORISH
    # -----------------------------------------

    if text == "⏭ O‘tkazib yuborish":

        if user["step"] == "contract":
            user["step"] = "evidence"
            show_product_step(chat_id)
            return

        if user["step"] == "evidence":
            finish_case(chat_id)
            return

        send_message(
            chat_id,
            "Bu bosqichda «O‘tkazib yuborish» ishlatilmaydi.",
        )
        return

    # -----------------------------------------
    # MAHSULOT FLOW
    # -----------------------------------------

    if user["step"] not in ["main", "finish"]:
        product_question(chat_id, text)
        return

    # -----------------------------------------
    # TUSHUNILMAGAN MATN
    # -----------------------------------------

    send_message(
        chat_id,
        "Iltimos, menyudan kerakli bo‘limni tanlang.",
        main_keyboard(),
    )


# =========================================================
# WEBHOOK
# =========================================================

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(silent=True) or {}

        print("UPDATE:", update)

        # -----------------------------------------
        # MESSAGE
        # -----------------------------------------

        message = update.get("message")

        if message:
            chat = message.get("chat", {})
            chat_id = chat.get("id")

            if not chat_id:
                return jsonify({"ok": True})

            # TEXT
            if "text" in message:
                handle_text(
                    chat_id,
                    message.get("text", "").strip(),
                )

            # DOCUMENT
            elif "document" in message:
                handle_document(
                    chat_id,
                    message.get("document", {}),
                )

            # PHOTO
            elif "photo" in message:
                handle_photo(
                    chat_id,
                    message.get("photo", []),
                )

        # -----------------------------------------
        # CALLBACK QUERY
        # -----------------------------------------

        callback_query = update.get("callback_query")

        if callback_query:
            callback_id = callback_query.get("id")
            answer_callback(callback_id)

        return jsonify({"ok": True})

    except Exception as e:
        print("WEBHOOK XATOSI:", repr(e))

        return jsonify({
            "ok": False,
            "error": str(e),
        }), 200


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/", methods=["GET"])
def home():
    return (
        "Mening Huquqim bot ishlayapti.",
        200,
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "openai": bool(openai_client),
        "model": OPENAI_MODEL,
    })


# =========================================================
# WEBHOOKNI O‘RNATISH
# =========================================================

def setup_webhook():
    if not BOT_TOKEN:
        print("BOT_TOKEN mavjud emas.")
        return

    try:
        response = requests.post(
            f"{TELEGRAM_API}/setWebhook",
            data={
                "url": WEBHOOK_URL,
            },
            timeout=20,
        )

        print("Webhook:", response.text)

    except Exception as e:
        print("Webhook setup error:", repr(e))


setup_webhook()


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port,
    )
