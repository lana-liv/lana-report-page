import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "hello! welcome to lanayanaliv's report area 🎀\n\n"
        "the report bot is currently online."
    )


def main():
    token = os.environ["BOT_TOKEN"]

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))

    print("bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
