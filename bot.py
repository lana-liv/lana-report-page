import os
import re
import sqlite3
import logging
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "8763829769:AAG2OySlzXX_pKxePI9KK_vqjv4Kavvh0XM)

# Replace this with YOUR numeric Telegram user ID.
# Example: OWNER_ID = 123456789
OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))

TUTORIAL_URL = "https://t.me/lanareports"
DB_FILE = "report_bot.db"

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ============================================================
# EXACT BUYER TEXT
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
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝗲𝗱:
𝐬𝐡𝐚𝐫𝗲𝗱/𝘀𝗹𝗮:
𝐝𝗮𝘁𝗲 𝗽𝘂𝗿𝗰𝗵𝗮𝘀𝗲𝗱:
𝐚𝗺𝗼𝘂𝗻𝘁 𝗽𝗮𝗶𝗱:
𝐬𝗽𝗲𝗰𝗶𝗳𝗶𝗰 𝗶𝘀𝘀𝘂𝗲:"""

# Correct the editing form's labels to match the requested form exactly.
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
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝗲𝗱:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:"""

FORM_TEXTS = {
    "entertainment": ENTERTAINMENT_FORM,
    "editing": EDITING_FORM,
    "educational": EDUCATIONAL_FORM,
    "others": OTHERS_FORM,
}

FORM_LABELS = {
    "entertainment": [
        "what premium", "email/number", "password", "profile and pin",
        "days availed", "shared/slp or sla", "date purchased",
        "amount paid", "specific issue",
    ],
    "editing": [
        "what premium", "email/number", "password", "days availed",
        "shared/sla", "date purchased", "amount paid", "specific issue",
    ],
    "educational": [
        "what premium", "email/number", "password", "days availed",
        "shared/sla", "date purchased", "amount paid", "specific issue",
    ],
    "others": [
        "what product", "product information", "days availed",
        "date purchased", "date reported", "amount paid", "specific issue",
    ],
}

# ============================================================
# REFUND SERVICE FEE TABLES
# Exact tiers supplied by the owner.
#
# None means the owner did not provide a tier for that range.
# The bot therefore does NOT invent a percentage for those days;
# it marks the refund as "manual review required".
# ============================================================

SERVICE_TIERS = {
    30: [
        (30, 30, Decimal("1.00")),
        (25, 29, Decimal("0.80")),
        (20, 24, Decimal("0.70")),
        (15, 19, Decimal("0.60")),
        (10, 14, Decimal("0.50")),
        (6, 9, Decimal("0.40")),
    ],
    60: [
        (60, 60, Decimal("1.00")),
        (55, 59, Decimal("0.80")),
        (45, 54, Decimal("0.70")),
        (35, 44, Decimal("0.60")),
        (25, 34, Decimal("0.50")),
        (15, 24, Decimal("0.40")),
        (7, 14, Decimal("0.30")),
    ],
    90: [
        (90, 90, Decimal("1.00")),
        (78, 89, Decimal("0.80")),
        (69, 77, Decimal("0.70")),
        (59, 68, Decimal("0.60")),
        (49, 58, Decimal("0.50")),
        (39, 48, Decimal("0.40")),
        (29, 38, Decimal("0.30")),
        (19, 28, Decimal("0.20")),
        (7, 18, Decimal("0.10")),
    ],
    120: [
        (120, 120, Decimal("1.00")),
        (110, 119, Decimal("0.80")),
        (95, 109, Decimal("0.70")),
        (80, 94, Decimal("0.60")),
        (60, 79, Decimal("0.50")),
        (49, 59, Decimal("0.40")),
        (35, 48, Decimal("0.30")),
        (20, 34, Decimal("0.20")),
        (8, 19, Decimal("0.10")),
    ],
    150: [
        (150, 150, Decimal("1.00")),
        (130, 149, Decimal("0.80")),
        (110, 129, Decimal("0.70")),
        (90, 109, Decimal("0.60")),
        (70, 89, Decimal("0.50")),
        (50, 69, Decimal("0.40")),
        (30, 49, Decimal("0.30")),
        (15, 29, Decimal("0.20")),
        (11, 14, Decimal("0.10")),
    ],
    180: [
        (180, 180, Decimal("1.00")),
        (150, 179, Decimal("0.80")),
        (120, 149, Decimal("0.70")),
        (90, 119, Decimal("0.60")),
        (70, 89, Decimal("0.50")),
        (50, 69, Decimal("0.40")),
        (30, 49, Decimal("0.30")),
        (15, 29, Decimal("0.20")),
        (11, 14, Decimal("0.10")),
    ],
    360: [
        (360, 360, Decimal("1.00")),
        (340, 359, Decimal("0.80")),
        (320, 339, Decimal("0.70")),
        (300, 319, Decimal("0.60")),
        (250, 299, Decimal("0.50")),
        (200, 249, Decimal("0.40")),
        (150, 199, Decimal("0.30")),
        (100, 149, Decimal("0.20")),
        (50, 99, Decimal("0.10")),
        (11, 49, Decimal("0.05")),
    ],
}

# Validity-day labels supplied by the owner.
# The refund table itself is based on the "maximum remaining days"
# specified for each subscription.
VALIDITY_OPTIONS = {
    30: "1 month / 25 working days",
    60: "2 months / 54 working days",
    90: "3 months / 84 working days",
    120: "4 months / 113 working days",
    150: "5 months / 140 working days",
    180: "6 months / 170 working days",
    360: "12 months / 350 working days",
}

# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_number TEXT UNIQUE,
            buyer_id INTEGER NOT NULL,
            buyer_username TEXT,
            category TEXT NOT NULL,
            form_text TEXT NOT NULL,
            date_purchased TEXT,
            date_reported TEXT,
            days_availed INTEGER,
            amount_paid TEXT,
            remaining_days INTEGER,
            refund_amount TEXT,
            refund_multiplier TEXT,
            refund_manual INTEGER DEFAULT 0,
            status TEXT DEFAULT 'SUBMITTED',
            proof_issue_message_id INTEGER,
            proof_vouch_message_id INTEGER,
            proof_payment_message_id INTEGER,
            refund_receipt_message_id INTEGER,
            warranty_proof_message_id INTEGER,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER PRIMARY KEY,
            category TEXT,
            stage TEXT,
            form_message TEXT,
            report_id INTEGER,
            extra TEXT
        );

        CREATE TABLE IF NOT EXISTS report_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            event TEXT,
            reason TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.commit()
conn.close()

def set_session(user_id, category=None, stage=None, form_message=None,
                report_id=None, extra=None):
    conn = db()
    conn.execute(
        """
        INSERT INTO user_sessions(user_id, category, stage, form_message, report_id, extra)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            category=excluded.category,
            stage=excluded.stage,
            form_message=excluded.form_message,
            report_id=excluded.report_id,
            extra=excluded.extra
        """,
        (user_id, category, stage, form_message, report_id, extra),
    )
    conn.commit()
    conn.close()

def get_session(user_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM user_sessions WHERE user_id=?", (user_id,)
    ).fetchone()
    conn.close()
    return row

def clear_session(user_id):
    conn = db()
    conn.execute("DELETE FROM user_sessions WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_report(report_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM reports WHERE id=?", (report_id,)
    ).fetchone()
    conn.close()
    return row

def get_report_by_number(report_number):
    conn = db()
    row = conn.execute(
        "SELECT * FROM reports WHERE report_number=?", (report_number,)
    ).fetchone()
    conn.close()
    return row

def add_event(report_id, event, reason=""):
    conn = db()
    conn.execute(
        "INSERT INTO report_events(report_id,event,reason,created_at) VALUES(?,?,?,?)",
        (report_id, event, reason, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()

# ============================================================
# HELPERS
# ============================================================

def owner_only(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id == OWNER_ID)

def money(value: Decimal) -> str:
    value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"₱{value:,.2f}"

def parse_money(text: str):
    m = re.search(r"(?:₱|php|p)?\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)", text, re.I)
    if not m:
        return None
    try:
        return Decimal(m.group(1).replace(",", ""))
    except InvalidOperation:
        return None

def parse_date_value(text: str):
    # Supports common forms such as:
    # 09/16/2026, 9/16/2026, 2026-09-16, Sep 16 2026, September 16, 2026
    patterns = [
        "%m/%d/%Y", "%m-%d-%Y", "%Y-%m-%d",
        "%m/%d/%y", "%m-%d-%y",
        "%B %d, %Y", "%B %d %Y",
        "%b %d, %Y", "%b %d %Y",
        "%d/%m/%Y", "%d-%m-%Y",
    ]
    for line in text.splitlines():
        if ":" not in line:
            continue
        value = line.split(":", 1)[1].strip()
        for fmt in patterns:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
    return None

def extract_field(text: str, label):
    target = label.lower()
    for line in text.splitlines():
        clean = re.sub(r"[*_`]", "", line).strip().lower()
        if clean.startswith(target + ":"):
            return line.split(":", 1)[1].strip()
    return ""

def extract_days(text: str):
    value = extract_field(text, "days availed")
    m = re.search(r"\d+", value)
    return int(m.group()) if m else None

def extract_amount(text: str):
    value = extract_field(text, "amount paid")
    return parse_money(value)

def choose_refund_table(days_availed):
    if days_availed is None:
        return None
    # User's service tables are based on these standard subscription lengths.
    # Exact matches are preferred. Otherwise use nearest standard length.
    standards = sorted(SERVICE_TIERS.keys())
    if days_availed in standards:
        return days_availed

    # Accept a few common representations (25/54/84/113/140/170/350 working days)
    working_to_calendar = {
        25: 30, 54: 60, 84: 90, 113: 120,
        140: 150, 170: 180, 350: 360,
    }
    if days_availed in working_to_calendar:
        return working_to_calendar[days_availed]

    return min(standards, key=lambda x: abs(x - days_availed))

def service_multiplier(calendar_validity, remaining_days):
    tiers = SERVICE_TIERS.get(calendar_validity, [])
    for low, high, multiplier in tiers:
        if low <= remaining_days <= high:
            return multiplier
    return None

def calculate_remaining_days(date_purchased, validity_days):
    """
    Remaining days are calculated from the purchase date to today's date,
    using calendar days, then capped at zero and at the submitted validity.
    This is the automatic countdown basis used by the bot.
    """
    today = date.today()
    elapsed = (today - date_purchased).days
    return max(0, validity_days - elapsed)

def calculate_refund(amount_paid, validity_days, remaining_days):
    table_days = choose_refund_table(validity_days)
    if table_days is None:
        return None, None, True, "validity days not recognized"

    multiplier = service_multiplier(table_days, remaining_days)
    if multiplier is None:
        return None, None, True, "no service-fee tier was provided for this remaining-day range"

    refund = (amount_paid / Decimal(validity_days)) * Decimal(remaining_days) * multiplier
    return refund.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), multiplier, False, ""

def buyer_name(user):
    if user.username:
        return f"@{user.username}"
    return user.full_name or str(user.id)

def main_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("entertainment", callback_data="cat:entertainment"),
            InlineKeyboardButton("editing", callback_data="cat:editing"),
        ],
        [
            InlineKeyboardButton("educational", callback_data="cat:educational"),
            InlineKeyboardButton("others", callback_data="cat:others"),
        ],
        [
            InlineKeyboardButton(
                "report step-by-step tutorial",
                url=TUTORIAL_URL,
            )
        ],
    ])

def submit_keyboard(report_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("submit", callback_data=f"submit:{report_id}")]
    ])

def seller_report_keyboard(report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("account fixed", callback_data=f"fixed:{report_id}"),
            InlineKeyboardButton("account replaced", callback_data=f"replaced:{report_id}"),
        ],
        [
            InlineKeyboardButton("refund sent", callback_data=f"refund_sent:{report_id}"),
        ],
        [
            InlineKeyboardButton(
                "warning, wrong details/format",
                callback_data=f"warning:{report_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "voided, wrong details/format",
                callback_data=f"voided:{report_id}",
            )
        ],
        [
            InlineKeyboardButton("reply to buyer", callback_data=f"reply:{report_id}"),
        ],
    ])

def warranty_keyboard(report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "warranty activated",
                callback_data=f"warranty_yes:{report_id}",
            ),
            InlineKeyboardButton(
                "warranty voided",
                callback_data=f"warranty_no:{report_id}",
            ),
        ],
        [
            InlineKeyboardButton("reply to buyer", callback_data=f"reply:{report_id}")
        ],
    ])

def refund_reason_keyboard(report_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "can't be fixed",
                callback_data=f"refund_reason_fixed:{report_id}",
            ),
            InlineKeyboardButton(
                "can't be replaced",
                callback_data=f"refund_reason_replaced:{report_id}",
            ),
        ]
    ])

def status_line(report):
    return f"status: {report['status']}"

def seller_report_text(report):
    refund = report["refund_amount"] or "manual review required"
return f"""𝗥𝗘𝗣𝗢𝗥𝗧 {report['report_number']}

𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫𝐧𝐚𝐦𝐞: {report['buyer_username'] or 'no username'}
𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫 𝐢𝐝: {report['buyer_id']}
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {report['report_number']}

𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝: {report['date_purchased']}
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝: {report['date_reported']}
𝐫𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐝𝐚𝐲𝐬: {report['remaining_days']}
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝: {report['amount_paid']}
𝐚𝐦𝐨𝐮𝐧𝐭 𝐭𝐨 𝐛𝐞 𝐫𝐞𝐟𝐮𝐧𝐝𝐞𝐝: {refund}

𝐛𝐮𝐲𝐞𝐫'𝐬 𝐛𝐚𝐧𝐤 𝐝𝐞𝐭𝐚𝐢𝐥𝐬: pending from buyer if refund is required
𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐩𝐚𝐲𝐦𝐞𝐧𝐭: attached above

{status_line(report)}"""

# ============================================================
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    clear_session(user.id)

    await update.message.reply_text(
        INTRO_TEXT,
        reply_markup=main_keyboard(),
    )

# ============================================================
# CATEGORY BUTTONS
# ============================================================

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.split(":", 1)[1]
    user = query.from_user

    form = FORM_TEXTS[category]
    set_session(
        user.id,
        category=category,
        stage="awaiting_form",
        form_message=form,
    )

    await query.message.reply_text(
        form + "\n\nsend the completed form in one bubble chat only."
    )

# ============================================================
# BUYER FORM
# ============================================================

def validate_form(category, text):
    lower = text.lower()
    missing = []

    for label in FORM_LABELS[category]:
        if label not in lower:
            missing.append(label)

    if missing:
        return False, f"missing fields: {', '.join(missing)}"

    days = extract_days(text)
    if not days or days <= 0:
        return False, "please enter a valid number for days availed."

    amount = extract_amount(text)
    if amount is None or amount < 0:
        return False, "please enter a valid amount paid."

    purchased = parse_date_value(text)
    if purchased is None:
        return False, "please enter date purchased in a recognizable format such as 09/16/2026."

    if purchased > date.today():
        return False, "date purchased cannot be in the future."

    return True, ""

async def buyer_form_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message or not update.message.text:
        return

    session = get_session(user.id)
    if not session or session["stage"] != "awaiting_form":
        return

    category = session["category"]
    text = update.message.text.strip()

    ok, reason = validate_form(category, text)
    if not ok:
        await update.message.reply_text(
            f"the report form is incomplete or invalid.\n\n{reason}\n\n"
            "please send the complete form again in one bubble chat only."
        )
        return

    set_session(
        user.id,
        category=category,
        stage="awaiting_proof_issue",
        form_message=text,
    )

    await update.message.reply_text(
        'format received.\n\nplease send your screenshot of proof of issue.'
    )

# ============================================================
# PROOFS
# ============================================================

async def buyer_proof_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    session = get_session(user.id)
    if not session:
        return

    stage = session["stage"]

    if stage == "awaiting_proof_issue":
        set_session(
            user.id,
            category=session["category"],
            stage="awaiting_proof_vouch",
            form_message=session["form_message"],
        )
        await update.message.reply_text(
            "proof of issue received.\n\nplease send your screenshot of proof of vouch."
        )
        return

    if stage == "awaiting_proof_vouch":
        set_session(
            user.id,
            category=session["category"],
            stage="awaiting_proof_payment",
            form_message=session["form_message"],
        )
        await update.message.reply_text(
            "proof of vouch received.\n\nplease send your proof of payment that "
            "shows the amount paid."
        )
        return

    if stage == "awaiting_proof_payment":
        # Create a temporary report. It only becomes SUBMITTED when buyer presses submit.
        category = session["category"]
        form_text = session["form_message"]
        days = extract_days(form_text)
        amount = extract_amount(form_text)
        purchased = parse_date_value(form_text)
        reported = date.today()

        remaining = calculate_remaining_days(purchased, days)
        refund, multiplier, manual, _ = calculate_refund(
            amount, days, remaining
        )

        conn = db()
        cur = conn.execute(
"""
            INSERT INTO reports(
                report_number,buyer_id,buyer_username,category,form_text,
                date_purchased,date_reported,days_availed,amount_paid,
                remaining_days,refund_amount,refund_multiplier,refund_manual,
                status,proof_payment_message_id,created_at
            )
            VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user.id,
                f"@{user.username}" if user.username else "",
                category,
                form_text,
                purchased.isoformat(),
                reported.isoformat(),
                days,
                str(amount),
                remaining,
                str(refund) if refund is not None else None,
                str(multiplier) if multiplier is not None else None,
                1 if manual else 0,
                "DRAFT",
                update.message.message_id,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        report_id = cur.lastrowid
        report_number = f"LR-{report_id:05d}"
        conn.execute(
            "UPDATE reports SET report_number=? WHERE id=?",
            (report_number, report_id),
        )
        conn.commit()
        conn.close()

        set_session(
            user.id,
            category=category,
            stage="awaiting_submit",
            form_message=form_text,
            report_id=report_id,
        )

        await update.message.reply_text(
            f"proof of payment received.\n\n"
            f"report number: {report_number}\n\n"
            "please review your report and click submit.",
            reply_markup=submit_keyboard(report_id),
        )
        return

# ============================================================
# BUYER SUBMIT
# ============================================================

async def submit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)

    if not report or report["buyer_id"] != query.from_user.id:
        await query.message.reply_text("this report does not belong to your account.")
        return

    if report["status"] != "DRAFT":
        await query.message.reply_text("this report has already been submitted.")
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='SUBMITTED' WHERE id=?",
        (report_id,),
    )
    conn.commit()
    conn.close()

    add_event(report_id, "SUBMITTED")

    report = get_report(report_id)

    buyer_message = f"""report submitted successfully.

report number: {report['report_number']}
status: SUBMITTED

please wait 0–7 days fixing days.

if the issue cannot be fixed after the fixing period, the report may proceed to FOR REFUND."""

    await query.message.reply_text(buyer_message)

    # Send seller report information.
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=seller_report_text(report),
        reply_markup=seller_report_keyboard(report_id),
    )

    # Forward the original form and payment proof to owner.
    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"category: {report['category']}\n"
            f"report number: {report['report_number']}\n\n"
            f"buyer form:\n{report['form_text']}"
        ),
    )

    # Forward proof payment if it exists.
    if report["proof_payment_message_id"]:
        try:
            await context.bot.forward_message(
                chat_id=OWNER_ID,
                from_chat_id=report["buyer_id"],
                message_id=report["proof_payment_message_id"],
            )
        except Exception as exc:
            logger.warning("Could not forward proof of payment: %s", exc)

    clear_session(query.from_user.id)

# ============================================================
# SELLER ACTION HELPERS
# ============================================================

async def notify_buyer(context, report, text):
    await context.bot.send_message(
        chat_id=report["buyer_id"],
        text=text,
    )

async def fixed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)
    if not report:
        await query.message.reply_text("report not found.")
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='ACCOUNT FIXED' WHERE id=?",
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_event(report_id, "ACCOUNT FIXED")

    await notify_buyer(
        context,
        report,
        f"""report number: {report['report_number']}

same account fixed.

kindly send proof of log in within six hours to activate warranty.""",
    )

    await query.message.reply_text(
        f"report {report['report_number']} marked as ACCOUNT FIXED.\n"
        "waiting for buyer's proof of log in."
    )

async def replaced_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)
    if not report:
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='ACCOUNT REPLACED' WHERE id=?",
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_event(report_id, "ACCOUNT REPLACED")

    await notify_buyer(
        context,
        report,
        f"""report number: {report['report_number']}

account replaced.

kindly check the replacement account and send proof of log in if requested.""",
    )

    await query.message.reply_text(
        f"report {report['report_number']} marked as ACCOUNT REPLACED."
    )

# ============================================================
# WARRANTY PROOF
# ============================================================

async def warranty_proof_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    session = get_session(user.id)
    if not session or session["stage"] != "awaiting_warranty_proof":
        return

    report_id = session["report_id"]
    report = get_report(report_id)
    if not report:
        clear_session(user.id)
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET warranty_proof_message_id=?, status='WARRANTY PROOF SENT' WHERE id=?",
        (update.message.message_id, report_id),
    )
    conn.commit()
    conn.close()

    add_event(report_id, "WARRANTY PROOF SENT")

    await update.message.reply_text(
        f"proof of log in received for report {report['report_number']}."
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"warranty proof received\n"
            f"report number: {report['report_number']}\n"
            f"buyer's username: {buyer_name(user)}\n"
            f"buyer's user id: {user.id}"
        ),
        reply_markup=warranty_keyboard(report_id),
    )

    try:
        await context.bot.forward_message(
            chat_id=OWNER_ID,
            from_chat_id=user.id,
            message_id=update.message.message_id,
        )
    except Exception as exc:
        logger.warning("Could not forward warranty proof: %s", exc)

clear_session(user.id)

# ============================================================
# WARRANTY BUTTONS
# ============================================================

async def warranty_yes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)
    if not report:
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='WARRANTY ACTIVATED' WHERE id=?",
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_event(report_id, "WARRANTY ACTIVATED")

    await notify_buyer(
        context,
        report,
        f"""report number: {report['report_number']}

warranty activated.""",
    )

    await query.message.reply_text(
        f"warranty activated for report {report['report_number']}."
    )

async def warranty_no_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)
    if not report:
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='WARRANTY VOIDED' WHERE id=?",
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_event(report_id, "WARRANTY VOIDED")

    await notify_buyer(
        context,
        report,
        f"""report number: {report['report_number']}

warranty voided.""",
    )

    await query.message.reply_text(
        f"warranty voided for report {report['report_number']}."
    )

# ============================================================
# REFUND FLOW
# ============================================================

async def refund_sent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)
    if not report:
        return

    set_session(
        OWNER_ID,
        stage="awaiting_refund_receipt",
        report_id=report_id,
    )

    await query.message.reply_text(
        f"send the refund receipt/proof of refund for report {report['report_number']}.\n\n"
        "after you send it, the bot will forward it to the buyer."
    )

async def owner_refund_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update) or not update.message:
        return

    session = get_session(OWNER_ID)
    if not session or session["stage"] != "awaiting_refund_receipt":
        return

    report_id = session["report_id"]
    report = get_report(report_id)
    if not report:
        clear_session(OWNER_ID)
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='REFUND SENT', refund_receipt_message_id=? WHERE id=?",
        (update.message.message_id, report_id),
    )
    conn.commit()
    conn.close()
    add_event(report_id, "REFUND SENT")

    await update.message.reply_text(
        f"refund receipt received for report {report['report_number']} and sent to buyer."
    )

    await context.bot.send_message(
        chat_id=report["buyer_id"],
        text=(
            f"report number: {report['report_number']}\n\n"
            "refund sent.\n"
            "proof of refund is attached below."
        ),
    )

    try:
        await update.message.forward(
            chat_id=report["buyer_id"],
        )
    except Exception as exc:
        logger.warning("Could not forward refund receipt: %s", exc)

    clear_session(OWNER_ID)

async def warning_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    set_session(OWNER_ID, stage="awaiting_warning_reason", report_id=report_id)

    await query.message.reply_text(
        "send the reason for the warning.\n\n"
        "the reason you send will be sent to the buyer."
    )

async def voided_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    set_session(OWNER_ID, stage="awaiting_voided_reason", report_id=report_id)

    await query.message.reply_text(
        "send the reason why the report is voided.\n\n"
        "the reason you send will be sent to the buyer."
    )

async def owner_reason_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update) or not update.message or not update.message.text:
        return

    session = get_session(OWNER_ID)
    if not session:
        return

    stage = session["stage"]
    if stage not in ("awaiting_warning_reason", "awaiting_voided_reason"):
        return

    report_id = session["report_id"]
    reason = update.message.text.strip()
    report = get_report(report_id)

    if not report:
        clear_session(OWNER_ID)
        await update.message.reply_text("report not found.")
        return

    if stage == "awaiting_warning_reason":
        status = "WARNING"
        label = "warning"
        event = "WARNING"
    else:
        status = "VOIDED"
        label = "voided"
        event = "VOIDED"

    conn = db()
    conn.execute(
        "UPDATE reports SET status=? WHERE id=?",
        (status, report_id),
    )
    conn.commit()
    conn.close()

    add_event(report_id, event, reason)

    await notify_buyer(
        context,
        report,
        f"""report number: {report['report_number']}

{label}, wrong details/format.

reason: {reason}""",
    )

    await update.message.reply_text(
        f"{label} reason sent to buyer for report {report['report_number']}."
    )
    clear_session(OWNER_ID)

# ============================================================
# FOR REFUND REASON
# ============================================================

async def trigger_for_refund(report_id, context, query_message=None):
    report = get_report(report_id)
    if not report:
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='FOR REFUND' WHERE id=?",
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_event(report_id, "FOR REFUND")

    await context.bot.send_message(
        chat_id=report["buyer_id"],
        text=(
            f"report number: {report['report_number']}\n\n"
            "FOR REFUND\n\n"
            "please choose the reason below and fill out the refund form."
        ),
        reply_markup=refund_reason_keyboard(report_id),
    )

    if query_message:
        await query_message.reply_text(
            f"report {report['report_number']} marked as FOR REFUND."
        )

async def refund_reason_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    report_id = int(query.data.split(":")[-1])
    report = get_report(report_id)
    if not report or report["buyer_id"] != query.from_user.id:
        return

    reason_key = query.data.split(":")[1]
    reason = "can't be fixed" if reason_key == "refund_reason_fixed" else "can't be replaced"

    set_session(
        query.from_user.id,
        stage="awaiting_refund_form",
        report_id=report_id,
        extra=reason,
    )

    await query.message.reply_text(
        f"refund reason: {reason}\n\n"
        "refund form:\n\n"
        "report number:\n"
        "date purchased:\n"
        "date reported:\n"
        "amount paid:\n"
        "account/product:\n"
        "days availed:\n"
        "user's bank details:\n\n"
        "send the completed refund form in one bubble chat only."
    )

async def refund_form_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message or not update.message.text:
        return

    session = get_session(user.id)
    if not session or session["stage"] != "awaiting_refund_form":
        return

    text = update.message.text.strip()
    lower = text.lower()

    required = [
        "report number",
        "date purchased",
        "date reported",
        "amount paid",
        "account/product",
        "days availed",
"user's bank details",
    ]
    missing = [x for x in required if x not in lower]

    if missing:
        await update.message.reply_text(
            "refund form is incomplete.\n\n"
            f"missing: {', '.join(missing)}"
        )
        return

    report = get_report(session["report_id"])
    if not report:
        clear_session(user.id)
        return

    bank_details = extract_field(text, "user's bank details")

    conn = db()
    conn.execute(
        "UPDATE reports SET status='REFUND FORM RECEIVED' WHERE id=?",
        (report["id"],),
    )
    conn.commit()
    conn.close()

    add_event(report["id"], "REFUND FORM RECEIVED", session["extra"] or "")

    await update.message.reply_text(
        f"refund form received for report {report['report_number']}.\n\n"
        "please send your proof of payment/receipt conversation if required."
    )

    # Send refund details to owner.
    current = get_report(report["id"])
    refund_display = current["refund_amount"] or "manual review required"

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=f"""REFUND REQUEST

report number: {current['report_number']}
refund reason: {session['extra'] or 'not specified'}

buyer: {current['buyer_username'] or 'no username'}
buyer user id: {current['buyer_id']}

date purchased: {current['date_purchased']}
date reported: {current['date_reported']}
remaining days: {current['remaining_days']}
amount paid: {current['amount_paid']}
amount to be refunded: {refund_display}

buyer's bank details:
{bank_details}

refund computation:
amount paid ÷ validity days × remaining days × service fee = refund

service fee multiplier used:
{current['refund_multiplier'] or 'manual review required'}"""
    )

    clear_session(user.id)

# ============================================================
# WARRANTY SESSION SETUP
# ============================================================

async def buyer_any_photo_or_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Routes non-text buyer messages when they are waiting for warranty proof.
    """
    user = update.effective_user
    if not user:
        return

    session = get_session(user.id)
    if session and session["stage"] == "awaiting_warranty_proof":
        await warranty_proof_message(update, context)
        return

# ============================================================
# MANUAL OWNER REPLY
# ============================================================

async def reply_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)
    if not report:
        await query.message.reply_text("report not found.")
        return

    set_session(
        OWNER_ID,
        stage="awaiting_manual_reply",
        report_id=report_id,
    )

    await query.message.reply_text(
        f"type the message you want to send to buyer of report {report['report_number']}."
    )

async def owner_manual_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update) or not update.message or not update.message.text:
        return

    session = get_session(OWNER_ID)
    if not session or session["stage"] != "awaiting_manual_reply":
        return

    report = get_report(session["report_id"])
    if not report:
        clear_session(OWNER_ID)
        await update.message.reply_text("report not found.")
        return

    await notify_buyer(
        context,
        report,
        f"message from seller:\n\n{update.message.text}",
    )

    await update.message.reply_text(
        f"your message was sent to buyer for report {report['report_number']}."
    )
    clear_session(OWNER_ID)

async def owner_reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "usage:\n/reply REPORT-NUMBER your message here"
        )
        return

    report_number = context.args[0]
    message = " ".join(context.args[1:])
    report = get_report_by_number(report_number)

    if not report:
        await update.message.reply_text("report number not found.")
        return

    await notify_buyer(
        context,
        report,
        f"message from seller:\n\n{message}",
    )

    await update.message.reply_text(
        f"message sent to buyer for report {report_number}."
    )

# ============================================================
# OWNER FORWARD / REPORT COMMANDS
# ============================================================

async def owner_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return

    if not context.args:
        await update.message.reply_text("usage: /report REPORT-NUMBER")
        return

    report = get_report_by_number(context.args[0])
    if not report:
        await update.message.reply_text("report number not found.")
        return

    await update.message.reply_text(
        seller_report_text(report),
        reply_markup=seller_report_keyboard(report["id"]),
    )

# ============================================================
# WARRANTY TIMEOUT CHECK
# ============================================================

async def warranty_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Every minute, check buyers whose account was fixed and whose
    six-hour warranty-proof window has expired.

    The exact timestamp is stored in report_events.
    If expired, the report is marked WARRANTY VOIDED.
    """
    now = datetime.now()

    conn = db()
    rows = conn.execute(
        """
        SELECT r.*, e.created_at AS fixed_at
        FROM reports r
        JOIN (
            SELECT report_id, MAX(created_at) AS created_at
            FROM report_events
            WHERE event='ACCOUNT FIXED'
            GROUP BY report_id
        ) e ON e.report_id=r.id
        WHERE r.status='ACCOUNT FIXED'
        """
    ).fetchall()
    conn.close()

    for report in rows:
        try:
            fixed_at = datetime.fromisoformat(report["fixed_at"])
        except Exception:
            continue

        if now >= fixed_at + timedelta(hours=6):
            conn = db()
            conn.execute(
                "UPDATE reports SET status='WARRANTY VOIDED' WHERE id=?",
                (report["id"],),
            )
            conn.commit()
            conn.close()

            add_event(report["id"], "WARRANTY VOIDED", "proof of log in not received within six hours")

            try:
                await notify_buyer(
                    context,
                    report,
                    f"""report number: {report['report_number']}

warranty voided.

proof of log in was not received within six hours.""",
                )
            except Exception as exc:
                logger.warning("Could not notify buyer of warranty timeout: %s", exc)

# ============================================================
# OWNER ACTION TO FORCE FOR REFUND
# ============================================================

async def owner_refund_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not owner_only(update):
        return

    if not context.args:
        await update.message.reply_text("usage: /forrefund REPORT-NUMBER")
        return

    report = get_report_by_number(context.args[0])
    if not report:
        await update.message.reply_text("report number not found.")
        return

    await trigger_for_refund(report["id"], context, update.message)

# ============================================================
# GENERIC MESSAGE ROUTER
# ============================================================

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    # Owner-specific states first.
    if user.id == OWNER_ID:
        session = get_session(OWNER_ID)
        if session:
            stage = session["stage"]
            if stage == "awaiting_refund_receipt":
                await owner_refund_receipt(update, context)
                return
            if stage in ("awaiting_warning_reason", "awaiting_voided_reason"):
                await owner_reason_message(update, context)
                return
            if stage == "awaiting_manual_reply":
                await owner_manual_reply(update, context)
                return

    # Buyer form/refund/warranty states.
    session = get_session(user.id)
    if not session:
        return

    stage = session["stage"]

    if stage == "awaiting_form":
        await buyer_form_message(update, context)
    elif stage in ("awaiting_proof_issue", "awaiting_proof_vouch", "awaiting_proof_payment"):
        # Text proofs are accepted too.
        await buyer_proof_message(update, context)
    elif stage == "awaiting_refund_form":
await refund_form_message(update, context)

# ============================================================
# PHOTO/DOCUMENT ROUTER
# ============================================================

async def media_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    session = get_session(user.id)
    if not session:
        return

    stage = session["stage"]

    if stage == "awaiting_proof_issue":
        set_session(
            user.id,
            category=session["category"],
            stage="awaiting_proof_vouch",
            form_message=session["form_message"],
        )
        await update.message.reply_text(
            "proof of issue received.\n\nplease send your screenshot of proof of vouch."
        )
        return

    if stage == "awaiting_proof_vouch":
        set_session(
            user.id,
            category=session["category"],
            stage="awaiting_proof_payment",
            form_message=session["form_message"],
        )
        await update.message.reply_text(
            "proof of vouch received.\n\nplease send your proof of payment that shows the amount paid."
        )
        return

    if stage == "awaiting_proof_payment":
        await buyer_proof_message(update, context)
        return

    if stage == "awaiting_warranty_proof":
        await warranty_proof_message(update, context)
        return

# ============================================================
# POST-SUBMIT PROOF FORWARDING FIX
# ============================================================

# We need to keep proof issue/vouch message IDs before submit.
# This handler records them in the temporary session's extra JSON.
import json

def update_session_extra(user_id, **kwargs):
    session = get_session(user_id)
    data = {}
    if session and session["extra"]:
        try:
            data = json.loads(session["extra"])
        except Exception:
            data = {}
    data.update(kwargs)

    set_session(
        user_id,
        category=session["category"] if session else None,
        stage=session["stage"] if session else None,
        form_message=session["form_message"] if session else None,
        report_id=session["report_id"] if session else None,
        extra=json.dumps(data),
    )

# Override the earlier proof behavior with ID tracking.
async def tracked_media_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    session = get_session(user.id)
    if not session:
        return

    stage = session["stage"]

    if stage == "awaiting_proof_issue":
        update_session_extra(user.id, proof_issue=update.message.message_id)
        set_session(
            user.id,
            category=session["category"],
            stage="awaiting_proof_vouch",
            form_message=session["form_message"],
            extra=json.dumps({"proof_issue": update.message.message_id}),
        )
        await update.message.reply_text(
            "proof of issue received.\n\nplease send your screenshot of proof of vouch."
        )
        return

    if stage == "awaiting_proof_vouch":
        extra = {}
        try:
            extra = json.loads(session["extra"] or "{}")
        except Exception:
            pass
        extra["proof_vouch"] = update.message.message_id

        set_session(
            user.id,
            category=session["category"],
            stage="awaiting_proof_payment",
            form_message=session["form_message"],
            extra=json.dumps(extra),
        )
        await update.message.reply_text(
            "proof of vouch received.\n\nplease send your proof of payment that shows the amount paid."
        )
        return

    if stage == "awaiting_proof_payment":
        await create_draft_from_payment(update, context)
        return

    if stage == "awaiting_warranty_proof":
        await warranty_proof_message(update, context)
        return

async def create_draft_from_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    session = get_session(user.id)

    category = session["category"]
    form_text = session["form_message"]
    days = extract_days(form_text)
    amount = extract_amount(form_text)
    purchased = parse_date_value(form_text)
    reported = date.today()

    remaining = calculate_remaining_days(purchased, days)
    refund, multiplier, manual, _ = calculate_refund(
        amount, days, remaining
    )

    extra = {}
    try:
        extra = json.loads(session["extra"] or "{}")
    except Exception:
        pass

    conn = db()
    cur = conn.execute(
        """
        INSERT INTO reports(
            report_number,buyer_id,buyer_username,category,form_text,
            date_purchased,date_reported,days_availed,amount_paid,
            remaining_days,refund_amount,refund_multiplier,refund_manual,
            status,proof_issue_message_id,proof_vouch_message_id,
            proof_payment_message_id,created_at
        )
        VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user.id,
            f"@{user.username}" if user.username else "",
            category,
            form_text,
            purchased.isoformat(),
            reported.isoformat(),
            days,
            str(amount),
            remaining,
            str(refund) if refund is not None else None,
            str(multiplier) if multiplier is not None else None,
            1 if manual else 0,
            "DRAFT",
            extra.get("proof_issue"),
            extra.get("proof_vouch"),
            update.message.message_id,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    report_id = cur.lastrowid
    report_number = f"LR-{report_id:05d}"
    conn.execute(
        "UPDATE reports SET report_number=? WHERE id=?",
        (report_number, report_id),
    )
    conn.commit()
    conn.close()

    set_session(
        user.id,
        category=category,
        stage="awaiting_submit",
        form_message=form_text,
        report_id=report_id,
        extra=json.dumps({
            "proof_issue": extra.get("proof_issue"),
            "proof_vouch": extra.get("proof_vouch"),
            "proof_payment": update.message.message_id,
        }),
    )

    await update.message.reply_text(
        f"proof of payment received.\n\n"
        f"report number: {report_number}\n\n"
        "please review your report and click submit.",
        reply_markup=submit_keyboard(report_id),
    )

# ============================================================
# REPLACE SUBMIT HANDLER WITH FULL PROOF FORWARDING
# ============================================================

async def submit_callback_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)

    if not report or report["buyer_id"] != query.from_user.id:
        await query.message.reply_text("this report does not belong to your account.")
        return

    if report["status"] != "DRAFT":
        await query.message.reply_text("this report has already been submitted.")
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='SUBMITTED' WHERE id=?",
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_event(report_id, "SUBMITTED")

    report = get_report(report_id)

    await query.message.reply_text(
        f"""report submitted successfully.

report number: {report['report_number']}
status: SUBMITTED

please wait 0–7 days fixing days.

if the issue cannot be fixed after the fixing period, the report may proceed to FOR REFUND."""
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=seller_report_text(report),
        reply_markup=seller_report_keyboard(report_id),
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=(
            f"category: {report['category']}\n"
            f"report number: {report['report_number']}\n\n"
            f"buyer form:\n{report['form_text']}"
        ),
    )

    for field, label in [
        ("proof_issue_message_id", "proof of issue"),
        ("proof_vouch_message_id", "proof of vouch"),
        ("proof_payment_message_id", "proof of payment"),
    ]:
        msg_id = report[field]
        if msg_id:
            try:
                await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=f"{label} — report {report['report_number']}",
                )
                await context.bot.forward_message(
                    chat_id=OWNER_ID,
                    from_chat_id=report["buyer_id"],
                    message_id=msg_id,
                )
            except Exception as exc:
                logger.warning("Could not forward %s: %s", label, exc)

    clear_session(query.from_user.id)

# ============================================================
# PATCH FIXED CALLBACK TO SET WARRANTY SESSION
# ============================================================

async def fixed_callback_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not owner_only(update):
        return

    report_id = int(query.data.split(":", 1)[1])
    report = get_report(report_id)
    if not report:
        await query.message.reply_text("report not found.")
        return

    conn = db()
    conn.execute(
        "UPDATE reports SET status='ACCOUNT FIXED' WHERE id=?",
        (report_id,),
    )
    conn.commit()
    conn.close()
    add_event(report_id, "ACCOUNT FIXED")

    await notify_buyer(
        context,
        report,
        f"""report number: {report['report_number']}

same account fixed.

kindly send proof of log in within six hours to activate warranty.""",
    )

    # The buyer's six-hour proof stage.
    set_session(
        report["buyer_id"],
        stage="awaiting_warranty_proof",
        report_id=report_id,
    )

    await query.message.reply_text(
        f"report {report['report_number']} marked as ACCOUNT FIXED.\n"
        "waiting for buyer's proof of log in within six hours."
    )

# ============================================================
# APP
# ============================================================

def build_app():
    if BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "Please put your Telegram bot token in BOT_TOKEN or set the BOT_TOKEN environment variable."
        )

    if OWNER_ID == 123456789:
        logger.warning(
            "OWNER_ID is still 123456789. Replace it with your real Telegram numeric user ID."
        )

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reply", owner_reply_command))
    app.add_handler(CommandHandler("report", owner_report_command))
    app.add_handler(CommandHandler("forrefund", owner_refund_command))

    # Category buttons.
    app.add_handler(
        CallbackQueryHandler(category_callback, pattern=r"^cat:")
    )

    # Submit button.
    app.add_handler(
        CallbackQueryHandler(submit_callback_full, pattern=r"^submit:")
    )

    # Seller action buttons.
    app.add_handler(
        CallbackQueryHandler(fixed_callback_full, pattern=r"^fixed:")
    )
    app.add_handler(
        CallbackQueryHandler(replaced_callback, pattern=r"^replaced:")
    )
    app.add_handler(
        CallbackQueryHandler(refund_sent_callback, pattern=r"^refund_sent:")
    )
    app.add_handler(
        CallbackQueryHandler(warning_callback, pattern=r"^warning:")
    )
    app.add_handler(
        CallbackQueryHandler(voided_callback, pattern=r"^voided:")
    )
    app.add_handler(
        CallbackQueryHandler(reply_button_callback, pattern=r"^reply:")
    )

    # Warranty buttons.
    app.add_handler(
        CallbackQueryHandler(warranty_yes_callback, pattern=r"^warranty_yes:")
    )
    app.add_handler(
        CallbackQueryHandler(warranty_no_callback, pattern=r"^warranty_no:")
    )

    # Refund reason buttons.
    app.add_handler(
        CallbackQueryHandler(
            refund_reason_callback,
            pattern=r"^refund_reason_(fixed|replaced):",
        )
    )

    # Media before generic text.
    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.ALL,
            tracked_media_router,
        )
    )

    # Generic text.
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            text_router,
        )
    )

    # Warranty timeout checker.
    if app.job_queue:
        app.job_queue.run_repeating(
            warranty_timeout_job,
            interval=60,
            first=10,
        )
    else:
        logger.warning(
            "JobQueue is unavailable. Install python-telegram-bot[job-queue] "
            "from requirements.txt for the six-hour automatic warranty timeout."
        )

    return app

def main():
    app = build_app()
    logger.info("lanayanaliv report bot is running.")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )

if __name__ == "__main__":
    main()
