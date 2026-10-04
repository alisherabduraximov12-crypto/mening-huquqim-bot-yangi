import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Oddiy vaqtinchalik xotira.
# Keyinchalik ma'lumotlar bazasiga o'tkazamiz.
USERS = {}


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
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=data,
            timeout=15
        )
    except Exception as e:
        print("send_message error:", e)


def send_document(chat_id, file_id):
    try:
        requests.post(
            f"{TELEGRAM_API}/sendDocument",
            json={
                "chat_id": chat_id,
                "document": file_id
            },
            timeout=15
        )
    except Exception as e:
        print("send_document error:", e)


# =========================
# KLAVIATURALAR
# =========================

def main_keyboard():
    return {
        "keyboard": [
            [{"text": "🛒 Mahsulot muammosi"}],
            [{"text": "💰 Pulni qaytarish"}, {"text": "🛠 Kafolat"}],
            [{"text": "📎 Kerakli hujjatlar"}, {"text": "⚖️ Huquqlarim"}],
            [{"text": "📞 Aloqa"}],
            [{"text": "💼 Qo‘shimcha xizmatlar"}]
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


def skip_keyboard():
    return {
        "keyboard": [
            [{"text": "⏭ O‘tkazib yuborish"}],
            [{"text": "⬅️ Orqaga"}]
        ],
        "resize_keyboard": True
    }


def back_keyboard():
    return {
        "keyboard": [
            [{"text": "⬅️ Orqaga"}],
            [{"text": "🏠 Bosh menyu"}]
        ],
        "resize_keyboard": True
    }


def finish_keyboard():
    return {
        "keyboard": [
            [{"text": "🏁 Yakunlash"}],
            [{"text": "⬅️ Orqaga"}]
        ],
        "resize_keyboard": True
    }


def paid_services_keyboard():
    return {
        "keyboard": [
            [{"text": "📝 Ariza tayyorlash"}],
            [{"text": "📑 Hujjat tahlili"}],
            [{"text": "🧭 Individual yo‘l xaritasi"}],
            [{"text": "📄 Shartnoma tekshiruvi"}],
            [{"text": "📂 Murojaat paketi"}],
            [{"text": "👨‍💼 Mutaxassis bilan aloqa"}],
            [{"text": "⬅️ Orqaga"}]
        ],
        "resize_keyboard": True
    }


# =========================
# FOYDALANUVCHI MA'LUMOTI
# =========================

def get_user(chat_id):
    if chat_id not in USERS:
        USERS[chat_id] = {
            "section": None,
            "step": None,
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
            "contract": "",
            "evidence": "",
            "evidence_files": []
        }

    return USERS[chat_id]


def reset_user(chat_id):
    USERS[chat_id] = {
        "section": None,
        "step": None,
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
        "contract": "",
        "evidence": "",
        "evidence_files": []
    }


# =========================
# START
# =========================

def start_bot(chat_id):
    reset_user(chat_id)

    text = (
        "👋 Assalomu alaykum!\n\n"
        "🛡 Mening Huquqim botiga xush kelibsiz.\n\n"
        "Bu bot iste’molchilarga muammo bo‘yicha "
        "dastlabki amaliy huquqiy yo‘l-yo‘riq beradi.\n\n"
        "Muammoingizni bosqichma-bosqich aniqlaymiz "
        "va keyingi qonuniy qadamlarni tushuntiramiz.\n\n"
        "Quyidagi bo‘limlardan birini tanlang:"
    )

    send_message(chat_id, text, main_keyboard())


# =========================
# MAHSULOT MUAMMOSI
# =========================

def start_product_problem(chat_id):
    data = get_user(chat_id)

    data["section"] = "product"
    data["step"] = "product"

    send_message(
        chat_id,
        "🛒 Mahsulot muammosi\n\n"
        "1-savol.\n"
        "Qanday mahsulot sotib oldingiz?",
        back_keyboard()
    )


def product_question(chat_id, text):
    data = get_user(chat_id)
    step = data.get("step")

    # 1. Mahsulot
    if step == "product":
        data["product"] = text
        data["step"] = "purchase_date"

        send_message(
            chat_id,
            "📅 2-savol.\n"
            "Mahsulotni qachon sotib oldingiz?\n\n"
            "Masalan: 15.05.2026",
            back_keyboard()
        )
        return

    # 2. Xarid sanasi
    if step == "purchase_date":
        data["purchase_date"] = text
        data["step"] = "problem"

        send_message(
            chat_id,
            "📝 3-savol.\n"
            "Mahsulotda qanday muammo yoki nuqson yuzaga keldi?",
            back_keyboard()
        )
        return

    # 3. Muammo
    if step == "problem":
        data["problem"] = text
        data["step"] = "seller_contacted"

        send_message(
            chat_id,
            "🏪 4-savol.\n"
            "Savdo tashkilotiga yoki sotuvchiga murojaat qildingizmi?",
            yes_no_keyboard()
        )
        return

    # 4. Sotuvchiga murojaat
    if step == "seller_contacted":
        if text == "✅ Ha":
            data["seller_contacted"] = "ha"
            data["step"] = "seller_response"

            send_message(
                chat_id,
                "🏪 Sotuvchi nima javob berdi?\n\n"
                "Javobini imkon qadar batafsil yozing.",
                back_keyboard()
            )
            return

        if text == "❌ Yo‘q":
            data["seller_contacted"] = "yo‘q"
            data["step"] = "service_contacted"

            send_message(
                chat_id,
                "🔧 5-savol.\n"
                "Ishlab chiqaruvchi yoki uning servis xizmatiga "
                "murojaat qildingizmi?",
                yes_no_keyboard()
            )
            return

        send_message(
            chat_id,
            "Iltimos, quyidagi tugmalardan birini tanlang.",
            yes_no_keyboard()
        )
        return

    # 5. Sotuvchi javobi
    if step == "seller_response":
        data["seller_response"] = text
        data["step"] = "service_contacted"

        send_message(
            chat_id,
            "🔧 5-savol.\n"
            "Ishlab chiqaruvchi yoki uning servis xizmatiga "
            "murojaat qildingizmi?",
            yes_no_keyboard()
        )
        return

    # 6. Servisga murojaat
    if step == "service_contacted":
        if text == "✅ Ha":
            data["service_contacted"] = "ha"
            data["step"] = "service_response"

            send_message(
                chat_id,
                "🔧 Servis qanday xulosa yoki javob berdi?\n\n"
                "Agar yozma xulosa bo‘lsa, mazmunini yozing.",
                back_keyboard()
            )
            return

        if text == "❌ Yo‘q":
            data["service_contacted"] = "yo‘q"
            data["step"] = "receipt"

            send_message(
                chat_id,
                "🧾 6-savol.\n"
                "Kassa yoki tovar cheki mavjudmi?",
                yes_no_keyboard()
            )
            return

        send_message(
            chat_id,
            "Iltimos, quyidagi tugmalardan birini tanlang.",
            yes_no_keyboard()
        )
        return

    # 7. Servis javobi
    if step == "service_response":
        data["service_response"] = text
        data["step"] = "receipt"

        send_message(
            chat_id,
            "🧾 6-savol.\n"
            "Kassa yoki tovar cheki mavjudmi?",
            yes_no_keyboard()
        )
        return

    # 8. Chek
    if step == "receipt":
        if text == "✅ Ha":
            data["receipt"] = "mavjud"
        elif text == "❌ Yo‘q":
            data["receipt"] = "mavjud emas"
        else:
            send_message(
                chat_id,
                "Iltimos, tugmalardan birini tanlang.",
                yes_no_keyboard()
            )
            return

        data["step"] = "warranty"

        send_message(
            chat_id,
            "🛡 7-savol.\n"
            "Kafolat taloni yoki kafolat muddati ko‘rsatilgan "
            "texnik hujjat mavjudmi?",
            yes_no_keyboard()
        )
        return

    # 9. Kafolat
    if step == "warranty":
        if text == "✅ Ha":
            data["warranty"] = "mavjud"
        elif text == "❌ Yo‘q":
            data["warranty"] = "mavjud emas"
        else:
            send_message(
                chat_id,
                "Iltimos, tugmalardan birini tanlang.",
                yes_no_keyboard()
            )
            return

        data["step"] = "installment"

        send_message(
            chat_id,
            "💳 8-savol.\n"
            "Mahsulotni muddatli to‘lov yoki kredit asosida oldingizmi?",
            yes_no_keyboard()
        )
        return

    # 10. Kredit / muddatli to‘lov
    if step == "installment":
        if text == "✅ Ha":
            data["installment"] = "ha"
            data["step"] = "contract"

            send_message(
                chat_id,
                "📄 Muddatli to‘lov yoki kredit shartnomasi "
                "mavjud bo‘lsa, uni yuboring.\n\n"
                "Yuborish imkoniyati bo‘lmasa, "
                "⏭ O‘tkazib yuborish tugmasini bosing.",
                skip_keyboard()
            )
            return

        if text == "❌ Yo‘q":
            data["installment"] = "yo‘q"
            data["step"] = "evidence"

            send_message(
                chat_id,
                "📎 Qo‘shimcha dalillar mavjud bo‘lsa, "
                "ular haqida yozing yoki fayl/foto yuboring.\n\n"
                "Masalan: sotuvchi bilan yozishma, "
                "mahsulot fotosi, video yoki boshqa hujjat.",
                skip_keyboard()
            )
            return

        send_message(
            chat_id,
            "Iltimos, tugmalardan birini tanlang.",
            yes_no_keyboard()
        )
        return

    # 11. Shartnoma
    if step == "contract":
        if text in ["⏭ O‘tkazib yuborish", "O‘tkazib yuborish"]:
            data["contract"] = "yuborilmadi"
        else:
            data["contract"] = "matn ko‘rinishida qabul qilindi"

        data["step"] = "evidence"

        send_message(
            chat_id,
            "📎 Qo‘shimcha dalillar mavjud bo‘lsa, "
            "ular haqida yozing yoki fayl/foto yuboring.\n\n"
            "Masalan: sotuvchi bilan yozishma, "
            "mahsulot fotosi, video yoki boshqa hujjat.",
            skip_keyboard()
        )
        return

    # 12. Dalillar
    if step == "evidence":
        if text in ["⏭ O‘tkazib yuborish", "O‘tkazib yuborish"]:
            data["evidence"] = ""
        else:
            data["evidence"] = text

        data["step"] = "finish"

        send_message(
            chat_id,
            "Ma’lumotlar qabul qilindi. ✅\n\n"
            "Endi dastlabki yo‘l-yo‘riqni tayyorlash uchun "
            "🏁 Yakunlash tugmasini bosing.",
            finish_keyboard()
        )
        return


# =========================
# YAKUNIY TAHLIL
# =========================

def finish_case(chat_id):
    data = get_user(chat_id)

    files_count = len(data.get("evidence_files", []))

    text = (
        "🔎 MUROJAAT BO‘YICHA DASTLABKI YO‘L-YO‘RIQ\n\n"
        f"🛒 Mahsulot: {data.get('product') or 'ko‘rsatilmagan'}\n"
        f"📅 Xarid sanasi: {data.get('purchase_date') or 'ko‘rsatilmagan'}\n\n"
        f"📝 Muammo: {data.get('problem') or 'ko‘rsatilmagan'}\n\n"
        "🏪 SOTUVCHI BILAN MULOQOT\n\n"
    )

    if data.get("seller_contacted") == "ha":
        text += (
            "Siz sotuvchiga murojaat qilganingizni ko‘rsatdingiz.\n\n"
            f"Javob: {data.get('seller_response') or 'ko‘rsatilmagan'}\n\n"
        )
    else:
        text += "Siz sotuvchiga murojaat qilmaganingizni ko‘rsatdingiz.\n\n"

    text += "🔧 SERVIS\n\n"

    if data.get("service_contacted") == "ha":
        text += (
            "Siz ishlab chiqaruvchi yoki servis xizmatiga "
            "murojaat qilganingizni ko‘rsatdingiz.\n\n"
            f"Servis javobi: "
            f"{data.get('service_response') or 'ko‘rsatilmagan'}\n\n"
        )
    else:
        text += (
            "Siz ishlab chiqaruvchi yoki servis xizmatiga "
            "murojaat qilmaganingizni ko‘rsatdingiz.\n\n"
            "Agar mahsulot nuqsonining sababi yoki texnik holatini "
            "aniqlash zarur bo‘lsa, servis ko‘rigi yoki yozma xulosa "
            "foydali dalil bo‘lishi mumkin.\n\n"
        )

    text += (
        "📎 HUJJATLAR VA DALILLAR\n\n"
        f"🧾 Chek: {data.get('receipt') or 'ko‘rsatilmagan'}\n"
        f"🛡 Kafolat hujjati: {data.get('warranty') or 'ko‘rsatilmagan'}\n"
        f"💳 Muddatli to‘lov/kredit: "
        f"{data.get('installment') or 'ko‘rsatilmagan'}\n"
        f"📄 Shartnoma: {data.get('contract') or 'yuborilmagan'}\n"
        f"📸 Yuklangan fayl/foto/video: {files_count} ta\n"
        f"📝 Qo‘shimcha yozma ma’lumot: "
        f"{1 if data.get('evidence') else 0} ta\n\n"
    )

    text += (
        "📌 KEYINGI QADAM\n\n"
        "1. Sotuvchining javobi va yozishmalarini saqlang.\n"
        "2. Mavjud chek, kafolat hujjati va boshqa dalillarni "
        "bir joyga jamlang.\n"
        "3. Mahsulot nuqsonining sababi bo‘yicha texnik masala "
        "mavjud bo‘lsa, servis ko‘rigi yoki xulosasini olishni ko‘rib chiqing.\n"
        "4. Muammoning mazmuniga qarab sotuvchiga qonuniy talab "
        "qo‘yish yoki tegishli vakolatli organga murojaat qilish "
        "masalasi ko‘rib chiqiladi.\n\n"
        "⚖️ MUHIM\n\n"
        "Ushbu bot dastlabki amaliy yo‘l-yo‘riq beradi. "
        "Bot avtomatik ravishda iste’molchini yoki sotuvchini "
        "aybdor deb e’lon qilmaydi.\n\n"
        "Yakuniy baho hujjatlar, shartnoma, mahsulot holati, "
        "servis yoki ekspertiza xulosasi va boshqa dalillarga "
        "bog‘liq bo‘lishi mumkin.\n\n"
        "Agar masala boshqa maxsus vakolatli davlat organi yoki "
        "sud vakolatiga kirsa, tegishli tartibda o‘sha organga "
        "yoki sudga murojaat qilish masalasi ko‘rib chiqiladi."
    )

    send_message(chat_id, text, main_keyboard())

    data["section"] = None
    data["step"] = None


# =========================
# STATIK BO‘LIMLAR
# =========================

def show_documents(chat_id):
    text = (
        "📎 KERAKLI HUJJATLAR\n\n"
        "Muammoingizga qarab quyidagi hujjatlar foydali bo‘lishi mumkin:\n\n"
        "🧾 Kassa yoki tovar cheki — mavjud bo‘lsa\n"
        "🛡 Kafolat taloni — mavjud bo‘lsa\n"
        "📄 Texnik hujjatlar — mavjud bo‘lsa\n"
        "💳 Kredit yoki muddatli to‘lov shartnomasi — tegishli bo‘lsa\n"
        "📸 Mahsulotning foto/video dalillari\n"
        "📝 Sotuvchi bilan yozishmalar yoki javob\n"
        "🔧 Servis xulosasi — mavjud bo‘lsa\n\n"
        "Chek mavjud bo‘lmasa ham, xaridni tasdiqlovchi "
        "boshqa dalillar muhim bo‘lishi mumkin."
    )

    send_message(chat_id, text, back_keyboard())


def show_rights(chat_id):
    text = (
        "⚖️ HUQUQLARIM\n\n"
        "Iste’molchi sifatida siz mahsulot va xizmatlar haqida "
        "to‘liq va tushunarli ma’lumot olish, tegishli sifat va "
        "xavfsizlik talablariga javob beradigan mahsulotni olish, "
        "qonunchilikda nazarda tutilgan hollarda o‘z huquqlaringizni "
        "himoya qilishni talab qilish huquqiga egasiz.\n\n"
        "Aniq huquq va talab mahsulot turi, nuqson, xarid shartlari "
        "va mavjud dalillarga qarab belgilanadi."
    )

    send_message(chat_id, text, back_keyboard())


def show_refund(chat_id):
    text = (
        "💰 PULNI QAYTARISH\n\n"
        "Pulni qaytarish masalasi mahsulotning holati, nuqsoni, "
        "xarid shartlari va qonunchilikdagi tegishli talablarga "
        "bog‘liq.\n\n"
        "Aniq holatni tushunish uchun 🛒 Mahsulot muammosi "
        "bo‘limidan foydalanib, savollarga javob bering."
    )

    send_message(chat_id, text, back_keyboard())


def show_warranty(chat_id):
    text = (
        "🛠 KAFOLAT\n\n"
        "Kafolat muddati, mahsulotning nuqsoni va servis xulosasi "
        "masalaning yechimida muhim bo‘lishi mumkin.\n\n"
        "Agar kafolat hujjati mavjud bo‘lsa, uni saqlang va "
        "zarur bo‘lsa servis yoki sotuvchiga taqdim eting."
    )

    send_message(chat_id, text, back_keyboard())


def show_contact(chat_id):
    text = (
        "📞 ALOQA\n\n"
        "Mening Huquqim\n\n"
        "📲 Telegram: @Qul_Umidi\n\n"
        "Savolingiz bo‘lsa, botdagi tegishli bo‘limdan "
        "foydalanishingiz mumkin."
    )

    send_message(chat_id, text, back_keyboard())


# =========================
# PULLIK XIZMATLAR
# =========================

def show_paid_services(chat_id):
    text = (
        "💼 QO‘SHIMCHA XIZMATLAR\n\n"
        "Muammoingiz bo‘yicha qo‘shimcha amaliy yordam "
        "olishingiz mumkin.\n\n"
        "📝 Ariza tayyorlash\n"
        "📑 Hujjat tahlili\n"
        "🧭 Individual yo‘l xaritasi\n"
        "📄 Shartnoma tekshiruvi\n"
        "📂 Murojaat paketi\n"
        "👨‍💼 Mutaxassis bilan aloqa\n\n"
        "Kerakli xizmatni tanlang."
    )

    send_message(chat_id, text, paid_services_keyboard())


def paid_service_info(chat_id, service):
    services = {
        "📝 Ariza tayyorlash": (
            "📝 ARIZA TAYYORLASH\n\n"
            "Siz bergan ma’lumotlar va mavjud hujjatlar asosida "
            "ariza yoki murojaat loyihasini tayyorlash bo‘yicha "
            "yordam.\n\n"
            "Xizmat tarkibi:\n"
            "• muammoni tartibga solish\n"
            "• talablarni shakllantirish\n"
            "• murojaat loyihasini tayyorlash\n\n"
            "💳 Narxi: keyin belgilanadi.\n\n"
            "Buyurtma berish uchun mutaxassis bilan bog‘lanish "
            "bo‘limidan foydalaning."
        ),

        "📑 Hujjat tahlili": (
            "📑 HUJJAT TAHLILI\n\n"
            "Shartnoma, chek, kafolat hujjati, servis xulosasi "
            "yoki boshqa hujjatlarni ko‘rib chiqish bo‘yicha "
            "amaliy yordam."
        ),

        "🧭 Individual yo‘l xaritasi": (
            "🧭 INDIVIDUAL YO‘L XARITASI\n\n"
            "Muammoingiz bo‘yicha qaysi tashkilotga, qanday "
            "tartibda va qanday hujjatlar bilan murojaat qilish "
            "kerakligini bosqichma-bosqich shakllantirish."
        ),

        "📄 Shartnoma tekshiruvi": (
            "📄 SHARTNOMA TEKSHIRUVI\n\n"
            "Shartnomadagi muhim shartlar, to‘lovlar, majburiyatlar, "
            "jarimalar, kafolat va boshqa bandlarni tushuntirish "
            "bo‘yicha yordam."
        ),

        "📂 Murojaat paketi": (
            "📂 MUROJAAT PAKETI\n\n"
            "Muammo, mavjud hujjatlar va dalillarni tartibga solish "
            "hamda tegishli murojaat loyihasini tayyorlash bo‘yicha "
            "kompleks yordam."
        ),

        "👨‍💼 Mutaxassis bilan aloqa": (
            "👨‍💼 MUTAXASSIS BILAN ALOQA\n\n"
            "Telegram: @Qul_Umidi\n\n"
            "Murojaat qilganda muammoingizni qisqacha yozing va "
            "mavjud hujjatlarni tayyorlab qo‘ying."
        )
    }

    send_message(
        chat_id,
        services.get(service, "Xizmat topilmadi."),
        back_keyboard()
    )


# =========================
# HUJJAT / FOTO QABUL QILISH
# =========================

def handle_document(chat_id, document):
    data = get_user(chat_id)

    file_id = document.get("file_id")

    if data.get("section") == "product":
        data.setdefault("evidence_files", []).append(file_id)

        send_message(
            chat_id,
            "📎 Fayl qabul qilindi. ✅\n\n"
            "Yana fayl yuborishingiz mumkin yoki "
            "⏭ O‘tkazib yuborish tugmasini bosing.",
            skip_keyboard()
        )


def handle_photo(chat_id, photo):
    data = get_user(chat_id)

    if data.get("section") == "product":
        file_id = photo[-1].get("file_id")

        data.setdefault("evidence_files", []).append(file_id)

        send_message(
            chat_id,
            "📸 Foto qabul qilindi. ✅\n\n"
            "Yana foto/fayl yuborishingiz mumkin yoki "
            "🏁 Yakunlash tugmasini bosing.",
            finish_keyboard()
        )


# =========================
# WEBHOOK
# =========================

@app.route("/", methods=["GET", "HEAD"])
def home():
    return "Mening Huquqim bot ishlayapti.", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = request.get_json(force=True)

        message = update.get("message")

        if not message:
            return jsonify({"ok": True})

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if not chat_id:
            return jsonify({"ok": True})

        # FOTO
        if "photo" in message:
            handle_photo(chat_id, message["photo"])
            return jsonify({"ok": True})

        # HUJJAT
        if "document" in message:
            handle_document(chat_id, message["document"])
            return jsonify({"ok": True})

        # MATN
        text = message.get("text", "")

        # START
        if text == "/start":
            start_bot(chat_id)
            return jsonify({"ok": True})

        # BOSH MENYU
        if text == "🏠 Bosh menyu":
            start_bot(chat_id)
            return jsonify({"ok": True})

        # ORQAGA
        if text == "⬅️ Orqaga":
            start_bot(chat_id)
            return jsonify({"ok": True})

        # MAHSULOT
        if text == "🛒 Mahsulot muammosi":
            start_product_problem(chat_id)
            return jsonify({"ok": True})

        # STATIK BO‘LIMLAR
        if text == "💰 Pulni qaytarish":
            show_refund(chat_id)
            return jsonify({"ok": True})

        if text == "🛠 Kafolat":
            show_warranty(chat_id)
            return jsonify({"ok": True})

        if text == "📎 Kerakli hujjatlar":
            show_documents(chat_id)
            return jsonify({"ok": True})

        if text == "⚖️ Huquqlarim":
            show_rights(chat_id)
            return jsonify({"ok": True})

        if text == "📞 Aloqa":
            show_contact(chat_id)
            return jsonify({"ok": True})

        # PULLIK XIZMATLAR
        if text == "💼 Qo‘shimcha xizmatlar":
            show_paid_services(chat_id)
            return jsonify({"ok": True})

        paid_services = [
            "📝 Ariza tayyorlash",
            "📑 Hujjat tahlili",
            "🧭 Individual yo‘l xaritasi",
            "📄 Shartnoma tekshiruvi",
            "📂 Murojaat paketi",
            "👨‍💼 Mutaxassis bilan aloqa"
        ]

        if text in paid_services:
            paid_service_info(chat_id, text)
            return jsonify({"ok": True})

        # YAKUNLASH
        if text == "🏁 Yakunlash":
            data = get_user(chat_id)

            if data.get("section") == "product":
                finish_case(chat_id)
            else:
                start_bot(chat_id)

            return jsonify({"ok": True})

        # O‘TKAZIB YUBORISH
        if text in ["⏭ O‘tkazib yuborish", "O‘tkazib yuborish"]:
            data = get_user(chat_id)

            if data.get("section") == "product":
                data["step"] = "evidence"

                send_message(
                    chat_id,
                    "📎 Qo‘shimcha dalillar mavjud bo‘lsa, "
                    "ular haqida yozing yoki fayl/foto yuboring.\n\n"
                    "Yoki yana ⏭ O‘tkazib yuborish tugmasini bosing.",
                    skip_keyboard()
                )
            else:
                start_bot(chat_id)

            return jsonify({"ok": True})

        # MAHSULOT SAVOLLARI
        data = get_user(chat_id)

        if data.get("section") == "product":
            product_question(chat_id, text)
            return jsonify({"ok": True})

        # NOMA’LUM BUYRUQ
        send_message(
            chat_id,
            "Iltimos, menyudagi bo‘limlardan birini tanlang.",
            main_keyboard()
        )

        return jsonify({"ok": True})

    except Exception as e:
        print("Webhook error:", e)
        return jsonify({"ok": True})


# =========================
# ISHGA TUSHISH
# =========================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
