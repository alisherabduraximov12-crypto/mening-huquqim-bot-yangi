
def handle_update(update):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat_id = (message.get("chat") or {}).get("id")
    if not chat_id:
        return
    text = (message.get("text") or "").strip()

    if not text:
        send_message(chat_id, "Hozircha matnli xabarlarni qabul qilaman. Muammoni matn ko‘rinishida yuboring.")
        return

    if text.startswith("/start"):
        sessions.pop(chat_id, None)
        send_message(
            chat_id,
            "Assalomu alaykum! 👋\n\n"
            "Men — “Mening Huquqim”. Iste’molchi muammosini dastlabki tahlil qilish, "
            "kerakli hujjatlarni aniqlash va ariza loyihasini tayyorlashga yordam beraman.\n\n"
            "Javoblar dastlabki axborot bo‘lib, rasmiy qaror yoki ekspertiza emas. "
            "Parol, SMS-kod yoki bank karta ma’lumotlarini yubormang."
        )
        return

    if text.startswith("/muammo") or text == "🛒 Muammom bor":
        begin_case(chat_id)
        return

    if text.startswith("/ariza") or text == "📝 Ariza tayyorlash":
        sessions[chat_id] = {"stage": "draft"}
        send_message(chat_id, "Ariza yoki talabnoma loyihasi uchun muammoni, sotuvchi/tashkilot nomini va talabingizni bitta xabarda yozing. Maxfiy ma’lumotlarni kiritmang.")
        return

    if text.startswith("/hujjatlar") or text == "📄 Kerakli hujjatlar":
        send_message(
            chat_id,
            "Odatda quyidagi hujjatlar foydali bo‘ladi:\n"
            "• chek yoki to‘lovni tasdiqlovchi hujjat;\n"
            "• shartnoma, buyurtma yoki kafolat hujjati;\n"
            "• nuqson aks etgan foto/video;\n"
            "• sotuvchiga yuborilgan talabnoma va javob;\n"
            "• zarar bo‘lsa, uni tasdiqlovchi hujjatlar.\n\n"
            "Aniq ro‘yxat vaziyatga qarab farq qiladi.\n\n" + LAW_LINKS
        )
        return

    if text.startswith("/huquqim") or text == "📚 Huquqlarim haqida":
        send_message(chat_id, "Huquqlar aniq vaziyat va tovar/xizmat turiga qarab belgilanadi. Shaxsiy holatingizni tahlil qilish uchun “🛒 Muammom bor” bo‘limini tanlang.\n\n" + LAW_LINKS)
        return

    if text.startswith("/aloqa") or text == "📞 Aloqa":
        send_message(chat_id, CONTACT_TEXT)
        return

    if text == "🔄 Qayta boshlash":
        sessions.pop(chat_id, None)
        send_message(chat_id, "Suhbat qayta boshlandi. Kerakli bo‘limni tanlang.")
        return

    session = sessions.get(chat_id)
    if session and session.get("stage") == "draft":
        sessions.pop(chat_id, None)
        prompt = (
            "Quyidagi ma’lumotlar asosida o‘zbek tilida rasmiy ariza yoki talabnoma loyihasini yozing. "
            "Noma’lum joylarni [to‘ldiring] deb belgilang. Qonun moddalarini taxmin qilmang. "
            "Oxirida ilova qilinadigan hujjatlar ro‘yxatini bering va loyiha ekanini ayting.\n\n" + text
        )
        run_ai(chat_id, prompt)
        return

    if session:
        handle_case_answer(chat_id, text)
        return

    send_message(chat_id, "Menyudan bo‘lim tanlang yoki /start buyrug‘ini yuboring.")


@app.get("/")
def health():
    return jsonify({
        "service": "Mening Huquqim",
        "status": "ok",
        "bot_token_configured": bool(BOT_TOKEN),
        "openai_key_configured": bool(OPENAI_API_KEY),
        "openai_model": OPENAI_MODEL,
    })


@app.post("/webhook")
def webhook():
    if WEBHOOK_SECRET:
        received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if received_secret != WEBHOOK_SECRET:
            return jsonify({"ok": False}), 403

    update = request.get_json(silent=True) or {}
    update_id = update.get("update_id")
    if update_id is not None:
        if update_id in seen_update_ids:
            return jsonify({"ok": True, "duplicate": True})
        seen_update_ids.add(update_id)
        if len(seen_update_ids) > 5000:
            seen_update_ids.clear()
            seen_update_ids.add(update_id)

    try:
        handle_update(update)
    except Exception as exc:
        # Do not log incoming user text or secrets.
        log.exception("Update processing failed: %s", type(exc).__name__)
        chat_id = ((update.get("message") or {}).get("chat") or {}).get("id")
        if chat_id:
            send_message(chat_id, "Kutilmagan xatolik yuz berdi. /start buyrug‘i bilan qayta urinib ko‘ring.")
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")))
