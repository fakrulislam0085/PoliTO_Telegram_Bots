import os
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# States
ASK_GROUPS, ASK_RULES, ASK_SURNAME = range(3)

# Store rules (in-memory)
rules = {}
num_groups = 0

# --- START / WELCOME ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("/findGroup")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    welcome_text = (
        "👋 Welcome to *PoliTOGroupFinderBot*!\n\n"
        # "🎓 This bot helps students at *Politecnico di Torino* find their course group.\n\n"
        "👉 How it works:\n"
        "1. From the 'NEWS' section of your course page, enter how many groups exist for your course.\n"
        "2. Provide the initial ranges for each group (format: `FAV-KHU`).\n"
        "3. Enter your surname, and I'll tell you your group.\n\n"
        "Press the button below to get started."
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")


# --- ENTRY POINT ---
async def find_group_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Please enter the number of *surname-based groups* defined in your course announcement "
        "(for example: 2, 3, or 4):",
        parse_mode="Markdown",
    )
    return ASK_GROUPS


# --- GROUP COUNT ---
async def ask_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global num_groups, rules
    try:
        num_groups = int(update.message.text.strip())
        rules = {}
        context.user_data["group_counter"] = 1
        await update.message.reply_text(
            f"✍️ Please enter the surname initials range for *Group {chr(64 + context.user_data['group_counter'])}*:\n"
            "Example format: `FAV-KHU`",
            parse_mode="Markdown",
        )
        return ASK_RULES
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number (e.g. 2, 3, 4).")
        return ASK_GROUPS


# --- RULES ---
async def ask_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global rules, num_groups
    group_num = context.user_data["group_counter"]
    group_name = f"Group {chr(64 + group_num)}"
    text = update.message.text.strip().upper()  # autocorrect to uppercase

    # format: only letters on both sides, at least 2 letters each, single dash
    if not re.match(r"^[A-Z]{2,}-[A-Z]{2,}$", text):
        await update.message.reply_text(
            "⚠️ Invalid format.\n\n"
            "Please use only *letters* (no numbers or symbols).\n"
            "Correct example: `FAV-KHU`",
            parse_mode="Markdown",
        )
        return ASK_RULES

    start, end = text.split("-")
    rules[group_name] = (start, end)

    # Next group or ask for surname
    if group_num < num_groups:
        context.user_data["group_counter"] += 1
        await update.message.reply_text(
            f"✍️ Enter the surname initials range for *Group {chr(64 + context.user_data['group_counter'])}*:",
            parse_mode="Markdown",
        )
        return ASK_RULES
    else:
        await update.message.reply_text(
            "✅ All groups have been set!\n\nNow please enter your *surname* to check your group:",
            parse_mode="Markdown",
        )
        return ASK_SURNAME


# --- SURNAME CHECK ---
async def ask_surname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    surname = update.message.text.strip().upper()[:3]  # take first 3 letters
    for group, (start, end) in rules.items():
        if start <= surname <= end:
            await update.message.reply_text(
                f"🎉 Your surname *{update.message.text}* belongs to → *{group}*", parse_mode="Markdown"
            )
            return ConversationHandler.END
    await update.message.reply_text("❌ Sorry, your surname does not match any group range.")
    return ConversationHandler.END


# --- CANCEL ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled. Type /findGroup to try again.")
    return ConversationHandler.END


import asyncio

async def main():
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("No BOT_TOKEN found. Please set it as an environment variable.")

    app = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("findGroup", find_group_entry)],
        states={
            ASK_GROUPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_groups)],
            ASK_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_rules)],
            ASK_SURNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_surname)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    # Run polling (async)
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

