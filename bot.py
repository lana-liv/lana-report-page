import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# =========================
# REPORT FORMS
# =========================

ENTERTAINMENT_FORM = """𝗘𝗡𝗧𝗘𝗥𝗧𝗔𝗜𝗡𝗠𝗘𝗡𝗧 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐩𝐫𝐨𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐩𝐢𝐧:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐩 𝐨𝐫 𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:"""

EDUCATIONAL_FORM = """𝗘𝗗𝗨𝗖𝗔𝗧𝗜𝗢𝗡𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:"""

EDITING_FORM = """𝗘𝗗𝗜𝗧𝗜𝗡𝗚 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:"""

OTHERS_FORM = """𝗢𝗧𝗛𝗘𝗥𝗦/𝗚𝗘𝗡𝗘𝗥𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐨𝐝𝐮𝐜𝐭:
𝐩𝐫𝐨𝐝𝐮𝐜𝐭 𝐢𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:"""


# =========================
# START MESSAGE
# =========================

START_MESSAGE = """🌷 SUBMIT YOUR REPORT HERE
━━━━━━━⊱⋆⊰━━━━━━━
step by step guide:
1. copy the form based on what premium account you're gonna report and send it here in one bubble chat only [please remember that there will be a reply that you need to send your proofs if you sent the correct format]
2. send the screenshot of your proof of issue and proof of vouch
3. click "submit"

send the form in one message and after the form, send the two screenshots of your proof.
────────────────────────
send the form exactly as it is. follow the format.
one mistake = warning
second mistake = voided
report directly to the owner = voided"""


# =========================
# /START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🎬 entertainment", callback_data="entertainment"),
            InlineKeyboardButton("🎨 editing", callback_data="editing"),
        ],
        [
            InlineKeyboardButton("📚 educational", callback_data="educational"),
            InlineKeyboardButton("📦 others", callback_data="others"),
        ],
        [
            InlineKeyboardButton(
                "🌷 report tutorial",
                url="https://t.me/lanareports",
            )
        ],
    ]

    await update.message.reply_text(
        START_MESSAGE,
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# =========================
# BUTTONS
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    forms = {
        "entertainment": ENTERTAINMENT_FORM,
        "educational": EDUCATIONAL_FORM,
        "editing": EDITING_FORM,
        "others": OTHERS_FORM,
    }

    form = forms.get(query.data)

    if form:
        await query.message.reply_text(
            form
            + "\n\n────────────────────────\n"
            "copy the form above and fill it out exactly as shown.\n"
            "send the completed form in ONE message."
        )


# =========================
# MAIN
# =========================

def main():
    token = os.environ["BOT_TOKEN"]

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
