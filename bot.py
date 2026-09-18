import os
import re
import sqlite3
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 6054777664
TUTORIAL_URL = "https://t.me/lanareports"
DB_FILE = "report_bot.db"

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set.")

# ============================================================
# DATABASE
# ============================================================

conn = sqlite3.connect(DB_FILE, check_same_thread=False)
conn.row_factory = sqlite3.Row

conn.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_number TEXT UNIQUE,
    buyer_id INTEGER,
    buyer_username TEXT,
    category TEXT,
    form_text TEXT,
    premium TEXT,
    product TEXT,
    email_number TEXT,
    password TEXT,
    profile_pin TEXT,
    product_information TEXT,
    days_availed INTEGER,
    shared_type TEXT,
    date_purchased TEXT,
    date_reported TEXT,
    amount_paid REAL,
    specific_issue TEXT,
    remaining_days INTEGER,
    status TEXT,
    submitted_at TEXT,
    fixing_deadline TEXT,
    owner_message_id INTEGER,
    buyer_status_message_id INTEGER,
    replacement_sent INTEGER DEFAULT 0,
    warranty_status TEXT,
    refund_reason TEXT,
    refund_form_submitted INTEGER DEFAULT 0,
    refund_bank_details TEXT,
    refund_proof_file_id TEXT,
    refund_amount REAL,
    refund_owner_message_id INTEGER
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS counters (
    name TEXT PRIMARY KEY,
    value INTEGER NOT NULL
)
""")

conn.commit()


def db_execute(query, params=()):
    cur = conn.execute(query, params)
    conn.commit()
    return cur


def db_fetchone(query, params=()):
    return conn.execute(query, params).fetchone()


def db_fetchall(query, params=()):
    return conn.execute(query, params).fetchall()


def next_report_number():
    row = db_fetchone(
        "SELECT value FROM counters WHERE name = 'report_number'"
    )

    if not row:
        number = 1
        db_execute(
            "INSERT INTO counters(name, value) VALUES('report_number', ?)",
            (number,),
        )
    else:
        number = row["value"] + 1
        db_execute(
            "UPDATE counters SET value = ? WHERE name = 'report_number'",
            (number,),
        )

    return f"R{number:04d}"


# ============================================================
# TEXT / DATE HELPERS
# ============================================================

def clean_text(value):
    return value.strip() if value else ""


def money(value):
    try:
        return f"₱{Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"
    except Exception:
        return f"₱{value}"


def parse_amount(value):
    value = value.replace("₱", "").replace(",", "").strip()
    try:
        return float(Decimal(value))
    except InvalidOperation:
        return None


def parse_date(value):
    value = value.strip()

    formats = [
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%m/%d/%y",
        "%d/%m/%Y",
        "%d/%m/%y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%m-%d-%Y",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    return None


def format_date(d):
    return d.strftime("%Y-%m-%d")


def calculate_remaining_days(date_purchased, days_availed):
    if not date_purchased or not days_availed:
        return 0

    expiry = date_purchased + timedelta(days=days_availed)
    remaining = (expiry - date.today()).days

    return max(0, remaining)


# ============================================================
# REFUND COMPUTATION
# ============================================================

def refund_service_fee(validity_days, remaining_days):
    validity_days = int(validity_days)
    remaining_days = int(remaining_days)

    if remaining_days <= 0:
        return Decimal("0")

    # Full refund at the full validity amount.
    if validity_days == 30:
        if remaining_days >= 30:
            return Decimal("1.00")
        if 25 <= remaining_days <= 29:
            return Decimal("0.80")
        if 20 <= remaining_days <= 24:
            return Decimal("0.70")
        if 15 <= remaining_days <= 19:
            return Decimal("0.60")
        if 10 <= remaining_days <= 14:
            return Decimal("0.50")
        if 6 <= remaining_days <= 9:
            return Decimal("0.40")
        return Decimal("0")

    if validity_days == 60:
        if remaining_days >= 60:
            return Decimal("1.00")
        if 55 <= remaining_days <= 59:
            return Decimal("0.80")
        if 45 <= remaining_days <= 54:
            return Decimal("0.70")
        if 35 <= remaining_days <= 44:
            return Decimal("0.60")
        if 25 <= remaining_days <= 34:
            return Decimal("0.50")
        if 15 <= remaining_days <= 24:
            return Decimal("0.40")
        if 7 <= remaining_days <= 14:
            return Decimal("0.30")
        return Decimal("0")

    if validity_days == 90:
        if remaining_days >= 90:
            return Decimal("1.00")
        if 78 <= remaining_days <= 89:
            return Decimal("0.80")
        if 69 <= remaining_days <= 77:
            return Decimal("0.70")
        if 59 <= remaining_days <= 68:
            return Decimal("0.60")
        if 49 <= remaining_days <= 58:
            return Decimal("0.50")
        if 39 <= remaining_days <= 48:
            return Decimal("0.40")
        if 29 <= remaining_days <= 38:
            return Decimal("0.30")
        if 19 <= remaining_days <= 28:
            return Decimal("0.20")
        if 7 <= remaining_days <= 18:
            return Decimal("0.10")
        return Decimal("0")

    if validity_days == 120:
        if remaining_days >= 120:
            return Decimal("1.00")
        if 110 <= remaining_days <= 119:
            return Decimal("0.80")
        if 95 <= remaining_days <= 109:
            return Decimal("0.70")
        if 80 <= remaining_days <= 94:
            return Decimal("0.60")
        if 60 <= remaining_days <= 79:
            return Decimal("0.50")
        if 49 <= remaining_days <= 59:
            return Decimal("0.40")
        if 35 <= remaining_days <= 48:
            return Decimal("0.30")
        if 20 <= remaining_days <= 34:
            return Decimal("0.20")
        if 8 <= remaining_days <= 19:
            return Decimal("0.10")
        return Decimal("0")

    if validity_days == 150:
        if remaining_days >= 150:
            return Decimal("1.00")
        if 130 <= remaining_days <= 149:
            return Decimal("0.80")
        if 110 <= remaining_days <= 129:
            return Decimal("0.70")
        if 90 <= remaining_days <= 109:
            return Decimal("0.60")
        if 70 <= remaining_days <= 89:
            return Decimal("0.50")
        if 50 <= remaining_days <= 69:
            return Decimal("0.40")
        if 30 <= remaining_days <= 49:
            return Decimal("0.30")
        if 15 <= remaining_days <= 29:
            return Decimal("0.20")
        if 11 <= remaining_days <= 14:
            return Decimal("0.10")
        return Decimal("0")

    if validity_days == 180:
        if remaining_days >= 180:
            return Decimal("1.00")
        if 150 <= remaining_days <= 179:
            return Decimal("0.80")
        if 120 <= remaining_days <= 149:
            return Decimal("0.70")
        if 90 <= remaining_days <= 119:
            return Decimal("0.60")
        if 70 <= remaining_days <= 89:
            return Decimal("0.50")
        if 50 <= remaining_days <= 69:
            return Decimal("0.40")
        if 30 <= remaining_days <= 49:
            return Decimal("0.30")
        if 15 <= remaining_days <= 29:
            return Decimal("0.20")
        if 11 <= remaining_days <= 14:
            return Decimal("0.10")
        return Decimal("0")

    if validity_days == 360:
        if remaining_days >= 360:
            return Decimal("1.00")
        if 340 <= remaining_days <= 359:
            return Decimal("0.80")
        if 320 <= remaining_days <= 339:
            return Decimal("0.70")
        if 300 <= remaining_days <= 319:
            return Decimal("0.60")
        if 250 <= remaining_days <= 299:
            return Decimal("0.50")
        if 200 <= remaining_days <= 249:
            return Decimal("0.40")
        if 150 <= remaining_days <= 199:
            return Decimal("0.30")
        if 100 <= remaining_days <= 149:
            return Decimal("0.20")
        if 50 <= remaining_days <= 99:
            return Decimal("0.10")
        if 11 <= remaining_days <= 49:
            return Decimal("0.05")
        return Decimal("0")

    # Fallback for other validity values.
    if remaining_days >= validity_days:
        return Decimal("1.00")

    ratio = Decimal(str(remaining_days)) / Decimal(str(validity_days))

    if ratio >= Decimal("0.80"):
        return Decimal("0.80")
    if ratio >= Decimal("0.70"):
        return Decimal("0.70")
    if ratio >= Decimal("0.60"):
        return Decimal("0.60")
    if ratio >= Decimal("0.50"):
        return Decimal("0.50")
    if ratio >= Decimal("0.40"):
        return Decimal("0.40")
    if ratio >= Decimal("0.30"):
        return Decimal("0.30")
    if ratio >= Decimal("0.20"):
        return Decimal("0.20")
    if ratio >= Decimal("0.10"):
        return Decimal("0.10")

    return Decimal("0")


def calculate_refund(amount_paid, validity_days, remaining_days):
    fee = refund_service_fee(validity_days, remaining_days)

    refund = (
        Decimal(str(amount_paid))
        / Decimal(str(validity_days))
        * Decimal(str(remaining_days))
        * fee
    )

    return refund.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ============================================================
# KEYBOARDS
# ============================================================

def buyer_main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("entertainment", callback_data="form_entertainment"),
            InlineKeyboardButton("editing", callback_data="form_editing"),
        ],
        [
            InlineKeyboardButton("educational", callback_data="form_educational"),
            InlineKeyboardButton("others", callback_data="form_others"),
        ],
        [
            InlineKeyboardButton(
                "report step-by-step tutorial",
                url=TUTORIAL_URL
            )
        ],
    ])


def submit_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("submit", callback_data="buyer_submit")]
    ])


def owner_keyboard(report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("report noted", callback_data=f"owner_noted:{report_id}"),
            InlineKeyboardButton("please wait", callback_data=f"owner_wait:{report_id}"),
        ],
        [
            InlineKeyboardButton("account replaced", callback_data=f"owner_replace:{report_id}"),
            InlineKeyboardButton("account fixed", callback_data=f"owner_fixed:{report_id}"),
        ],
        [
            InlineKeyboardButton("warning", callback_data=f"owner_warning:{report_id}"),
            InlineKeyboardButton("voided", callback_data=f"owner_voided:{report_id}"),
        ],
        [
            InlineKeyboardButton(
                "can't fix/rep, for refund na",
                callback_data=f"owner_refund:{report_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "reply buyer",
                callback_data=f"owner_reply:{report_id}"
            )
        ],
    ])


def action_choice_keyboard(action, report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "send as is",
                callback_data=f"send_action:{action}:{report_id}"
            ),
            InlineKeyboardButton(
                "reply first",
                callback_data=f"reply_action:{action}:{report_id}"
            ),
        ]
    ])


def warranty_keyboard(report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "warranty activated",
                callback_data=f"warranty_yes:{report_id}"
            ),
            InlineKeyboardButton(
                "warranty voided",
                callback_data=f"warranty_no:{report_id}"
            ),
        ]
    ])


def refund_reason_keyboard(report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "can't be fixed",
                callback_data=f"refund_reason:fixed:{report_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "can't be replaced",
                callback_data=f"refund_reason:replaced:{report_id}"
            )
        ],
    ])


def refund_form_keyboard(report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "refund form",
                callback_data=f"refund_form:{report_id}"
            )
        ]
    ])


def refund_owner_keyboard(report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "refund sent",
                callback_data=f"refund_sent:{report_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "warning, wrong details/format",
                callback_data=f"refund_warning:{report_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "voided, wrong details/format",
                callback_data=f"refund_voided:{report_id}"
            )
        ],
    ])


# ============================================================
# BUYER INTRODUCTION
# ============================================================

INTRO_TEXT = """welcome to lanayanaliv's report page!
━━━━━━━━⊱⋆⊰━━━━━━━━
guide:
1. copy the form based on what premium
account you're gonna report and send it
here in one bubble chat only [please
remember that there will be a reply that
you need to send your proofs if you sent
the correct format]
2. send the screenshot of your proof of
issue and proof of vouch
3. click "submit"

terms to remember:
slp = solo profile [one device/two devices]
sla = solo account
specific issue: ano yung nangyari? bakit ka
nag re-report?
────────────────────
first mistake and first direct to owner
report = warning
second mistake and second direct to
owner report = voided"""


# ============================================================
# FORM TEXTS
# ============================================================

FORMS = {
    "entertainment": """𝗘𝗡𝗧𝗘𝗥𝗧𝗔𝗜𝗡𝗠𝗘𝗡𝗧 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐩𝐫𝐨𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐩𝐢𝐧:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐩 𝐨𝐫 𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:""",

    "educational": """𝗘𝗗𝗨𝗖𝗔𝗧𝗜𝗢𝗡𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:""",

    "editing": """𝗘𝗗𝗜𝗧𝗜𝗡𝗚 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:""",

    "others": """𝗢𝗧𝗛𝗘𝗥𝗦/𝗚𝗘𝗡𝗘𝗥𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐨𝐝𝐮𝐜𝐭:
𝐩𝐫𝐨𝐝𝐮𝐜𝐭 𝐢𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:""",
}


# ============================================================
# PARSING FORM
# ============================================================

def normalize_label(label):
    label = label.lower().strip()
    label = re.sub(r"[^\w\s/]", "", label)
    label = re.sub(r"\s+", " ", label)
    return label


def parse_form(text, category):
    lines = text.splitlines()
    values = {}

    for line in lines:
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = normalize_label(key)
        value = value.strip()

        if value:
            values[key] = value

    def get(*keys):
        for key in keys:
            normalized = normalize_label(key)
            if normalized in values:
                return values[normalized]
        return ""

    if category in ("entertainment", "educational", "editing"):
        required = {
            "what_premium": get("what premium"),
            "email_number": get("email/number", "email / number"),
            "password": get("password"),
            "days_availed": get("days availed"),
            "shared_type": get(
                "shared/slp or sla",
                "shared/sla/slp",
                "shared/sla/slp"
            ),
            "date_purchased": get("date purchased"),
            "amount_paid": get("amount paid"),
            "specific_issue": get("specific issue"),
        }

        if category == "entertainment":
            required["profile_pin"] = get("profile and pin")

        missing = [
            name for name, value in required.items()
            if not value
        ]

        if missing:
            return None, f"missing fields: {', '.join(missing)}"

        days = None
        try:
            days = int(re.search(r"\d+", required["days_availed"]).group())
        except Exception:
            pass

        if not days or days <= 0:
            return None, "days availed must be a valid number."

        purchased = parse_date(required["date_purchased"])

        if not purchased:
            return None, "date purchased is not in a recognized date format."

        amount = parse_amount(required["amount_paid"])

        if amount is None or amount < 0:
            return None, "amount paid must be a valid amount."

        reported = date.today()

        data = {
            "premium": required["what_premium"],
            "product": "",
            "email_number": required["email_number"],
            "password": required["password"],
            "profile_pin": required.get("profile_pin", ""),
            "product_information": "",
            "days_availed": days,
            "shared_type": required["shared_type"],
            "date_purchased": format_date(purchased),
            "date_reported": format_date(reported),
            "amount_paid": amount,
            "specific_issue": required["specific_issue"],
        }

        return data, None

    required = {
        "product": get("what product"),
        "product_information": get("product information"),
        "days_availed": get("days availed"),
        "date_purchased": get("date purchased"),
        "date_reported": get("date reported"),
        "amount_paid": get("amount paid"),
        "specific_issue": get("specific issue"),
    }

    missing = [
        name for name, value in required.items()
        if not value
    ]

    if missing:
        return None, f"missing fields: {', '.join(missing)}"

    try:
        days = int(re.search(r"\d+", required["days_availed"]).group())
    except Exception:
        days = None

    if not days or days <= 0:
        return None, "days availed must be a valid number."

    purchased = parse_date(required["date_purchased"])
    reported = parse_date(required["date_reported"])

    if not purchased:
        return None, "date purchased is not in a recognized date format."

    if not reported:
        return None, "date reported is not in a recognized date format."

    amount = parse_amount(required["amount_paid"])

    if amount is None or amount < 0:
        return None, "amount paid must be a valid amount."

    data = {
        "premium": "",
        "product": required["product"],
        "email_number": "",
        "password": "",
        "profile_pin": "",
        "product_information": required["product_information"],
        "days_availed": days,
        "shared_type": "",
        "date_purchased": format_date(purchased),
        "date_reported": format_date(reported),
        "amount_paid": amount,
        "specific_issue": required["specific_issue"],
    }

    return data, None


# ============================================================
# START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        await update.message.reply_text(
            "welcome to lanayanaliv's report page!\n"
            "owner mode is active."
        )
        return ConversationHandler.END

    context.user_data.clear()

    await update.message.reply_text(
        INTRO_TEXT,
        reply_markup=buyer_main_keyboard()
    )

    return ConversationHandler.END


# ============================================================
# FORM BUTTON
# ============================================================

async def form_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.replace("form_", "")
    context.user_data["category"] = category
    context.user_data["awaiting_form"] = True

    await query.message.reply_text(
        FORMS[category]
        + "\n\nsend the completed form here in one bubble chat only."
    )


# ============================================================
# BUYER FORM MESSAGE
# ============================================================

async def receive_buyer_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id == OWNER_ID:
        return

    if not context.user_data.get("awaiting_form"):
        return

    if not update.message.text:
        return

    category = context.user_data.get("category")

    if not category:
        return

    data, error = parse_form(
        update.message.text,
        category
    )

    if error:
        await update.message.reply_text(
            "please check your report form.\n\n"
            + error
            + "\n\nsend the complete corrected form again in one bubble chat."
        )
        return

    context.user_data["form_data"] = data
    context.user_data["form_text"] = update.message.text
    context.user_data["awaiting_form"] = False
    context.user_data["proof_files"] = []

    await update.message.reply_text(
        "your report form format is correct.\n\n"
        "please send your proof of issue and proof of vouch.\n"
        "send 2 photos/proofs here."
    )


# ============================================================
# BUYER PROOFS
# ============================================================

async def receive_buyer_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id == OWNER_ID:
        return

    if "form_data" not in context.user_data:
        return

    if not update.message.photo and not update.message.document:
        return

    files = context.user_data.setdefault("proof_files", [])

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    else:
        if not update.message.document.mime_type:
            await update.message.reply_text("please send an image.")
            return

        if not update.message.document.mime_type.startswith("image/"):
            await update.message.reply_text("please send an image.")
            return

        file_id = update.message.document.file_id
        file_type = "document"

    files.append({
        "file_id": file_id,
        "file_type": file_type,
    })

    count = len(files)

    if count == 1:
        await update.message.reply_text(
            "proof of issue received.\n\n"
            "please send your proof of vouch."
        )
        return

    if count == 2:
        await update.message.reply_text(
            "proof of issue and proof of vouch received.\n\n"
            "click submit when you are ready.",
            reply_markup=submit_keyboard()
        )
        return

    await update.message.reply_text(
        "2 proofs are already complete. please click submit."
    )


# ============================================================
# SUBMIT REPORT
# ============================================================

async def submit_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if user.id == OWNER_ID:
        return

    data = context.user_data.get("form_data")
    files = context.user_data.get("proof_files", [])
    category = context.user_data.get("category")

    if not data or len(files) < 2:
        await query.message.reply_text(
            "please complete the report form and send both proofs first."
        )
        return

    report_number = next_report_number()

    purchased = parse_date(data["date_purchased"])
    remaining = calculate_remaining_days(
        purchased,
        data["days_availed"]
    )

    submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fixing_deadline = (
        date.today() + timedelta(days=7)
    ).strftime("%Y-%m-%d")

    username = (
        f"@{user.username}"
        if user.username
        else "(no username)"
    )

    db_execute("""
        INSERT INTO reports (
            report_number,
            buyer_id,
            buyer_username,
            category,
            form_text,
            premium,
            product,
            email_number,
            password,
            profile_pin,
            product_information,
            days_availed,
            shared_type,
            date_purchased,
            date_reported,
            amount_paid,
            specific_issue,
            remaining_days,
            status,
            submitted_at,
            fixing_deadline
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_number,
        user.id,
        username,
        category,
        context.user_data["form_text"],
        data["premium"],
        data["product"],
        data["email_number"],
        data["password"],
        data["profile_pin"],
        data["product_information"],
        data["days_availed"],
        data["shared_type"],
        data["date_purchased"],
        data["date_reported"],
        data["amount_paid"],
        data["specific_issue"],
        remaining,
        "SUBMITTED",
        submitted_at,
        fixing_deadline,
    ))

    report_id = db_fetchone(
        "SELECT id FROM reports WHERE report_number = ?",
        (report_number,)
    )["id"]

    buyer_status = await query.message.reply_text(
        f"report number: {report_number}\n\n"
        "report submitted.\n"
        "status: submitted\n"
        "please wait 0-7 fixing days.\n\n"
        f"remaining subscription days: {remaining}"
    )

    db_execute(
        "UPDATE reports SET buyer_status_message_id = ? WHERE id = ?",
        (buyer_status.message_id, report_id)
    )

    owner_text = build_owner_report(report_id)

    owner_message = await context.bot.send_message(
        chat_id=OWNER_ID,
        text=owner_text,
        reply_markup=owner_keyboard(report_id)
    )

    db_execute(
        "UPDATE reports SET owner_message_id = ? WHERE id = ?",
        (owner_message.message_id, report_id)
    )

    # Send both proof files to owner.
    for index, proof in enumerate(files, start=1):
        caption = (
            f"report {report_number}\n"
            f"proof {index}"
        )

        if proof["file_type"] == "photo":
            await context.bot.send_photo(
                chat_id=OWNER_ID,
                photo=proof["file_id"],
                caption=caption
            )
        else:
            await context.bot.send_document(
                chat_id=OWNER_ID,
                document=proof["file_id"],
                caption=caption
            )

    await query.message.reply_text(
        "your report has been submitted successfully.\n\n"
        f"report number: {report_number}\n"
        "status: submitted\n"
        "please wait 0-7 fixing days.\n"
        f"remaining subscription days: {remaining}"
    )

    context.user_data.clear()


# ============================================================
# OWNER REPORT DISPLAY
# ============================================================

def build_owner_report(report_id):
    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return "report not found."

    category = r["category"]

    if category == "others":
        premium_line = f"𝐰𝐡𝐚𝐭 𝐩𝐫𝐨𝐝𝐮𝐜𝐭: {r['product']}"
        type_line = ""
    else:
        premium_line = f"𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦: {r['premium']}"
        type_line = f"𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚/𝐬𝐥𝐩: {r['shared_type']}"

    return (
        f"𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫𝐧𝐚𝐦𝐞: {r['buyer_username']}\n"
        f"𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫 𝐢𝐝: {r['buyer_id']}\n"
        f"𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {r['report_number']}\n\n"
        f"{premium_line}\n"
        f"{type_line}\n"
        f"𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝: {r['date_purchased']}\n"
        f"𝐫𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐝𝐚𝐲𝐬: {r['remaining_days']}\n"
        f"𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝: {money(r['amount_paid'])}\n"
        f"𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞: {r['specific_issue']}\n\n"
        f"𝐩𝐫𝐨𝐨𝐟 𝐢𝐬𝐬𝐮𝐞: received\n"
        f"𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐯𝐨𝐮𝐜𝐡: received\n\n"
        f"status: {r['status']}"
    )


# ============================================================
# OWNER BUTTONS
# ============================================================

async def owner_noted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    db_execute(
        "UPDATE reports SET status = 'REPORT NOTED' WHERE id = ?",
        (report_id,)
    )

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    await update_owner_message(query, report_id)

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=f"report number: {r['report_number']}\n\nreport noted."
    )


async def owner_wait(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    await query.message.reply_text(
        "please choose how to send this to the buyer:",
        reply_markup=action_choice_keyboard("wait", report_id)
    )


async def owner_fixed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    db_execute(
        "UPDATE reports SET status = 'ACCOUNT FIXED' WHERE id = ?",
        (report_id,)
    )

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    await update_owner_message(query, report_id)

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=(
            f"report number: {r['report_number']}\n\n"
            "same account fixed.\n\n"
            "send your proof of login within six hours here in the bot "
            "to activate your warranty. tysm!"
        )
    )

    db_execute(
        "UPDATE reports SET warranty_status = 'WAITING FOR PROOF' WHERE id = ?",
        (report_id,)
    )


async def owner_replace(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    context.user_data["replacement_report_id"] = report_id
    context.user_data["awaiting_replacement"] = True

    await query.message.reply_text(
        """𝗮𝗰𝗰𝗼𝘂𝗻𝘁 𝗿𝗲𝗽𝗹𝗮𝗰𝗲𝗺𝗲𝗻𝘁
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫:
𝐧𝐞𝐰 𝐚𝐜𝐜𝐨𝐮𝐧𝐭:
𝐧𝐞𝐰 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐧𝐞𝐰 𝐩𝐫𝐨𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐩𝐢𝐧:

send the completed replacement form in one bubble chat."""
    )


async def receive_replacement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.user_data.get("awaiting_replacement"):
        return

    text = update.message.text or ""

    report_id = context.user_data.get("replacement_report_id")

    if not report_id:
        return

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        await update.message.reply_text("report not found.")
        return

    values = {}

    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[normalize_label(key)] = value.strip()

    new_account = values.get("new account", "")
    new_password = values.get("new password", "")
    new_profile_pin = values.get("new profile and pin", "")

    if not new_account or not new_password or not new_profile_pin:
        await update.message.reply_text(
            "please send the complete replacement form with all fields."
        )
        return

    db_execute(
        "UPDATE reports SET status = 'ACCOUNT REPLACED', replacement_sent = 1 "
        "WHERE id = ?",
        (report_id,)
    )

    await update.message.reply_text("replacement sent to buyer.")

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=(
            f"report number: {r['report_number']}\n\n"
            "𝗮𝗰𝗰𝗼𝘂𝗻𝘁 𝗿𝗲𝗽𝗹𝗮𝗰𝗲𝗺𝗲𝗻𝘁\n"
            f"𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {r['report_number']}\n"
            f"𝐧𝐞𝐰 𝐚𝐜𝐜𝐨𝐮𝐧𝐭: {new_account}\n"
            f"𝐧𝐞𝐰 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝: {new_password}\n"
            f"𝐧𝐞𝐰 𝐩𝐫𝐨𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐩𝐢𝐧: {new_profile_pin}\n\n"
            "𝐬𝐞𝐧𝐝 𝐲𝐨𝐮𝐫 𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐥𝐨𝐠 𝐢𝐧 𝐰𝐢𝐭𝐡𝐢𝐧 𝐬𝐢𝐱 𝐡𝐨𝐮𝐫𝐬 𝐡𝐞𝐫𝐞 𝐢𝐧 𝐭𝐡𝐞 𝐛𝐨𝐭 𝐭𝐨 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞 𝐲𝐨𝐮𝐫 𝐰𝐚𝐫𝐫𝐚𝐧𝐭𝐲. 𝐭𝐲𝐬𝐦!"
        )
    )

    await update_owner_message_by_id(
        context,
        report_id
    )

    context.user_data.pop("replacement_report_id", None)
    context.user_data.pop("awaiting_replacement", None)


async def owner_warning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    await query.message.reply_text(
        "choose how to send the warning:",
        reply_markup=action_choice_keyboard("warning", report_id)
    )


async def owner_voided(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    await query.message.reply_text(
        "choose how to send the void:",
        reply_markup=action_choice_keyboard("voided", report_id)
    )


async def owner_refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    await query.message.reply_text(
        "why refund?",
        reply_markup=refund_reason_keyboard(report_id)
    )


# ============================================================
# ACTION SEND / REPLY
# ============================================================

async def send_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    _, action, report_id_text = query.data.split(":")
    report_id = int(report_id_text)

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    if action == "wait":
        status = "PLEASE WAIT"
        buyer_text = (
            f"report number: {r['report_number']}\n\n"
            "please wait 0-7 fixing days."
        )

        db_execute(
            "UPDATE reports SET status = ? WHERE id = ?",
            (status, report_id)
        )

    elif action == "warning":
        status = "WARNING"
        buyer_text = (
            f"report number: {r['report_number']}\n\n"
            "warning.\n"
            "please remember the report rules."
        )

        db_execute(
            "UPDATE reports SET status = ? WHERE id = ?",
            (status, report_id)
        )

    elif action == "voided":
        status = "VOIDED"
        buyer_text = (
            f"report number: {r['report_number']}\n\n"
            "your report has been voided."
        )

        db_execute(
            "UPDATE reports SET status = ? WHERE id = ?",
            (status, report_id)
        )

    else:
        return

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=buyer_text
    )

    await update_owner_message_by_id(context, report_id)


async def reply_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    _, action, report_id_text = query.data.split(":")
    report_id = int(report_id_text)

    context.user_data["manual_reply_report_id"] = report_id
    context.user_data["manual_reply_action"] = action
    context.user_data["awaiting_owner_reply"] = True

    await query.message.reply_text(
        "send the message you want to send to the buyer."
    )


async def receive_owner_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.user_data.get("awaiting_owner_reply"):
        return

    report_id = context.user_data.get("manual_reply_report_id")
    action = context.user_data.get("manual_reply_action")

    if not report_id:
        return

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    text = update.message.text or ""

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=text
    )

    if action == "warning":
        db_execute(
            "UPDATE reports SET status = 'WARNING' WHERE id = ?",
            (report_id,)
        )
    elif action == "voided":
        db_execute(
            "UPDATE reports SET status = 'VOIDED' WHERE id = ?",
            (report_id,)
        )
    elif action == "wait":
        db_execute(
            "UPDATE reports SET status = 'PLEASE WAIT' WHERE id = ?",
            (report_id,)
        )

    await update.message.reply_text("reply sent to buyer.")

    await update_owner_message_by_id(
        context,
        report_id
    )

    context.user_data.pop("manual_reply_report_id", None)
    context.user_data.pop("manual_reply_action", None)
    context.user_data.pop("awaiting_owner_reply", None)


async def owner_manual_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    context.user_data["manual_reply_report_id"] = report_id
    context.user_data["awaiting_owner_reply"] = True

    await query.message.reply_text(
        "send the message you want to send to the buyer."
    )


# ============================================================
# REFUND FLOW
# ============================================================

async def refund_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    _, reason, report_id_text = query.data.split(":")
    report_id = int(report_id_text)

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    if reason == "fixed":
        reason_text = "can't be fixed"
    else:
        reason_text = "can't be replaced"

    db_execute(
        "UPDATE reports SET status = 'FOR REFUND', refund_reason = ? WHERE id = ?",
        (reason_text, report_id)
    )

    await query.message.reply_text(
        f"refund reason: {reason_text}\n\n"
        "the buyer will now receive the refund form."
    )

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=(
            f"report number: {r['report_number']}\n\n"
            f"why refund?\n"
            f"{reason_text}\n\n"
            "━━━━━━━━⊱⋆⊰━━━━━━━━\n"
            "guide:\n"
            "~ first, fill out and submit the form\n"
            "~ second step, send your bank details\n"
            "and it can be a photo of you qr code\n"
            "or your bank number and initials\n"
            "~ last step is provide your proof of\n"
            "payment. screenshot mo yung convo\n"
            "natin sa part kung nasaan yung receipt\n"
            "na sinend mo noong nag bayad ka"
        ),
        reply_markup=refund_form_keyboard(report_id)
    )

    await update_owner_message_by_id(context, report_id)


async def refund_form_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    report_id = int(query.data.split(":")[1])

    if query.from_user.id == OWNER_ID:
        return

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r or r["buyer_id"] != query.from_user.id:
        return

    context.user_data["refund_report_id"] = report_id
    context.user_data["awaiting_refund_form"] = True

    await query.message.reply_text(
        """𝗥𝗘𝗙𝗨𝗡𝗗 𝗙𝗢𝗥𝗠
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:

send the completed refund form in one bubble chat."""
    )


async def receive_refund_form(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        return

    if not context.user_data.get("awaiting_refund_form"):
        return

    report_id = context.user_data.get("refund_report_id")

    if not report_id:
        return

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    values = {}

    for line in (update.message.text or "").splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[normalize_label(key)] = value.strip()

    report_number = values.get("report number", "")
    date_purchased = values.get("date purchased", "")
    date_reported = values.get("date reported", "")
    amount_paid = values.get("amount paid", "")

    if not all([
        report_number,
        date_purchased,
        date_reported,
        amount_paid
    ]):
        await update.message.reply_text(
            "please complete all refund form fields."
        )
        return

    if report_number != r["report_number"]:
        await update.message.reply_text(
            "report number does not match your report."
        )
        return

    purchased = parse_date(date_purchased)
    reported = parse_date(date_reported)
    amount = parse_amount(amount_paid)

    if not purchased or not reported or amount is None:
        await update.message.reply_text(
            "please check the dates and amount and send the refund form again."
        )
        return

    context.user_data["refund_date_purchased"] = format_date(purchased)
    context.user_data["refund_date_reported"] = format_date(reported)
    context.user_data["refund_amount_paid"] = amount
    context.user_data["awaiting_refund_form"] = False
    context.user_data["awaiting_bank_details"] = True

    await update.message.reply_text(
        "refund form received.\n\n"
        "now send your bank details.\n"
        "you can send a photo of your qr code or send your bank number and initials."
    )


async def receive_bank_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        return

    if not context.user_data.get("awaiting_bank_details"):
        return

    report_id = context.user_data.get("refund_report_id")

    if not report_id:
        return

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    if update.message.photo:
        bank_details = update.message.photo[-1].file_id
        context.user_data["refund_bank_type"] = "photo"
    elif update.message.document:
        bank_details = update.message.document.file_id
        context.user_data["refund_bank_type"] = "document"
    elif update.message.text:
        bank_details = update.message.text
        context.user_data["refund_bank_type"] = "text"
    else:
        await update.message.reply_text(
            "please send your qr code photo or bank number and initials."
        )
        return

    context.user_data["refund_bank_details"] = bank_details
    context.user_data["awaiting_bank_details"] = False
    context.user_data["awaiting_refund_proof"] = True

    await update.message.reply_text(
        "bank details received.\n\n"
        "now send your proof of payment.\n"
        "send a screenshot of the conversation where your payment receipt is shown."
    )


async def receive_refund_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        return

    if not context.user_data.get("awaiting_refund_proof"):
        return

    report_id = context.user_data.get("refund_report_id")

    if not report_id:
        return

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    else:
        await update.message.reply_text(
            "please send your proof of payment as a photo."
        )
        return

    context.user_data["refund_proof_file_id"] = file_id
    context.user_data["refund_proof_file_type"] = file_type
    context.user_data["awaiting_refund_proof"] = False

    await update.message.reply_text(
        "proof of payment received.\n\n"
        "click submit to send your refund request.",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "submit",
                    callback_data=f"refund_submit:{report_id}"
                )
            ]
        ])
    )


async def submit_refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    report_id = int(query.data.split(":")[1])

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r or r["buyer_id"] != query.from_user.id:
        return

    bank_details = context.user_data.get("refund_bank_details")
    proof_file_id = context.user_data.get("refund_proof_file_id")
    proof_file_type = context.user_data.get("refund_proof_file_type")

    if not bank_details or not proof_file_id:
        await query.message.reply_text(
            "please complete the bank details and proof of payment first."
        )
        return

    purchased = parse_date(r["date_purchased"])

    remaining = calculate_remaining_days(
        purchased,
        r["days_availed"]
    )

    refund_amount = calculate_refund(
        r["amount_paid"],
        r["days_availed"],
        remaining
    )

    db_execute("""
        UPDATE reports
        SET
            remaining_days = ?,
            refund_form_submitted = 1,
            refund_bank_details = ?,
            refund_proof_file_id = ?,
            refund_amount = ?,
            status = 'REFUND REQUEST SUBMITTED'
        WHERE id = ?
    """, (
        remaining,
        bank_details,
        proof_file_id,
        float(refund_amount),
        report_id,
    ))

    buyer_text = (
        f"report number: {r['report_number']}\n\n"
        "refund request submitted.\n\n"
        f"remaining days: {remaining}\n"
        f"amount paid: {money(r['amount_paid'])}\n"
        f"amount to be refunded: {money(refund_amount)}"
    )

    await query.message.reply_text(buyer_text)

    owner_text = (
        f"𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫𝐧𝐚𝐦𝐞: {r['buyer_username']}\n"
        f"𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫 𝐢𝐝: {r['buyer_id']}\n"
        f"𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {r['report_number']}\n\n"
        f"𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝: {r['date_purchased']}\n"
        f"𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝: {r['date_reported']}\n"
        f"𝐫𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐝𝐚𝐲𝐬: {remaining}\n"
        f"𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝: {money(r['amount_paid'])}\n"
        f"𝐚𝐦𝐨𝐮𝐧𝐭 𝐭𝐨 𝐛𝐞 𝐫𝐞𝐟𝐮𝐧𝐝𝐞𝐝: {money(refund_amount)}\n\n"
        f"𝐛𝐮𝐲𝐞𝐫'𝐬 𝐛𝐚𝐧𝐤 𝐝𝐞𝐭𝐚𝐢𝐥𝐬: received\n"
        f"𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐩𝐚𝐲𝐦𝐞𝐧𝐭: received"
    )

    owner_message = await context.bot.send_message(
        chat_id=OWNER_ID,
        text=owner_text,
        reply_markup=refund_owner_keyboard(report_id)
    )

    db_execute(
        "UPDATE reports SET refund_owner_message_id = ? WHERE id = ?",
        (owner_message.message_id, report_id)
    )

    if context.user_data.get("refund_bank_type") == "photo":
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=bank_details,
            caption=f"report {r['report_number']} - buyer's bank qr"
        )
    elif context.user_data.get("refund_bank_type") == "document":
        await context.bot.send_document(
            chat_id=OWNER_ID,
            document=bank_details,
            caption=f"report {r['report_number']} - buyer's bank details"
        )
    else:
        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=(
                f"report {r['report_number']} - buyer's bank details:\n"
                f"{bank_details}"
            )
        )

    if proof_file_type == "photo":
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=proof_file_id,
            caption=f"report {r['report_number']} - proof of payment"
        )
    else:
        await context.bot.send_document(
            chat_id=OWNER_ID,
            document=proof_file_id,
            caption=f"report {r['report_number']} - proof of payment"
        )

    context.user_data.clear()


# ============================================================
# REFUND OWNER ACTIONS
# ============================================================

async def refund_sent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    context.user_data["refund_receipt_report_id"] = report_id
    context.user_data["awaiting_refund_receipt"] = True

    await query.message.reply_text(
        "send the refund receipt here as proof of refund."
    )


async def receive_refund_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.user_data.get("awaiting_refund_receipt"):
        return

    report_id = context.user_data.get("refund_receipt_report_id")

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"
    else:
        await update.message.reply_text(
            "please send the refund receipt as a photo or document."
        )
        return

    db_execute(
        "UPDATE reports SET status = 'REFUND SENT' WHERE id = ?",
        (report_id,)
    )

    if file_type == "photo":
        await context.bot.send_photo(
            chat_id=r["buyer_id"],
            photo=file_id,
            caption=(
                f"report number: {r['report_number']}\n\n"
                "refund sent.\n"
                "here is your proof of refund."
            )
        )
    else:
        await context.bot.send_document(
            chat_id=r["buyer_id"],
            document=file_id,
            caption=(
                f"report number: {r['report_number']}\n\n"
                "refund sent.\n"
                "here is your proof of refund."
            )
        )

    await update.message.reply_text(
        "refund receipt sent to buyer."
    )

    await update_owner_message_by_id(
        context,
        report_id
    )

    context.user_data.pop("refund_receipt_report_id", None)
    context.user_data.pop("awaiting_refund_receipt", None)


async def refund_warning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    context.user_data["refund_action_report_id"] = report_id
    context.user_data["refund_action"] = "warning"
    context.user_data["awaiting_refund_reason"] = True

    await query.message.reply_text(
        "send the reason why the refund request has a warning."
    )


async def refund_voided(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    context.user_data["refund_action_report_id"] = report_id
    context.user_data["refund_action"] = "voided"
    context.user_data["awaiting_refund_reason"] = True

    await query.message.reply_text(
        "send the reason why the refund request is voided."
    )


async def receive_refund_action_reason(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.user_data.get("awaiting_refund_reason"):
        return

    report_id = context.user_data.get("refund_action_report_id")
    action = context.user_data.get("refund_action")

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    reason = update.message.text or ""

    if action == "warning":
        status = "REFUND WARNING"
        buyer_text = (
            f"report number: {r['report_number']}\n\n"
            "warning, wrong details/format.\n\n"
            f"reason: {reason}"
        )
    else:
        status = "REFUND VOIDED"
        buyer_text = (
            f"report number: {r['report_number']}\n\n"
            "voided, wrong details/format.\n\n"
            f"reason: {reason}"
        )

    db_execute(
        "UPDATE reports SET status = ? WHERE id = ?",
        (status, report_id)
    )

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=buyer_text
    )

    await update.message.reply_text(
        "message sent to buyer."
    )

    await update_owner_message_by_id(
        context,
        report_id
    )

    context.user_data.pop("refund_action_report_id", None)
    context.user_data.pop("refund_action", None)
    context.user_data.pop("awaiting_refund_reason", None)


# ============================================================
# WARRANTY
# ============================================================

async def receive_warranty_proof(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user

    if user.id == OWNER_ID:
        return

    if not update.message.photo and not update.message.document:
        return

    reports = db_fetchall(
        """
        SELECT * FROM reports
        WHERE buyer_id = ?
        AND warranty_status = 'WAITING FOR PROOF'
        AND status IN ('ACCOUNT FIXED', 'ACCOUNT REPLACED')
        ORDER BY id DESC
        """,
        (user.id,)
    )

    if not reports:
        return

    r = reports[0]

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    else:
        file_id = update.message.document.file_id
        file_type = "document"

    db_execute(
        "UPDATE reports SET warranty_status = 'WAITING FOR APPROVAL' WHERE id = ?",
        (r["id"],)
    )

    await update.message.reply_text(
        f"report number: {r['report_number']}\n\n"
        "proof of login received.\n"
        "wait for my approval if warranty activated or warranty voided."
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"report number: {r['report_number']}\n\n"
            "buyer sent proof of login.\n"
            "waiting for warranty approval."
        ),
        reply_markup=warranty_keyboard(r["id"])
    )

    if file_type == "photo":
        await context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=file_id,
            caption=f"report {r['report_number']} - proof of login"
        )
    else:
        await context.bot.send_document(
            chat_id=OWNER_ID,
            document=file_id,
            caption=f"report {r['report_number']} - proof of login"
        )


async def warranty_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    db_execute(
        "UPDATE reports SET warranty_status = 'ACTIVATED', status = 'WARRANTY ACTIVATED' "
        "WHERE id = ?",
        (report_id,)
    )

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=(
            f"report number: {r['report_number']}\n\n"
            "warranty activated."
        )
    )

    await query.message.reply_text(
        "warranty activated and buyer notified."
    )


async def warranty_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != OWNER_ID:
        return

    report_id = int(query.data.split(":")[1])

    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r:
        return

    db_execute(
        "UPDATE reports SET warranty_status = 'VOIDED', status = 'WARRANTY VOIDED' "
        "WHERE id = ?",
        (report_id,)
    )

    await context.bot.send_message(
        chat_id=r["buyer_id"],
        text=(
            f"report number: {r['report_number']}\n\n"
            "warranty voided."
        )
    )

    await query.message.reply_text(
        "warranty voided and buyer notified."
    )


# ============================================================
# OWNER MESSAGE UPDATES
# ============================================================

async def update_owner_message(query, report_id):
    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r or not r["owner_message_id"]:
        return

    try:
        await query.edit_message_text(
            build_owner_report(report_id),
            reply_markup=owner_keyboard(report_id)
        )
    except Exception:
        pass


async def update_owner_message_by_id(context, report_id):
    r = db_fetchone(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    )

    if not r or not r["owner_message_id"]:
        return

    try:
        await context.bot.edit_message_text(
            chat_id=OWNER_ID,
            message_id=r["owner_message_id"],
            text=build_owner_report(report_id),
            reply_markup=owner_keyboard(report_id)
        )
    except Exception:
        pass


# ============================================================
# DAILY REMAINING-DAYS UPDATE
# ============================================================

async def daily_update(context: ContextTypes.DEFAULT_TYPE):
    reports = db_fetchall(
        """
        SELECT * FROM reports
        WHERE status NOT IN (
            'REFUND SENT',
            'VOIDED',
            'REFUND VOIDED'
        )
        """
    )

    for r in reports:
        purchased = parse_date(r["date_purchased"])

        if not purchased:
            continue

        remaining = calculate_remaining_days(
            purchased,
            r["days_availed"]
        )

        old_remaining = r["remaining_days"]

        if remaining != old_remaining:
            db_execute(
                "UPDATE reports SET remaining_days = ? WHERE id = ?",
                (remaining, r["id"])
            )

        if remaining <= 0 and r["status"] not in (
            "REFUND SENT",
            "REFUND REQUEST SUBMITTED",
            "REFUND WARNING",
            "REFUND VOIDED",
        ):
            db_execute(
                "UPDATE reports SET status = 'FOR REFUND' WHERE id = ?",
                (r["id"],)
            )

            try:
                await context.bot.send_message(
                    chat_id=r["buyer_id"],
                    text=(
                        f"report number: {r['report_number']}\n\n"
                        "0 days remaining.\n"
                        "this report is now for refund."
                    ),
                    reply_markup=refund_form_keyboard(r["id"])
                )
            except Exception:
                pass

            continue

        # Update buyer status message.
        if r["buyer_status_message_id"]:
            try:
                status = db_fetchone(
                    "SELECT status FROM reports WHERE id = ?",
                    (r["id"],)
                )["status"]

                await context.bot.edit_message_text(
                    chat_id=r["buyer_id"],
                    message_id=r["buyer_status_message_id"],
                    text=(
                        f"report number: {r['report_number']}\n\n"
                        f"status: {status.lower()}\n"
                        "please wait 0-7 fixing days.\n\n"
                        f"remaining subscription days: {remaining}"
                    )
                )
            except Exception:
                pass

        # Update owner report message.
        await update_owner_message_by_id(
            context,
            r["id"]
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("BOT ERROR:", context.error)


# ============================================================
# MAIN
# ============================================================

def main():
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Start
    application.add_handler(
        CommandHandler("start", start)
    )

    # Buyer category buttons
    application.add_handler(
        CallbackQueryHandler(
            form_button,
            pattern=r"^form_(entertainment|editing|educational|others)$"
        )
    )

    # Buyer submit
    application.add_handler(
        CallbackQueryHandler(
            submit_report,
            pattern=r"^buyer_submit$"
        )
    )

    # Owner report buttons
    application.add_handler(
        CallbackQueryHandler(
            owner_noted,
            pattern=r"^owner_noted:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_wait,
            pattern=r"^owner_wait:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_replace,
            pattern=r"^owner_replace:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_fixed,
            pattern=r"^owner_fixed:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_warning,
            pattern=r"^owner_warning:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_voided,
            pattern=r"^owner_voided:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_refund,
            pattern=r"^owner_refund:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_manual_reply,
            pattern=r"^owner_reply:\d+$"
        )
    )

    # Owner send/reply choices
    application.add_handler(
        CallbackQueryHandler(
            send_action,
            pattern=r"^send_action:(wait|warning|voided):\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            reply_action,
            pattern=r"^reply_action:(wait|warning|voided):\d+$"
        )
    )

    # Refund reason
    application.add_handler(
        CallbackQueryHandler(
            refund_reason,
            pattern=r"^refund_reason:(fixed|replaced):\d+$"
        )
    )

    # Refund form
    application.add_handler(
        CallbackQueryHandler(
            refund_form_button,
            pattern=r"^refund_form:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            submit_refund,
            pattern=r"^refund_submit:\d+$"
        )
    )

    # Refund owner actions
    application.add_handler(
        CallbackQueryHandler(
            refund_sent,
            pattern=r"^refund_sent:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            refund_warning,
            pattern=r"^refund_warning:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            refund_voided,
            pattern=r"^refund_voided:\d+$"
        )
    )

    # Warranty
    application.add_handler(
        CallbackQueryHandler(
            warranty_yes,
            pattern=r"^warranty_yes:\d+$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            warranty_no,
            pattern=r"^warranty_no:\d+$"
        )
    )

    # Text handlers
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_replacement,
        ),
        group=0
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_refund_action_reason,
        ),
        group=1
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_owner_reply,
        ),
        group=2
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_refund_form,
        ),
        group=3
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_bank_details,
        ),
        group=4
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receive_buyer_form,
        ),
        group=5
    )

    # Buyer photos/documents
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.IMAGE,
            receive_buyer_photo,
        ),
        group=6
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.IMAGE,
            receive_warranty_proof,
        ),
        group=7
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.IMAGE,
            receive_refund_proof,
        ),
        group=8
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            receive_refund_receipt,
        ),
        group=9
    )

    application.add_error_handler(error_handler)

    # Daily automatic update.
    if application.job_queue:
        application.job_queue.run_repeating(
            daily_update,
            interval=86400,
            first=60,
        )

    print("welcome to lanayanaliv's report area - the report bot is currently online.")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
