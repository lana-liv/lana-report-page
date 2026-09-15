import re
import sqlite3
import logging
from datetime import datetime, date, timedelta
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = "8763829769:AAG2OySlzXX_pKxePI9KK_vqjv4Kavvh0XM"

# Your Telegram numeric user ID
OWNER_ID = 6054777664

DB_FILE = "reports.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# DATABASE
# ============================================================

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_number INTEGER UNIQUE NOT NULL,
            reporter_username TEXT,
            reporter_user_id INTEGER,
            category TEXT,
            premium TEXT,
            email_number TEXT,
            password TEXT,
            profile_pin TEXT,
            days_availed INTEGER,
            share_type TEXT,
            date_purchased TEXT,
            amount_paid REAL,
            specific_issue TEXT,
            date_reported TEXT,
            expiry_date TEXT,
            days_remaining INTEGER,
            status TEXT DEFAULT 'SUBMITTED',
            refund_status TEXT DEFAULT 'NOT REQUESTED',
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def create_report(data):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COALESCE(MAX(report_number), 0) + 1
        FROM reports
        """
    )

    report_number = cur.fetchone()[0]

    cur.execute(
        """
        INSERT INTO reports (
            report_number,
            reporter_username,
            reporter_user_id,
            category,
            premium,
            email_number,
            password,
            profile_pin,
            days_availed,
            share_type,
            date_purchased,
            amount_paid,
            specific_issue,
            date_reported,
            expiry_date,
            days_remaining,
            status,
            refund_status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_number,
            data["reporter_username"],
            data["reporter_user_id"],
            data["category"],
            data["premium"],
            data["email_number"],
            data["password"],
            data["profile_pin"],
            data["days_availed"],
            data["share_type"],
            data["date_purchased"],
            data["amount_paid"],
            data["specific_issue"],
            data["date_reported"],
            data["expiry_date"],
            data["days_remaining"],
            "SUBMITTED",
            "NOT REQUESTED",
            datetime.now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()

    return report_number


def get_report(report_number):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM reports WHERE report_number = ?",
        (report_number,),
    )

    row = cur.fetchone()
    conn.close()

    return row


def update_report_status(report_number, status):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE reports
        SET status = ?
        WHERE report_number = ?
        """,
        (status, report_number),
    )

    conn.commit()
    conn.close()


def update_refund_status(report_number, refund_status):
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE reports
        SET refund_status = ?
        WHERE report_number = ?
        """,
        (refund_status, report_number),
    )

    conn.commit()
    conn.close()


# ============================================================
# DATE / NUMBER PARSING
# ============================================================

def parse_date(value):
    if not value:
        return None

    value = value.strip()

    formats = [
        "%m.%d.%y",
        "%m.%d.%Y",
        "%m/%d/%y",
        "%m/%d/%Y",
        "%m-%d-%y",
        "%m-%d-%Y",
        "%Y-%m-%d",
        "%d.%m.%y",
        "%d.%m.%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def parse_money(value):
    if not value:
        return None

    cleaned = value.replace("₱", "")
    cleaned = cleaned.replace(",", "")
    cleaned = cleaned.strip()

    match = re.search(r"\d+(?:\.\d+)?", cleaned)

    if not match:
        return None

    try:
        return float(match.group())
    except ValueError:
        return None


def parse_days(value):
    if not value:
        return None

    match = re.search(r"\d+", value)

    if not match:
        return None

    try:
        return int(match.group())
    except ValueError:
        return None


# ============================================================
# FORM PARSER
# ============================================================

def clean_text(text):
    """
    Removes some Unicode formatting characters so the parser
    can recognize labels such as:

    𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝
    𝗱𝗮𝘆𝘀 𝗮𝘃𝗮𝗶𝗹𝗲𝗱
    days availed
    """

    replacements = {
        "𝐚": "a", "𝐛": "b", "𝐜": "c", "𝐝": "d",
        "𝐞": "e", "𝐟": "f", "𝐠": "g", "𝐡": "h",
        "𝐢": "i", "𝐣": "j", "𝐤": "k", "𝐥": "l",
        "𝐦": "m", "𝐧": "n", "𝐨": "o", "𝐩": "p",
        "𝐪": "q", "𝐫": "r", "𝐬": "s", "𝐭": "t",
        "𝐮": "u", "𝐯": "v", "𝐰": "w", "𝐱": "x",
        "𝐲": "y", "𝐳": "z",

        "𝗮": "a", "𝗯": "b", "𝗰": "c", "𝗱": "d",
        "𝗲": "e", "𝗳": "f", "𝗴": "g", "𝗵": "h",
        "𝗶": "i", "𝗷": "j", "𝗸": "k", "𝗹": "l",
        "𝗺": "m", "𝗻": "n", "𝗼": "o", "𝗽": "p",
        "𝗾": "q", "𝗿": "r", "𝘀": "s", "𝘁": "t",
        "𝘂": "u", "𝘃": "v", "𝘄": "w", "𝘅": "x",
        "𝘆": "y", "𝘇": "z",

        "𝒂": "a", "𝒃": "b", "𝒄": "c", "𝒅": "d",
        "𝒆": "e", "𝒇": "f", "𝒈": "g", "𝒉": "h",
        "𝒊": "i", "𝒋": "j", "𝒌": "k", "𝒍": "l",
        "𝒎": "m", "𝒏": "n", "𝒐": "o", "𝒑": "p",
        "𝒒": "q", "𝒓": "r", "𝒔": "s", "𝒕": "t",
        "𝒖": "u", "𝒗": "v", "𝒘": "w", "𝒙": "x",
        "𝒚": "y", "𝒛": "z",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def get_field(text, labels):
    """
    Finds:
        label: value

    even if labels are written with slightly different
    capitalization.
    """

    lines = text.splitlines()

    normalized_labels = [
        label.lower().strip()
        for label in labels
    ]

    for line in lines:
        clean_line = clean_text(line).strip()

        if ":" not in clean_line:
            continue

        key, value = clean_line.split(":", 1)

        key = key.strip().lower()
        value = value.strip()

        for label in normalized_labels:
            if key == label:
                return value

    return ""


def parse_report_form(update):
    message = update.message
    raw_text = message.text or ""

    text = clean_text(raw_text)

    category = get_field(
        text,
        ["category"]
    )

    premium = get_field(
        text,
        ["what premium", "premium"]
    )

    email_number = get_field(
        text,
        ["email/number", "email / number", "email"]
    )

    password = get_field(
        text,
        ["password"]
    )

    profile_pin = get_field(
        text,
        ["profile and pin", "profile & pin", "profile/pin"]
    )

    days_raw = get_field(
        text,
        ["days availed", "days"]
    )

    share_type = get_field(
        text,
        [
            "shared/slp or sla",
            "shared / slp or sla",
            "shared/slp/sla",
            "share type",
        ]
    )

    date_purchased_raw = get_field(
        text,
        [
            "date purchased",
            "date purchase",
        ]
    )

    amount_raw = get_field(
        text,
        [
            "amount paid",
            "amount",
        ]
    )

    specific_issue = get_field(
        text,
        [
            "specific issue",
            "issue",
            "problem",
        ]
    )

    # --------------------------------------------------------
    # AUTOMATIC VALUES
    # --------------------------------------------------------

    days_availed = parse_days(days_raw)
    date_purchased = parse_date(date_purchased_raw)
    amount_paid = parse_money(amount_raw)

    date_reported = date.today()

    errors = []

    if not category:
        errors.append("category")

    if not premium:
        errors.append("what premium")

    if not days_availed:
        errors.append("days availed")

    if not date_purchased:
        errors.append("date purchased")

    if amount_paid is None:
        errors.append("amount paid")

    if not specific_issue:
        errors.append("specific issue")

    if errors:
        return None, errors

    # --------------------------------------------------------
    # AUTOMATIC EXPIRY + REMAINING DAYS
    # --------------------------------------------------------

    expiry_date = date_purchased + timedelta(days=days_availed)

    days_remaining = (expiry_date - date_reported).days

    if days_remaining < 0:
        days_remaining = 0

    username = message.from_user.username

    if username:
        username = "@" + username

    reporter_user_id = message.from_user.id

    data = {
        "reporter_username": username or "no username",
        "reporter_user_id": reporter_user_id,
        "category": category,
        "premium": premium,
        "email_number": email_number or "not provided",
        "password": password or "not provided",
        "profile_pin": profile_pin or "not provided",
        "days_availed": days_availed,
        "share_type": share_type or "not provided",
        "date_purchased": date_purchased.isoformat(),
        "amount_paid": amount_paid,
        "specific_issue": specific_issue,
        "date_reported": date_reported.isoformat(),
        "expiry_date": expiry_date.isoformat(),
        "days_remaining": days_remaining,
    }

    return data, []


# ============================================================
# DISPLAY HELPERS
# ============================================================

def format_date(value):
    if not value:
        return "not available"

    try:
        d = date.fromisoformat(value)
        return d.strftime("%B %d, %Y")
    except ValueError:
        return value


def format_money(value):
    if value is None:
        return "not available"

    if float(value).is_integer():
        return f"₱{int(value):,}"

    return f"₱{value:,.2f}"


def build_report_message(report):
    return (
        f"NEW REPORT #{report['report_number']:04d}\n\n"

        f"reporter: {report['reporter_username']}\n"
        f"user id: {report['reporter_user_id']}\n"
        f"category: {report['category']}\n"
        f"amount paid: {format_money(report['amount_paid'])}\n"
        f"days availed: {report['days_availed']}\n"
        f"date purchased: {format_date(report['date_purchased'])}\n"
        f"date reported: {format_date(report['date_reported'])}\n"
        f"subscription days remaining at report: "
        f"{report['days_remaining']} days\n"
        f"expiry date: {format_date(report['expiry_date'])}\n"
        f"status: {report['status']}\n\n"

        f"report form:\n"
        f"category: {report['category']}\n"
        f"what premium: {report['premium']}\n"
        f"email/number: {report['email_number']}\n"
        f"password: {report['password']}\n"
        f"profile and pin: {report['profile_pin']}\n"
        f"days availed: {report['days_availed']}\n"
        f"shared/slp or sla: {report['share_type']}\n"
        f"date purchased: {format_date(report['date_purchased'])}\n"
        f"amount paid: {format_money(report['amount_paid'])}\n"
        f"specific issue: {report['specific_issue']}\n\n"

        f"refund status: {report['refund_status']}"
    )


# ============================================================
# KEYBOARDS
# ============================================================

def report_actions(report_number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "request refund",
                callback_data=f"refund:{report_number}"
            )
        ],
        [
            InlineKeyboardButton(
                "mark resolved",
                callback_data=f"resolve:{report_number}"
            ),
            InlineKeyboardButton(
                "void report",
                callback_data=f"void:{report_number}"
            ),
        ],
    ])


def owner_actions(report_number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "approve refund",
                callback_data=f"approve_refund:{report_number}"
            ),
            InlineKeyboardButton(
                "reject refund",
                callback_data=f"reject_refund:{report_number}"
            ),
        ],
        [
            InlineKeyboardButton(
                "mark resolved",
                callback_data=f"resolve:{report_number}"
            ),
            InlineKeyboardButton(
                "void report",
                callback_data=f"void:{report_number}"
            ),
        ],
    ])


# ============================================================
# COMMANDS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "submit report",
                callback_data="start_report"
            )
        ]
    ])

    await update.message.reply_text(
        "welcome! please choose an option below.",
        reply_markup=keyboard,
    )


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "send your completed report form in one message.\n\n"
        "the bot will automatically read the details, "
        "calculate the subscription days remaining, "
        "and create the report number."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "commands:\n\n"
        "/start - open report menu\n"
        "/report - submit a report\n"
        "/myreports - view your submitted reports\n"
        "/reportinfo <number> - view a report\n"
        "/help - show this message"
    )


# ============================================================
# SUBMIT REPORT
# ============================================================

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # Don't try to parse commands
    if update.message.text.startswith("/"):
        return

    data, errors = parse_report_form(update)

    if errors:
        missing = "\n".join(
            f"• {item}"
            for item in errors
        )

        await update.message.reply_text(
            "report cannot be submitted yet.\n\n"
            "missing or invalid information:\n"
            f"{missing}\n\n"
            "please check the form and send it again.\n"
            "no report number has been created."
        )

        return

    report_number = create_report(data)

    report = get_report(report_number)

    # --------------------------------------------------------
    # REPORTER MESSAGE
    # --------------------------------------------------------

    reporter_text = (
        f"report submitted successfully.\n\n"
        f"report number: #{report_number:04d}\n"
        f"category: {report['category']}\n"
        f"premium: {report['premium']}\n"
        f"amount paid: {format_money(report['amount_paid'])}\n"
        f"days availed: {report['days_availed']}\n"
        f"date purchased: {format_date(report['date_purchased'])}\n"
        f"date reported: {format_date(report['date_reported'])}\n"
        f"subscription days remaining: "
        f"{report['days_remaining']} days\n"
        f"expiry date: {format_date(report['expiry_date'])}\n"
        f"status: {report['status']}"
    )

    await update.message.reply_text(
        reporter_text,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "request refund",
                    callback_data=f"refund:{report_number}"
                )
            ]
        ])
    )

    # --------------------------------------------------------
    # OWNER NOTIFICATION
    # --------------------------------------------------------

    owner_text = build_report_message(report)

    try:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=owner_text,
            reply_markup=owner_actions(report_number),
        )
    except Exception as e:
        logger.error(
            "Could not send owner notification: %s",
            e
        )


# ============================================================
# CALLBACKS
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    data = query.data

    # --------------------------------------------------------
    # START REPORT
    # --------------------------------------------------------

    if data == "start_report":
        await query.message.reply_text(
            "send your completed report form in one message.\n\n"
            "example:\n\n"
            "category: entertainment\n"
            "what premium: netflix\n"
            "email/number: example@email.com\n"
            "password: example\n"
            "profile and pin: X1 - 0427\n"
            "days availed: 30\n"
            "shared/slp or sla: shared\n"
            "date purchased: 08.27.26\n"
            "amount paid: 60\n"
            "specific issue: end subscription / nawala pagka-premium"
        )
        return

    # --------------------------------------------------------
    # GET REPORT NUMBER
    # --------------------------------------------------------

    try:
        action, number = data.split(":", 1)
        report_number = int(number)
    except ValueError:
        return

    report = get_report(report_number)

    if not report:
        await query.message.reply_text(
            "report not found."
        )
        return

    # --------------------------------------------------------
    # REFUND REQUEST
    # --------------------------------------------------------

    if action == "refund":
        if query.from_user.id != report["reporter_user_id"]:
            await query.message.reply_text(
                "only the reporter of this report can request a refund."
            )
            return

        if report["refund_status"] == "REQUESTED":
            await query.message.reply_text(
                "refund has already been requested for this report."
            )
            return

        if report["refund_status"] == "APPROVED":
            await query.message.reply_text(
                "refund has already been approved."
            )
            return

        update_refund_status(
            report_number,
            "REQUESTED"
        )

        await query.message.reply_text(
            f"refund request submitted for report "
            f"#{report_number:04d}."
        )

        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=(
                    f"REFUND REQUEST\n\n"
                    f"report: #{report_number:04d}\n"
                    f"reporter: {report['reporter_username']}\n"
                    f"user id: {report['reporter_user_id']}\n"
                    f"amount paid: {format_money(report['amount_paid'])}\n"
                    f"refund status: REQUESTED"
                ),
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "approve refund",
                            callback_data=f"approve_refund:{report_number}"
                        ),
                        InlineKeyboardButton(
                            "reject refund",
                            callback_data=f"reject_refund:{report_number}"
                        ),
                    ]
                ])
            )
        except Exception as e:
            logger.error(
                "Refund notification error: %s",
                e
            )

        return

    # --------------------------------------------------------
    # OWNER ONLY ACTIONS
    # --------------------------------------------------------

    if query.from_user.id != OWNER_ID:
        await query.message.reply_text(
            "owner-only action."
        )
        return

    # --------------------------------------------------------
    # APPROVE REFUND
    # --------------------------------------------------------

    if action == "approve_refund":
        update_refund_status(
            report_number,
            "APPROVED"
        )

        update_report_status(
            report_number,
            "REFUND APPROVED"
        )

        await query.message.reply_text(
            f"refund approved for report "
            f"#{report_number:04d}."
        )

        try:
            await context.bot.send_message(
                chat_id=report["reporter_user_id"],
                text=(
                    f"your refund request for report "
                    f"#{report_number:04d} has been approved.\n\n"
                    f"amount paid: "
                    f"{format_money(report['amount_paid'])}"
                )
            )
        except Exception as e:
            logger.error(
                "Could not notify reporter: %s",
                e
            )

        return

    # --------------------------------------------------------
    # REJECT REFUND
    # --------------------------------------------------------

    if action == "reject_refund":
        update_refund_status(
            report_number,
            "REJECTED"
        )

        update_report_status(
            report_number,
            "REFUND REJECTED"
        )

        await query.message.reply_text(
            f"refund rejected for report "
            f"#{report_number:04d}."
        )

        try:
            await context.bot.send_message(
                chat_id=report["reporter_user_id"],
                text=(
                    f"your refund request for report "
                    f"#{report_number:04d} has been rejected."
                )
            )
        except Exception as e:
            logger.error(
                "Could not notify reporter: %s",
                e
            )

        return

    # --------------------------------------------------------
    # RESOLVE
    # --------------------------------------------------------

    if action == "resolve":
        update_report_status(
            report_number,
            "RESOLVED"
        )

        await query.message.reply_text(
            f"report #{report_number:04d} marked as resolved."
        )

        try:
            await context.bot.send_message(
                chat_id=report["reporter_user_id"],
                text=(
                    f"your report #{report_number:04d} "
                    f"has been marked as resolved."
                )
            )
        except Exception as e:
            logger.error(
                "Could not notify reporter: %s",
                e
            )

        return

    # --------------------------------------------------------
    # VOID
    # --------------------------------------------------------

    if action == "void":
        update_report_status(
            report_number,
            "VOID"
        )

        await query.message.reply_text(
            f"report #{report_number:04d} has been marked as VOID."
        )

        try:
            await context.bot.send_message(
                chat_id=report["reporter_user_id"],
                text=(
                    f"your report #{report_number:04d} "
                    f"has been marked as VOID.\n\n"
                    f"please make sure the report information "
                    f"is complete and correct."
                )
            )
        except Exception as e:
            logger.error(
                "Could not notify reporter: %s",
                e
            )

        return


# ============================================================
# MY REPORTS
# ============================================================

async def myreports_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user_id = update.effective_user.id

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM reports
        WHERE reporter_user_id = ?
        ORDER BY report_number DESC
        LIMIT 20
        """,
        (user_id,),
    )

    reports = cur.fetchall()
    conn.close()

    if not reports:
        await update.message.reply_text(
            "you don't have any submitted reports yet."
        )
        return

    lines = ["your reports:\n"]

    for report in reports:
        lines.append(
            f"#{report['report_number']:04d} | "
            f"{report['category']} | "
            f"{report['status']} | "
            f"{report['days_remaining']} days remaining"
        )

    await update.message.reply_text(
        "\n".join(lines)
    )


# ============================================================
# REPORT INFO
# ============================================================

async def reportinfo_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if not context.args:
        await update.message.reply_text(
            "usage: /reportinfo 1"
        )
        return

    try:
        report_number = int(context.args[0])
    except ValueError:
        await update.message.reply_text(
            "invalid report number."
        )
        return

    report = get_report(report_number)

    if not report:
        await update.message.reply_text(
            "report not found."
        )
        return

    # Reporter can only see their own report.
    # Owner can see every report.

    if (
        update.effective_user.id != OWNER_ID
        and update.effective_user.id != report["reporter_user_id"]
    ):
        await update.message.reply_text(
            "you don't have permission to view this report."
        )
        return

    await update.message.reply_text(
        build_report_message(report)
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.error(
        "Exception while handling update:",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        print(
            "ERROR: Please put your Telegram bot token "
            "inside BOT_TOKEN first."
        )
        return

    init_db()

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("report", report_command)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("myreports", myreports_command)
    )

    application.add_handler(
        CommandHandler("reportinfo", reportinfo_command)
    )

    application.add_handler(
        CallbackQueryHandler(callback_handler)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_report
        )
    )

    application.add_error_handler(error_handler)

    print("Report bot is running...")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
