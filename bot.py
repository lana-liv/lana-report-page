import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)


WELCOME_MESSAGE = """welcome to lanayanaliv's report page
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
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝗼𝗿𝘁𝗲𝗱:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:"""


FORMS = {
    "entertainment": ENTERTAINMENT_FORM,
    "editing": EDITING_FORM,
    "educational": EDUCATIONAL_FORM,
    "others": OTHERS_FORM,
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

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

    await update.message.reply_text(
        WELCOME_MESSAGE,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data

    context.user_data["category"] = category
    context.user_data["stage"] = "waiting_form"
    context.user_data["proofs"] = []

    await query.message.reply_text(FORMS[category])


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stage = context.user_data.get("stage")

    if stage == "waiting_form":
        context.user_data["report_form"] = update.message.text

        context.user_data["stage"] = "waiting_proofs"

        await update.message.reply_text(
            "send the screenshot of your proof of vouch and proof of issue."
        )

        return

    if stage == "waiting_proofs":
        if not update.message.photo:
            await update.message.reply_text(
                "please send the screenshots of your proof of vouch and proof of issue."
            )
            return

        context.user_data["proofs"].append(update.message.photo[-1].file_id)

        proof_count = len(context.user_data["proofs"])

        if proof_count == 1:
            await update.message.reply_text(
                "proof received. send the other screenshot."
            )

        elif proof_count >= 2:
            context.user_data["stage"] = "ready_to_submit"

            keyboard = [
                [
                    InlineKeyboardButton(
                        "submit",
                        callback_data="submit_report"
                    )
                ]
            ]

            await update.message.reply_text(
                "both proofs received. click submit.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


async def submit_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if context.user_data.get("stage") != "ready_to_submit":
        await query.message.reply_text(
            "please complete the report form and send both proofs first."
        )
        return

    context.user_data["stage"] = "submitted"

    await query.message.reply_text(
        "your report has been submitted.\n\n"
        "please wait for the report to be reviewed."
    )


def main():
    token = os.environ["BOT_TOKEN"]

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(category_selected, pattern="^(entertainment|editing|educational|others)$"))
    app.add_handler(CallbackQueryHandler(submit_report, pattern="^submit_report$"))
    app.add_handler(
        MessageHandler(
            filters.TEXT | filters.PHOTO,
            receive_message
        )
    )

    print("bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
