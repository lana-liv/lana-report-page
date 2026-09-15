import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    message = (
        "welcome to lanayanaliv's report page\n"
        "   ━━━━━━━⊱⋆⊰━━━━━━━\n"
        "report guide:\n"
        "1. copy the form based on what premium\n"
        "account you're gonna report and send it\n"
        "here in one bubble chat only [please re-\n"
        "member that there will be a reply that\n"
        "you need to send your proofs if you sent\n"
        "the correct format]\n"
        "2. send the screenshot of your proof of\n"
        "issue and proof of vouch\n"
        "3. click \"submit\"\n\n"
        "send the form in one message only and\n"
        "after the form, send the screenshots of\n"
        "your proof.\n"
        "───────────────────\n"
        "one mistake = warning\n"
        "second mistake = voided\n"
        "report directly to the owner = voided"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "entertainment",
                callback_data="entertainment"
            ),
            InlineKeyboardButton(
                "editing",
                callback_data="editing"
            )
        ],
        [
            InlineKeyboardButton(
                "educational",
                callback_data="educational"
            ),
            InlineKeyboardButton(
                "others",
                callback_data="others"
            )
        ],
        [
            InlineKeyboardButton(
                "report tutorial",
                url="https://t.me/lanareports"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        reply_markup=reply_markup
    )


def main():
    token = os.environ["BOT_TOKEN"]

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))

    print("bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
