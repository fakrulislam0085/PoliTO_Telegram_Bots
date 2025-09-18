# bot_render_ready.py
import os
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters

# States
ASK_LANGUAGE, ASK_GROUPS, ASK_RULES, ASK_SURNAME = range(4)

TRANSLATIONS = {
    "en": {
        "choose_language": "🌐 Choose language",
        "ask_num_groups": "📚 Enter number of surname-based groups (e.g. 2, 3, 4).",
        "ask_group_range": "✍️ Enter range for {group} (e.g. FAV-KHU).",
        "all_groups_set": "✅ All groups set! Now enter your surname:",
        "invalid_number": "❌ Enter a valid number.",
        "invalid_format": "⚠️ Invalid format. Use ABC-XYZ",
        "surname_result": "🎉 {surname} → {group}",
        "surname_not_found": "❌ No match for that surname.",
        "check_caveat": "Tip: double-check the group initials you entered (e.g., AAA-ZZZ).",
        "try_again": "🔁 Try again",
        "enter_surname": "Please enter your surname to check the group:",
        "cancelled": "❌ Cancelled. Type /findGroup to try again.",
        "back": "◀️ Back",
        "cancel": "❌ Cancel"
    },
    "it": {
        "choose_language": "🌐 Scegli la lingua",
        "ask_num_groups": "📚 Inserisci il numero di gruppi (es. 2, 3, 4).",
        "ask_group_range": "✍️ Inserisci l'intervallo per {group} (es. FAV-KHU).",
        "all_groups_set": "✅ Gruppi impostati! Ora inserisci il cognome:",
        "invalid_number": "❌ Inserisci un numero valido.",
        "invalid_format": "⚠️ Formato non valido. Usa ABC-XYZ",
        "surname_result": "🎉 {surname} → {group}",
        "surname_not_found": "❌ Nessuna corrispondenza.",
        "check_caveat": "Suggerimento: ricontrolla le iniziali di gruppo inserite (es. AAA-ZZZ).",
        "try_again": "🔁 Riprova",
        "enter_surname": "Inserisci il tuo cognome per verificare il gruppo:",
        "cancelled": "❌ Annullato. Digita /findGroup per riprovare.",
        "back": "◀️ Indietro",
        "cancel": "❌ Annulla"
    }
}

# Logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def make_keyboard(lang, primary_btn_texts):
    back = TRANSLATIONS[lang]["back"]
    cancel = TRANSLATIONS[lang]["cancel"]
    primary_row = [KeyboardButton(t) for t in primary_btn_texts]
    kb = [primary_row, [KeyboardButton(back), KeyboardButton(cancel)]]
    return ReplyKeyboardMarkup(kb, resize_keyboard=True, one_time_keyboard=False)

def push_state(context, state):
    stack = context.user_data.setdefault("stack", [])
    stack.append(state)

def pop_current_and_get_prev(context):
    stack = context.user_data.setdefault("stack", [])
    if stack:
        stack.pop()  # remove current
    return stack[-1] if stack else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("/findGroup")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    welcome_text = (
        "👋 Welcome to *PoliTO Group Finder Bot*!\n\n"
        "🎓 This bot helps you to find your course group at *Politecnico di Torino*.\n\n"
        "👉 How it works:\n"
        "1. From the 'NEWS' section of your course page, enter how many groups exist for your course.\n"
        "2. Provide the initial ranges for each group (format: FAV-KHU).\n"
        "3. Enter your surname, and I'll tell you your group.\n\n"
        "Press the button below to get started."
    )
    logging.info("/start called by %s", update.effective_user.id)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def find_group_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # reset per-user data and stack
    context.user_data.clear()
    context.user_data["lang"] = "en"
    keyboard = [[KeyboardButton("English"), KeyboardButton("Italiano")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(TRANSLATIONS["en"]["choose_language"], reply_markup=reply_markup)
    push_state(context, ASK_LANGUAGE)
    return ASK_LANGUAGE

async def resend_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, state):
    lang = context.user_data.get("lang", "en")
    if state == ASK_LANGUAGE:
        keyboard = [[KeyboardButton("English"), KeyboardButton("Italiano")]]
        await update.message.reply_text(TRANSLATIONS[lang]["choose_language"],
                                        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True))
    elif state == ASK_GROUPS:
        kb = make_keyboard(lang, ["2", "3", "4"])
        await update.message.reply_text(TRANSLATIONS[lang]["ask_num_groups"], reply_markup=kb)
    elif state == ASK_RULES:
        grp = f"Group {chr(64 + context.user_data.get('group_counter',1))}"
        kb = make_keyboard(lang, ["AAA-ZZZ"])
        await update.message.reply_text(TRANSLATIONS[lang]["ask_group_range"].format(group=grp), reply_markup=kb, parse_mode="Markdown")
    elif state == ASK_SURNAME:
        kb = make_keyboard(lang, ["Rossi", "Bianchi"])
        await update.message.reply_text(TRANSLATIONS[lang]["all_groups_set"], reply_markup=kb, parse_mode="Markdown")

# Handlers
async def ask_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in (TRANSLATIONS["en"]["cancel"], TRANSLATIONS["it"]["cancel"]):
        await update.message.reply_text(TRANSLATIONS["en"]["cancelled"])
        return ConversationHandler.END
    lang = "it" if "ital" in text.lower() else "en"
    context.user_data["lang"] = lang
    context.user_data["rules"] = {}
    context.user_data["num_groups"] = 0
    context.user_data["group_counter"] = 1
    kb = make_keyboard(lang, ["2", "3", "4"])
    await update.message.reply_text(TRANSLATIONS[lang]["ask_num_groups"], reply_markup=kb, parse_mode="Markdown")
    push_state(context, ASK_GROUPS)
    return ASK_GROUPS

async def ask_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    text = update.message.text.strip()
    if text == TRANSLATIONS[lang]["back"]:
        prev = pop_current_and_get_prev(context) or ASK_LANGUAGE
        await resend_prompt(update, context, prev)
        return prev
    if text in (TRANSLATIONS["en"]["cancel"], TRANSLATIONS["it"]["cancel"]):
        await update.message.reply_text(TRANSLATIONS[lang]["cancelled"])
        return ConversationHandler.END
    try:
        num = int(text)
        context.user_data["num_groups"] = num
        context.user_data["rules"] = {}
        context.user_data["group_counter"] = 1
        grp = f"Group {chr(64 + context.user_data['group_counter'])}"
        kb = make_keyboard(lang, ["AAA-ZZZ"])
        await update.message.reply_text(TRANSLATIONS[lang]["ask_group_range"].format(group=grp), reply_markup=kb, parse_mode="Markdown")
        push_state(context, ASK_RULES)
        return ASK_RULES
    except ValueError:
        await update.message.reply_text(TRANSLATIONS[lang]["invalid_number"])
        return ASK_GROUPS

async def ask_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    text = update.message.text.strip()
    if text == TRANSLATIONS[lang]["back"]:
        prev = pop_current_and_get_prev(context) or ASK_GROUPS
        await resend_prompt(update, context, prev)
        return prev
    if text in (TRANSLATIONS["en"]["cancel"], TRANSLATIONS["it"]["cancel"]):
        await update.message.reply_text(TRANSLATIONS[lang]["cancelled"])
        return ConversationHandler.END
    try:
        start, end = text.split("-")
        context.user_data["rules"][f"Group {chr(64 + context.user_data['group_counter'])}"] = (start.upper(), end.upper())
    except ValueError:
        await update.message.reply_text(TRANSLATIONS[lang]["invalid_format"])
        return ASK_RULES
    if context.user_data["group_counter"] < context.user_data["num_groups"]:
        context.user_data["group_counter"] += 1
        grp = f"Group {chr(64 + context.user_data['group_counter'])}"
        kb = make_keyboard(lang, ["AAA-ZZZ"])
        await update.message.reply_text(TRANSLATIONS[lang]["ask_group_range"].format(group=grp), reply_markup=kb, parse_mode="Markdown")
        push_state(context, ASK_RULES)
        return ASK_RULES
    else:
        kb = make_keyboard(lang, ["Rossi", "Bianchi"])
        await update.message.reply_text(TRANSLATIONS[lang]["all_groups_set"], reply_markup=kb, parse_mode="Markdown")
        push_state(context, ASK_SURNAME)
        return ASK_SURNAME

async def ask_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    text = update.message.text.strip()
    if text == TRANSLATIONS[lang]["back"]:
        prev = pop_current_and_get_prev(context) or ASK_RULES
        await resend_prompt(update, context, prev)
        return prev
    if text in (TRANSLATIONS["en"]["cancel"], TRANSLATIONS["it"]["cancel"]):
        await update.message.reply_text(TRANSLATIONS[lang]["cancelled"])
        return ConversationHandler.END
    if text == TRANSLATIONS[lang]["try_again"]:
        kb = make_keyboard(lang, ["Rossi", "Bianchi"])
        await update.message.reply_text(TRANSLATIONS[lang]["enter_surname"], reply_markup=kb, parse_mode="Markdown")
        return ASK_SURNAME
    surname_raw = text
    surname = surname_raw.upper()[:3]
    for group, (start, end) in context.user_data["rules"].items():
        if start <= surname <= end:
            await update.message.reply_text(TRANSLATIONS[lang]["surname_result"].format(surname=surname_raw, group=group), parse_mode="Markdown")
            return ConversationHandler.END
    kb = make_keyboard(lang, [TRANSLATIONS[lang]["try_again"]])
    await update.message.reply_text(TRANSLATIONS[lang]["surname_not_found"] + "\n\n" + TRANSLATIONS[lang]["check_caveat"],
                                    reply_markup=kb, parse_mode="Markdown")
    return ASK_SURNAME

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(TRANSLATIONS[lang]["cancelled"])
    return ConversationHandler.END

def main():
    # require environment variable (fail fast)
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logging.critical("TELEGRAM_TOKEN env var is not set. Exiting.")
        raise SystemExit("Set TELEGRAM_TOKEN environment variable before running.")

    # build application
    app = Application.builder().token(token).build()
    logging.info("Application built, starting handlers...")

    # Conversation handler (same as before)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("findGroup", find_group_entry)],
        states={
            ASK_LANGUAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_language)],
            ASK_GROUPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_groups)],
            ASK_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rules)],
            ASK_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_surname)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    # programmatically set command list so clients show slash suggestions
    import asyncio
    from telegram import BotCommand

    async def _set_cmds():
        await app.bot.set_my_commands([
            BotCommand("start", "Show welcome message"),
            BotCommand("findGroup", "Start group finder"),
            BotCommand("cancel", "Cancel the current operation")
        ])

    # Run command-setting synchronously before polling
    try:
        asyncio.get_event_loop().run_until_complete(_set_cmds())
        logging.info("Bot commands set via API")
    except Exception as e:
        logging.warning("Could not set bot commands programmatically: %s", e)

    logging.info("Application started")
    app.run_polling()


if __name__ == "__main__":
    main()
