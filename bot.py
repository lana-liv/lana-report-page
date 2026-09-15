import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


WELCOME_MESSAGE = """welcome to lanayanaliv's report page  🌷
     ━━━━━━━⊱⋆⊰━━━━━━━
report guide:
1. copy the form based on what premium
account you're gonna report and send it
here in one bubble chat only [please re-
member that there will be a reply that
you need to send your proofs if you sent
the correct format]
2. send the screenshot of your proof of
issue and proof of vouch
3. click "submit"

send the form in one message only and
after the form, send the screenshots of
your proof.
       ───────────────────
one mistake = warning
second mistake = voided
report directly to the owner = voided"""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("entertainment", callback_data="entertainment"),
            InlineKeyboardButton("editing", callback_data="editing"),
        ],
        [
            InlineKeyboardButton("educational", callback_data="educational"),
            InlineKeyboardButton("others", callback_data="others"),
        ],
        [
            InlineKeyboardButton(
                "report tutorial",
                url="https://t.me/lanareports"
            )
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=reply_markup
    )


async def button_pressed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        f"you selected {query.data}.\n\n"
        "the report form will be added here next."
    )


def main():
    token = os.environ.get("BOT_TOKEN")

    if not token:
        raise RuntimeError("BOT_TOKEN is missing from Railway Variables.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_pressed))

    print("bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
