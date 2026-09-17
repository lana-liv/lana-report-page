import os
import re
import sqlite3
import logging
import asyncio
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
)


BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])

TUTORIAL_URL = "https://t.me/lanareports"
DB_FILE = os.getenv("DB_FILE", "report_bot.db")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("lanayanaliv_report_bot")

(
    CHOOSING_CATEGORY,
    ENTERING_FORM,
    WAITING_ISSUE_PROOF,
    WAITING_VOUCH_PROOF,
    WAITING_SUBMIT,
    REFUND_REASON,
    REFUND_FORM,
    WAITING_PAYMENT_PROOF,
) = range(8)


def db_connect():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db_connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_no TEXT UNIQUE,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            category TEXT NOT NULL,
            raw_form TEXT NOT NULL,
            product TEXT,
            amount_paid REAL,
            days_availed INTEGER,
            date_purchased TEXT,
            date_reported TEXT,
            subscription_remaining INTEGER,
            status TEXT NOT NULL,
            issue_proof_file_id TEXT,
            issue_proof_type TEXT,
            vouch_proof_file_id TEXT,
            vouch_proof_type TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            fixing_deadline TEXT,
            owner_note TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS refunds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            report_no TEXT NOT NULL,
            reason TEXT,
            refund_form TEXT NOT NULL,
            amount_paid REAL,
            validity_days INTEGER,
            remaining_days INTEGER,
            service_fee REAL,
            refund_amount REAL,
            bank_details TEXT,
            payment_proof_file_id TEXT,
            payment_proof_type TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(report_id) REFERENCES reports(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            report_no TEXT NOT NULL,
            last_contact_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_rules (
            user_id INTEGER PRIMARY KEY,
            mistake_count INTEGER DEFAULT 0,
            direct_owner_count INTEGER DEFAULT 0,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today_text():
    return date.today().strftime("%Y-%m-%d")


def get_report(report_no: str):
    conn = db_connect()
    row = conn.execute(
        "SELECT * FROM reports WHERE report_no = ?",
        (report_no.upper(),)
    ).fetchone()
    conn.close()
    return row


def get_report_by_id(report_id: int):
    conn = db_connect()
    row = conn.execute(
        "SELECT * FROM reports WHERE id = ?",
        (report_id,)
    ).fetchone()
    conn.close()
    return row


def save_report(data):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports (
            report_no, user_id, username, first_name, category, raw_form,
            product, amount_paid, days_availed, date_purchased,
            date_reported, subscription_remaining, status,
            issue_proof_file_id, issue_proof_type,
            vouch_proof_file_id, vouch_proof_type,
            created_at, updated_at, fixing_deadline, owner_note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["report_no"],
        data["user_id"],
        data["username"],
        data["first_name"],
        data["category"],
        data["raw_form"],
        data.get("product"),
        data.get("amount_paid"),
        data.get("days_availed"),
        data.get("date_purchased"),
        data.get("date_reported"),
        data.get("subscription_remaining"),
        data.get("status", "SUBMITTED"),
        data.get("issue_proof_file_id"),
        data.get("issue_proof_type"),
        data.get("vouch_proof_file_id"),
        data.get("vouch_proof_type"),
        now_text(),
        now_text(),
        data.get("fixing_deadline"),
        data.get("owner_note"),
    ))
    report_id = cur.lastrowid
    conn.commit()
    conn.close()
    return report_id


def update_report(report_no, **fields):
    if not fields:
        return

    allowed = {
        "status",
        "issue_proof_file_id",
        "issue_proof_type",
        "vouch_proof_file_id",
        "vouch_proof_type",
        "subscription_remaining",
        "fixing_deadline",
        "owner_note",
        "updated_at",
    }

    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return

    fields["updated_at"] = now_text()
    set_sql = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [report_no.upper()]

    conn = db_connect()
    conn.execute(
        f"UPDATE reports SET {set_sql} WHERE report_no = ?",
        values
    )
    conn.commit()
    conn.close()


def next_report_number():
    conn = db_connect()
    row = conn.execute(
        "SELECT id FROM reports ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()

    next_id = (row["id"] + 1) if row else 1
    return f"RPT-{next_id:04d}"


def save_user_report(user_id, report_no):
    conn = db_connect()
    conn.execute(
        "INSERT INTO user_reports (user_id, report_no, last_contact_at) VALUES (?, ?, ?)",
        (user_id, report_no, now_text())
    )
    conn.commit()
    conn.close()


def get_latest_report_for_user(user_id):
    conn = db_connect()
    row = conn.execute("""
        SELECT r.*
        FROM reports r
        WHERE r.user_id = ?
        ORDER BY r.id DESC
        LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()
    return row


def get_or_create_rule(user_id):
    conn = db_connect()
    row = conn.execute(
        "SELECT * FROM user_rules WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    if row:
        conn.close()
        return row

    conn.execute(
        "INSERT INTO user_rules (user_id, mistake_count, direct_owner_count, updated_at) VALUES (?, 0, 0, ?)",
        (user_id, now_text())
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM user_rules WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row


def increment_mistake(user_id):
    conn = db_connect()
    conn.execute("""
        INSERT INTO user_rules (user_id, mistake_count, direct_owner_count, updated_at)
        VALUES (?, 1, 0, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            mistake_count = mistake_count + 1,
            updated_at = excluded.updated_at
    """, (user_id, now_text()))
    conn.commit()
    row = conn.execute(
        "SELECT * FROM user_rules WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row


def increment_direct_owner(user_id):
    conn = db_connect()
    conn.execute("""
        INSERT INTO user_rules (user_id, mistake_count, direct_owner_count, updated_at)
        VALUES (?, 0, 1, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            direct_owner_count = direct_owner_count + 1,
            updated_at = excluded.updated_at
    """, (user_id, now_text()))
    conn.commit()
    row = conn.execute(
        "SELECT * FROM user_rules WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return row


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d.%m.%Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
]


def parse_date(value: str) -> Optional[date]:
    if not value:
        return None

    value = value.strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    match = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", value)
    if match:
        d, m, y = map(int, match.groups())
        try:
            return date(y, m, d)
        except ValueError:
            pass

    match = re.search(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b", value)
    if match:
        y, m, d = map(int, match.groups())
        try:
            return date(y, m, d)
        except ValueError:
            pass

    return None


def normalize_date(value: str) -> Optional[str]:
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else None


def parse_money(value: str) -> Optional[float]:
    if not value:
        return None

    cleaned = value.replace(",", "")
    match = re.search(r"(\d+(?:\.\d{1,2})?)", cleaned)
    if not match:
        return None

    try:
        return float(match.group(1))
    except ValueError:
        return None


def parse_days(value: str) -> Optional[int]:
    if not value:
        return None

    match = re.search(r"\b(\d{1,4})\b", value)
    if not match:
        return None

    try:
        days = int(match.group(1))
        if 0 < days <= 3660:
            return days
    except ValueError:
        pass

    return None


def calculate_remaining(date_purchased: Optional[date], validity_days: Optional[int], report_date: Optional[date] = None):
    if not date_purchased or not validity_days:
        return None

    report_date = report_date or date.today()
    expiry = date_purchased + timedelta(days=validity_days)
    remaining = (expiry - report_date).days

    return max(0, remaining)


def get_lines(text):
    return [line.strip() for line in text.splitlines() if line.strip()]


def value_after_labels(text, labels):
    for line in get_lines(text):
        lower = line.lower()
        for label in labels:
            if lower.startswith(label.lower()):
                value = line[len(label):].strip(" :|-")
                if value:
                    return value
    return None


def parse_report_form(category, text):
    category = category.lower()

    result = {
        "product": None,
        "amount_paid": None,
        "days_availed": None,
        "date_purchased": None,
        "date_reported": None,
    }

    if category == "entertainment":
        product = value_after_labels(text, [
            "what premium", "premium", "what premium account"
        ])
        email = value_after_labels(text, [
            "email/number", "email", "number"
        ])
        password = value_after_labels(text, ["password"])
        profile_pin = value_after_labels(text, [
            "profile and pin", "profile", "pin"
        ])
        days = value_after_labels(text, ["days availed", "days"])
        shared = value_after_labels(text, [
            "shared/slp or sla", "shared/slp", "slp", "sla"
        ])
        purchased = value_after_labels(text, [
            "date purchased", "date purchase", "purchase date"
        ])
        amount = value_after_labels(text, [
            "amount paid", "amount"
        ])
        issue = value_after_labels(text, [
            "specific issue", "issue"
        ])

        result.update({
            "product": product,
            "email": email,
            "password": password,
            "profile_pin": profile_pin,
            "days_availed": parse_days(days),
            "sharing": shared,
            "date_purchased": normalize_date(purchased) if purchased else None,
            "amount_paid": parse_money(amount),
            "specific_issue": issue,
        })

    elif category in ("editing", "educational"):
        product = value_after_labels(text, [
            "what premium", "premium"
        ])
        email = value_after_labels(text, [
            "email/number", "email", "number"
        ])
        password = value_after_labels(text, ["password"])
        days = value_after_labels(text, ["days availed", "days"])
        shared = value_after_labels(text, [
            "shared/sla", "shared", "sla"
        ])
        purchased = value_after_labels(text, [
            "date purchased", "purchase date"
        ])
        amount = value_after_labels(text, [
            "amount paid", "amount"
        ])
        issue = value_after_labels(text, [
            "specific issue", "issue"
        ])

        result.update({
            "product": product,
            "email": email,
            "password": password,
            "days_availed": parse_days(days),
            "sharing": shared,
            "date_purchased": normalize_date(purchased) if purchased else None,
            "amount_paid": parse_money(amount),
            "specific_issue": issue,
        })

    else:
        product = value_after_labels(text, [
            "what product", "product"
        ])
        product_info = value_after_labels(text, [
            "product information", "product info"
        ])
        days = value_after_labels(text, ["days availed", "days"])
        purchased = value_after_labels(text, [
            "date purchased", "purchase date"
        ])
        reported = value_after_labels(text, [
            "date reported", "report date"
        ])
        amount = value_after_labels(text, [
            "amount paid", "amount"
        ])
        issue = value_after_labels(text, [
            "specific issue", "issue"
        ])

        result.update({
            "product": product,
            "product_information": product_info,
            "days_availed": parse_days(days),
            "date_purchased": normalize_date(purchased) if purchased else None,
            "date_reported": normalize_date(reported) if reported else None,
            "amount_paid": parse_money(amount),
            "specific_issue": issue,
        })

    return result


def form_is_parseable(parsed, category):
    required = [
        parsed.get("days_availed"),
        parsed.get("amount_paid"),
        parsed.get("date_purchased"),
    ]

    return all(x is not None for x in required)


REFUND_TIERS = {
    30: [
        (30, 30, 1.00),
        (25, 29, 0.80),
        (20, 24, 0.70),
        (15, 19, 0.60),
        (10, 14, 0.50),
        (6, 9, 0.40),
    ],
    60: [
        (60, 60, 1.00),
        (55, 59, 0.80),
        (45, 54, 0.70),
        (35, 44, 0.60),
        (25, 34, 0.50),
        (15, 24, 0.40),
        (7, 14, 0.30),
    ],
    90: [
        (90, 90, 1.00),
        (78, 89, 0.80),
        (69, 77, 0.70),
        (59, 68, 0.60),
        (49, 58, 0.50),
        (39, 48, 0.40),
        (29, 38, 0.30),
        (19, 28, 0.20),
        (7, 18, 0.10),
    ],
    120: [
        (120, 120, 1.00),
        (110, 119, 0.80),
        (95, 109, 0.70),
        (80, 94, 0.60),
        (60, 79, 0.50),
        (49, 59, 0.40),
        (35, 48, 0.30),
        (20, 34, 0.20),
        (8, 19, 0.10),
    ],
    150: [
        (150, 150, 1.00),
        (130, 149, 0.80),
        (110, 129, 0.70),
        (90, 109, 0.60),
        (70, 89, 0.50),
        (50, 69, 0.40),
        (30, 49, 0.30),
        (15, 29, 0.20),
        (11, 14, 0.10),
    ],
    180: [
        (180, 180, 1.00),
        (150, 179, 0.80),
        (120, 149, 0.70),
        (90, 119, 0.60),
        (70, 89, 0.50),
        (50, 69, 0.40),
        (30, 49, 0.30),
        (15, 29, 0.20),
        (11, 14, 0.10),
    ],
    360: [
        (360, 360, 1.00),
        (340, 359, 0.80),
        (320, 339, 0.70),
        (300, 319, 0.60),
        (250, 299, 0.50),
        (200, 249, 0.40),
        (150, 199, 0.30),
        (100, 149, 0.20),
        (50, 99, 0.10),
        (11, 49, 0.05),
    ],
}


def refund_tier_for_validity(validity_days, remaining_days):
    if validity_days is None or remaining_days is None:
        return 0.0

    if validity_days <= 30:
        tiers = REFUND_TIERS[30]
    elif validity_days <= 60:
        tiers = REFUND_TIERS[60]
    elif validity_days <= 90:
        tiers = REFUND_TIERS[90]
    elif validity_days <= 120:
        tiers = REFUND_TIERS[120]
    elif validity_days <= 150:
        tiers = REFUND_TIERS[150]
    elif validity_days <= 180:
        tiers = REFUND_TIERS[180]
    elif validity_days <= 360:
        tiers = REFUND_TIERS[360]
    else:
        return 0.0

    for low, high, multiplier in tiers:
        if low <= remaining_days <= high:
            return multiplier

    return 0.0


def calculate_refund(amount_paid, validity_days, remaining_days):
    if not amount_paid or not validity_days or remaining_days is None:
        return {
            "service_fee": 0.0,
            "refund": 0.0,
        }

    multiplier = refund_tier_for_validity(validity_days, remaining_days)
    refund = (amount_paid / validity_days) * remaining_days * multiplier

    return {
        "service_fee": multiplier,
        "refund": round(refund, 2),
    }


WELCOME_TEXT = """welcome to lanayanaliv's report page!

━━━━━━━━⊱⋆⊰━━━━━━━━

guide:

1. copy the form based on what premium account you're gonna report and send it here in one bubble chat only [please remember that there will be a reply that you need to send your proofs if you sent the correct format]
2. send the screenshot of your proof of issue and proof of vouch
3. click "submit"

terms to remember:

slp = solo profile [one device/two devices]
sla = solo account
specific issue: ano yung nangyari? bakit ka nag re-report?

────────────────────

first mistake and first direct to owner report = warning
second mistake and second direct to owner report = voided
"""

CATEGORY_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Entertainment", callback_data="cat:Entertainment"),
        InlineKeyboardButton("Editing", callback_data="cat:Editing"),
    ],
    [
        InlineKeyboardButton("Educational", callback_data="cat:Educational"),
        InlineKeyboardButton("Others", callback_data="cat:Others"),
    ],
    [
        InlineKeyboardButton("Report Tutorial", url=TUTORIAL_URL),
    ],
])

FORMS = {
    "Entertainment": """entertainment report form

what premium:
email/number:
password:
profile and pin:
days availed:
shared/slp or sla:
date purchased:
amount paid:
specific issue:

send the completed form in one bubble chat only.""",

    "Editing": """editing report form

what premium:
email/number:
password:
days availed:
shared/sla:
date purchased:
amount paid:
specific issue:

send the completed form in one bubble chat only.""",

    "Educational": """educational report form

what premium:
email/number:
password:
days availed:
shared/sla:
date purchased:
amount paid:
specific issue:

send the completed form in one bubble chat only.""",

    "Others": """general report form

what product:
product information:
days availed:
date purchased:
date reported:
amount paid:
specific issue:

send the completed form in one bubble chat only.""",
}


def report_submit_keyboard(report_no):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("submit", callback_data=f"submit:{report_no}")]
    ])


def refund_reason_keyboard(report_no):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("can't be fixed", callback_data=f"refundreason:{report_no}:cantfix")],
        [InlineKeyboardButton("can't be replaced", callback_data=f"refundreason:{report_no}:cantreplace")],
    ])


def owner_report_keyboard(report_no, user_id):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("account fixed", callback_data=f"fix:{report_no}"),
            InlineKeyboardButton("account replaced", callback_data=f"replace:{report_no}"),
        ],
        [
            InlineKeyboardButton("for refund", callback_data=f"forrefund:{report_no}"),
        ],
        [
            InlineKeyboardButton("reply", callback_data=f"reply:{report_no}:{user_id}"),
        ],
    ])


async def send_report_form(update, context, category):
    context.user_data["category"] = category
    context.user_data["state"] = "form"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(FORMS[category])
    else:
        await update.message.reply_text(FORMS[category])

    return ENTERING_FORM


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    if update.effective_chat:
        await update.effective_chat.send_message(
            WELCOME_TEXT,
            reply_markup=CATEGORY_KEYBOARD,
        )

    return CHOOSING_CATEGORY


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.split(":", 1)[1]
    return await send_report_form(update, context, category)


async def form_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    category = context.user_data.get("category")

    if not category:
        await update.message.reply_text(
            "please choose a report category first.",
            reply_markup=CATEGORY_KEYBOARD,
        )
        return CHOOSING_CATEGORY

    parsed = parse_report_form(category, text)

    context.user_data["raw_form"] = text
    context.user_data["parsed"] = parsed

    if not form_is_parseable(parsed, category):
        await update.message.reply_text(
            "please check your form and send it again in the correct format.\n\n"
            "i need the days availed, amount paid, and date purchased to calculate your subscription days remaining."
        )
        return ENTERING_FORM

    await update.message.reply_text(
        "form received.\n\n"
        "please send your proof of issue screenshot."
    )
    return WAITING_ISSUE_PROOF


async def issue_proof_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"

    if not file_id:
        await update.message.reply_text(
            "please send your proof of issue as a photo or document."
        )
        return WAITING_ISSUE_PROOF

    context.user_data["issue_proof_file_id"] = file_id
    context.user_data["issue_proof_type"] = file_type

    await update.message.reply_text(
        "proof of issue received.\n\n"
        "now send your proof of vouch screenshot."
    )
    return WAITING_VOUCH_PROOF


async def vouch_proof_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"

    if not file_id:
        await update.message.reply_text(
            "please send your proof of vouch as a photo or document."
        )
        return WAITING_VOUCH_PROOF

    context.user_data["vouch_proof_file_id"] = file_id
    context.user_data["vouch_proof_type"] = file_type

    parsed = context.user_data.get("parsed", {})
    purchased = parse_date(parsed.get("date_purchased", "")) if parsed.get("date_purchased") else None
    report_date = date.today()

    if parsed.get("date_reported"):
        parsed_report_date = parse_date(parsed["date_reported"])
        if parsed_report_date:
            report_date = parsed_report_date

    remaining = calculate_remaining(
        purchased,
        parsed.get("days_availed"),
        report_date,
    )

    context.user_data["remaining"] = remaining
    context.user_data["report_date"] = report_date.isoformat()

    await update.message.reply_text(
        "both proofs received.\n\n"
        "your report is ready to submit.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("submit", callback_data="submit_pending")]
        ])
    )
    return WAITING_SUBMIT


async def submit_pending_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    return await create_report_from_context(update, context)


async def create_report_from_context(update, context):
    user = update.effective_user
    category = context.user_data.get("category")
    raw_form = context.user_data.get("raw_form", "")
    parsed = context.user_data.get("parsed", {})

    if not category or not raw_form or not parsed:
        await update.effective_chat.send_message(
            "your report session expired. please start again with /start."
        )
        return ConversationHandler.END

    report_no = next_report_number()

    safe_form = raw_form
    safe_form = re.sub(r"(?im)^(\s*password\s*:\s*).*$", r"\1[redacted]", safe_form)

    purchased = parse_date(parsed.get("date_purchased", "")) if parsed.get("date_purchased") else None
    report_date = parse_date(context.user_data.get("report_date", "")) or date.today()
    validity = parsed.get("days_availed")
    remaining = calculate_remaining(purchased, validity, report_date)

    deadline = report_date + timedelta(days=7)

    data = {
        "report_no": report_no,
        "user_id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "category": category,
        "raw_form": safe_form,
        "product": parsed.get("product"),
        "amount_paid": parsed.get("amount_paid"),
        "days_availed": validity,
        "date_purchased": purchased.isoformat() if purchased else None,
        "date_reported": report_date.isoformat(),
        "subscription_remaining": remaining,
        "status": "SUBMITTED",
        "issue_proof_file_id": context.user_data.get("issue_proof_file_id"),
        "issue_proof_type": context.user_data.get("issue_proof_type"),
        "vouch_proof_file_id": context.user_data.get("vouch_proof_file_id"),
        "vouch_proof_type": context.user_data.get("vouch_proof_type"),
        "fixing_deadline": deadline.isoformat(),
    }

    report_id = save_report(data)
    save_user_report(user.id, report_no)

    buyer_text = (
        f"report submitted successfully.\n\n"
        f"report number: {report_no}\n"
        f"status: SUBMITTED\n"
        f"fixing period: 0–7 days\n"
        f"fixing deadline: {deadline.strftime('%B %d, %Y')}\n"
        f"subscription days remaining at report: {remaining if remaining is not None else 'not available'}\n\n"
        "please wait for an update. if the account/product cannot be fixed or replaced within the fixing period, the report may be moved to FOR REFUND."
    )

    await update.effective_chat.send_message(buyer_text)

    await notify_owner_about_report(context, get_report_by_id(report_id))

    context.user_data.clear()
    return ConversationHandler.END


def format_report_owner(row):
    remaining = row["subscription_remaining"]
    return (
        f"new report\n\n"
        f"report number: {row['report_no']}\n"
        f"buyer username: @{row['username'] if row['username'] else 'no_username'}\n"
        f"buyer user id: {row['user_id']}\n"
        f"category: {row['category']}\n"
        f"product: {row['product'] or 'not parsed'}\n"
        f"amount paid: ₱{row['amount_paid']:.2f}" if row["amount_paid"] is not None else
        f"new report\n\n"
        f"report number: {row['report_no']}\n"
        f"buyer username: @{row['username'] if row['username'] else 'no_username'}\n"
        f"buyer user id: {row['user_id']}\n"
        f"category: {row['category']}\n"
        f"product: {row['product'] or 'not parsed'}\n"
    )


def full_report_owner_text(row):
    amount = f"₱{row['amount_paid']:.2f}" if row['amount_paid'] is not None else "not parsed"
    return (
        f"new report\n\n"
        f"report number: {row['report_no']}\n"
        f"buyer username: @{row['username'] if row['username'] else 'no_username'}\n"
        f"buyer user id: {row['user_id']}\n"
        f"category: {row['category']}\n"
        f"product/premium: {row['product'] or 'not parsed'}\n"
        f"amount paid: {amount}\n"
        f"days availed: {row['days_availed'] if row['days_availed'] is not None else 'not parsed'}\n"
        f"date purchased: {row['date_purchased'] or 'not parsed'}\n"
        f"date reported: {row['date_reported'] or 'not parsed'}\n"
        f"subscription days remaining at report: {row['subscription_remaining'] if row['subscription_remaining'] is not None else 'not available'}\n"
        f"status: {row['status']}\n"
        f"fixing deadline: {row['fixing_deadline'] or 'not set'}\n\n"
        f"report form:\n{row['raw_form']}"
    )


async def notify_owner_about_report(context, row):
    if not row:
        return

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=full_report_owner_text(row),
        reply_markup=owner_report_keyboard(row["report_no"], row["user_id"]),
    )

    if row["issue_proof_file_id"]:
        try:
            if row["issue_proof_type"] == "photo":
                await context.bot.send_photo(
                    chat_id=OWNER_ID,
                    photo=row["issue_proof_file_id"],
                    caption=f"{row['report_no']} - proof of issue",
                )
            else:
                await context.bot.send_document(
                    chat_id=OWNER_ID,
                    document=row["issue_proof_file_id"],
                    caption=f"{row['report_no']} - proof of issue",
                )
        except Exception:
            logger.exception("Could not send issue proof.")

    if row["vouch_proof_file_id"]:
        try:
            if row["vouch_proof_type"] == "photo":
                await context.bot.send_photo(
                    chat_id=OWNER_ID,
                    photo=row["vouch_proof_file_id"],
                    caption=f"{row['report_no']} - proof of vouch",
                )
            else:
                await context.bot.send_document(
                    chat_id=OWNER_ID,
                    document=row["vouch_proof_file_id"],
                    caption=f"{row['report_no']} - proof of vouch",
                )
        except Exception:
            logger.exception("Could not send vouch proof.")


def owner_only(user_id):
    return user_id == OWNER_ID


async def owner_action(update, context, action):
    query = update.callback_query
    await query.answer()

    if not owner_only(update.effective_user.id):
        await query.message.reply_text("owner only.")
        return

    parts = query.data.split(":")
    report_no = parts[1]
    row = get_report(report_no)

    if not row:
        await query.message.reply_text("report not found.")
        return

    if action == "fix":
        update_report(report_no, status="ACCOUNT FIXED")
        await context.bot.send_message(
            row["user_id"],
            f"report {report_no} update:\n\nstatus: ACCOUNT FIXED"
        )
        await query.message.reply_text(f"{report_no} marked as ACCOUNT FIXED.")

    elif action == "replace":
        update_report(report_no, status="ACCOUNT REPLACED")
        await context.bot.send_message(
            row["user_id"],
            f"report {report_no} update:\n\nstatus: ACCOUNT REPLACED"
        )
        await query.message.reply_text(f"{report_no} marked as ACCOUNT REPLACED.")

    elif action == "forrefund":
        update_report(report_no, status="FOR REFUND")
        await context.bot.send_message(
            row["user_id"],
            f"report {report_no} update:\n\n"
            "status: FOR REFUND\n\n"
            "please choose your reason below, then fill out the refund form.",
            reply_markup=refund_reason_keyboard(report_no),
        )
        await query.message.reply_text(f"{report_no} marked as FOR REFUND.")

    await query.edit_message_reply_markup(reply_markup=None)


async def fix_callback(update, context):
    await owner_action(update, context, "fix")


async def replace_callback(update, context):
    await owner_action(update, context, "replace")


async def forrefund_callback(update, context):
    await owner_action(update, context, "forrefund")


async def reply_callback(update, context):
    query = update.callback_query
    await query.answer()

    if not owner_only(update.effective_user.id):
        return

    parts = query.data.split(":")
    report_no = parts[1]
    user_id = int(parts[2])

    context.user_data["reply_report_no"] = report_no
    context.user_data["reply_user_id"] = user_id

    await query.message.reply_text(
        f"reply mode for {report_no}.\n\n"
        "send your message now. your next message will be sent to the buyer."
    )


async def owner_text_message(update, context):
    if not owner_only(update.effective_user.id):
        return

    user_id = context.user_data.get("reply_user_id")
    report_no = context.user_data.get("reply_report_no")

    if not user_id or not report_no:
        return

    text = update.message.text
    if not text:
        await update.message.reply_text(
            "reply mode currently accepts text messages."
        )
        return

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"message from lanayanaliv regarding report {report_no}:\n\n{text}"
        )
        await update.message.reply_text(
            f"message sent to buyer for {report_no}."
        )
    except Exception as exc:
        await update.message.reply_text(
            f"could not send the message: {exc}"
        )

    context.user_data.pop("reply_user_id", None)
    context.user_data.pop("reply_report_no", None)


async def refund_reason_callback(update, context):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    report_no = parts[1]
    reason_code = parts[2]

    row = get_report(report_no)

    if not row or row["user_id"] != update.effective_user.id:
        await query.message.reply_text("this refund request does not belong to you.")
        return ConversationHandler.END

    reason = "can't be fixed" if reason_code == "cantfix" else "can't be replaced"

    context.user_data["refund_report_no"] = report_no
    context.user_data["refund_reason"] = reason

    await query.message.reply_text(
        f"reason selected: {reason}\n\n"
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

    return REFUND_FORM


async def refund_form_message(update, context):
    report_no = context.user_data.get("refund_report_no")
    row = get_report(report_no) if report_no else None

    if not row:
        await update.message.reply_text(
            "refund session expired. please contact the owner."
        )
        return ConversationHandler.END

    text = update.message.text or ""
    context.user_data["refund_form"] = text

    date_purchased = value_after_labels(text, [
        "date purchased", "purchase date"
    ])
    date_reported = value_after_labels(text, [
        "date reported", "report date"
    ])
    amount_paid = value_after_labels(text, [
        "amount paid", "amount"
    ])
    account_product = value_after_labels(text, [
        "account/product", "account", "product"
    ])
    days_availed = value_after_labels(text, [
        "days availed", "days"
    ])
    bank_details = value_after_labels(text, [
        "user's bank details", "users bank details",
        "bank details", "bank", "qr", "bank number"
    ])

    parsed = {
        "date_purchased": normalize_date(date_purchased) if date_purchased else row["date_purchased"],
        "date_reported": normalize_date(date_reported) if date_reported else row["date_reported"],
        "amount_paid": parse_money(amount_paid) if amount_paid else row["amount_paid"],
        "account_product": account_product or row["product"],
        "days_availed": parse_days(days_availed) if days_availed else row["days_availed"],
        "bank_details": bank_details,
    }

    purchased = parse_date(parsed["date_purchased"]) if parsed["date_purchased"] else None
    reported = parse_date(parsed["date_reported"]) if parsed["date_reported"] else date.today()

    remaining = calculate_remaining(
        purchased,
        parsed["days_availed"],
        reported,
    )

    calc = calculate_refund(
        parsed["amount_paid"],
        parsed["days_availed"],
        remaining,
    )

    context.user_data["refund_parsed"] = parsed
    context.user_data["refund_remaining"] = remaining
    context.user_data["refund_service_fee"] = calc["service_fee"]
    context.user_data["refund_amount"] = calc["refund"]

    await update.message.reply_text(
        "refund form received.\n\n"
        "please send your proof of payment screenshot.\n"
        "this can be your receipt or the payment conversation."
    )

    return WAITING_PAYMENT_PROOF


async def payment_proof_message(update, context):
    report_no = context.user_data.get("refund_report_no")
    row = get_report(report_no) if report_no else None

    if not row:
        await update.message.reply_text("refund session expired.")
        return ConversationHandler.END

    file_id = None
    file_type = None

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_type = "photo"
    elif update.message.document:
        file_id = update.message.document.file_id
        file_type = "document"

    if not file_id:
        await update.message.reply_text(
            "please send your proof of payment as a photo or document."
        )
        return WAITING_PAYMENT_PROOF

    parsed = context.user_data.get("refund_parsed", {})
    remaining = context.user_data.get("refund_remaining")
    service_fee = context.user_data.get("refund_service_fee", 0.0)
    refund_amount = context.user_data.get("refund_amount", 0.0)

    conn = db_connect()
    conn.execute("""
        INSERT INTO refunds (
            report_id, report_no, reason, refund_form,
            amount_paid, validity_days, remaining_days,
            service_fee, refund_amount, bank_details,
            payment_proof_file_id, payment_proof_type,
            status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row["id"],
        report_no,
        context.user_data.get("refund_reason", ""),
        context.user_data.get("refund_form", ""),
        parsed.get("amount_paid"),
        parsed.get("days_availed"),
        remaining,
        service_fee,
        refund_amount,
        parsed.get("bank_details"),
        file_id,
        file_type,
        "PENDING OWNER REVIEW",
        now_text(),
        now_text(),
    ))
    conn.commit()
    conn.close()

    update_report(report_no, status="FOR REFUND")

    buyer_text = (
        f"refund request submitted.\n\n"
        f"report number: {report_no}\n"
        f"reason: {context.user_data.get('refund_reason')}\n"
        f"remaining days: {remaining if remaining is not None else 'not available'}\n"
        f"service fee: {service_fee:.2f}\n"
        f"computed refund: ₱{refund_amount:.2f}\n\n"
        "your refund request and proof of payment have been sent to the owner for review."
    )

    await update.message.reply_text(buyer_text)

    owner_text = (
        f"refund request\n\n"
        f"report number: {report_no}\n"
        f"buyer username: @{row['username'] if row['username'] else 'no_username'}\n"
        f"buyer user id: {row['user_id']}\n"
        f"reason: {context.user_data.get('refund_reason')}\n"
        f"date purchased: {parsed.get('date_purchased') or 'not parsed'}\n"
        f"date reported: {parsed.get('date_reported') or 'not parsed'}\n"
        f"amount paid: ₱{parsed.get('amount_paid', 0):.2f}\n"
        f"account/product: {parsed.get('account_product') or 'not parsed'}\n"
        f"days availed: {parsed.get('days_availed') or 'not parsed'}\n"
        f"remaining days: {remaining if remaining is not None else 'not available'}\n"
        f"service fee: {service_fee:.2f}\n"
        f"computed refund: ₱{refund_amount:.2f}\n"
        f"bank details: {parsed.get('bank_details') or 'not provided'}\n"
        f"status: PENDING OWNER REVIEW"
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=owner_text,
    )

    try:
        if file_type == "photo":
            await context.bot.send_photo(
                chat_id=OWNER_ID,
                photo=file_id,
                caption=f"{report_no} - proof of payment",
            )
        else:
            await context.bot.send_document(
                chat_id=OWNER_ID,
                document=file_id,
                caption=f"{report_no} - proof of payment",
            )
    except Exception:
        logger.exception("Could not send refund payment proof.")

    context.user_data.clear()
    return ConversationHandler.END


async def cmd_report(update, context):
    if not owner_only(update.effective_user.id):
        await update.message.reply_text("owner only.")
        return

    if not context.args:
        await update.message.reply_text("usage: /report RPT-0001")
        return

    report_no = context.args[0].upper()
    row = get_report(report_no)

    if not row:
        await update.message.reply_text("report not found.")
        return

    await update.message.reply_text(
        full_report_owner_text(row),
        reply_markup=owner_report_keyboard(report_no, row["user_id"]),
    )


async def cmd_status(update, context):
    if not owner_only(update.effective_user.id):
        await update.message.reply_text("owner only.")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "usage: /status RPT-0001 STATUS\n\n"
            "examples:\n"
            "/status RPT-0001 SUBMITTED\n"
            "/status RPT-0001 ACCOUNT FIXED\n"
            "/status RPT-0001 ACCOUNT REPLACED\n"
            "/status RPT-0001 FOR REFUND"
        )
        return

    report_no = context.args[0].upper()
    status = " ".join(context.args[1:]).upper()
    row = get_report(report_no)

    if not row:
        await update.message.reply_text("report not found.")
        return

    allowed_statuses = {
        "SUBMITTED",
        "ACCOUNT FIXED",
        "ACCOUNT REPLACED",
        "FOR REFUND",
        "VOIDED",
        "WARNING",
    }

    if status not in allowed_statuses:
        await update.message.reply_text(
            "invalid status. use SUBMITTED, ACCOUNT FIXED, ACCOUNT REPLACED, FOR REFUND, VOIDED, or WARNING."
        )
        return

    update_report(report_no, status=status)

    await context.bot.send_message(
        row["user_id"],
        f"report {report_no} update:\n\nstatus: {status}"
    )
    await update.message.reply_text(
        f"{report_no} updated to {status}."
    )


async def cmd_fix(update, context):
    if not owner_only(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("usage: /fix RPT-0001")
        return

    report_no = context.args[0].upper()
    row = get_report(report_no)

    if not row:
        await update.message.reply_text("report not found.")
        return

    update_report(report_no, status="ACCOUNT FIXED")
    await context.bot.send_message(
        row["user_id"],
        f"report {report_no} update:\n\nstatus: ACCOUNT FIXED"
    )
    await update.message.reply_text("done.")


async def cmd_replace(update, context):
    if not owner_only(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("usage: /replace RPT-0001")
        return

    report_no = context.args[0].upper()
    row = get_report(report_no)

    if not row:
        await update.message.reply_text("report not found.")
        return

    update_report(report_no, status="ACCOUNT REPLACED")
    await context.bot.send_message(
        row["user_id"],
        f"report {report_no} update:\n\nstatus: ACCOUNT REPLACED"
    )
    await update.message.reply_text("done.")


async def cmd_refund(update, context):
    if not owner_only(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("usage: /refund RPT-0001")
        return

    report_no = context.args[0].upper()
    row = get_report(report_no)

    if not row:
        await update.message.reply_text("report not found.")
        return

    update_report(report_no, status="FOR REFUND")

    await context.bot.send_message(
        row["user_id"],
        f"report {report_no} update:\n\n"
        "status: FOR REFUND\n\n"
        "please choose your reason below.",
        reply_markup=refund_reason_keyboard(report_no),
    )

    await update.message.reply_text("done.")


async def cmd_reply(update, context):
    if not owner_only(update.effective_user.id):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "usage: /reply RPT-0001 your message here"
        )
        return

    report_no = context.args[0].upper()
    text = " ".join(context.args[1:])
    row = get_report(report_no)

    if not row:
        await update.message.reply_text("report not found.")
        return

    try:
        await context.bot.send_message(
            row["user_id"],
            f"message from lanayanaliv regarding report {report_no}:\n\n{text}"
        )
        await update.message.reply_text("message sent.")
    except Exception as exc:
        await update.message.reply_text(f"could not send message: {exc}")


async def cmd_warning(update, context):
    if not owner_only(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("usage: /warning USER_ID")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user id must be numeric.")
        return

    rules = increment_mistake(user_id)
    count = rules["mistake_count"]

    if count >= 2:
        status = "VOIDED"
        message = (
            "second mistake recorded.\n\n"
            "your report/warranty is VOIDED."
        )
    else:
        status = "WARNING"
        message = (
            "first mistake recorded.\n\n"
            "this is a WARNING."
        )

    try:
        await context.bot.send_message(user_id, message)
    except Exception:
        pass

    await update.message.reply_text(
        f"user {user_id}: {status}\n"
        f"mistake count: {count}"
    )


async def cmd_direct_owner(update, context):
    if not owner_only(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("usage: /directowner USER_ID")
        return

    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("user id must be numeric.")
        return

    rules = increment_direct_owner(user_id)
    count = rules["direct_owner_count"]

    if count >= 2:
        status = "VOIDED"
        message = (
            "second direct-to-owner report recorded.\n\n"
            "your report/warranty is VOIDED."
        )
    else:
        status = "WARNING"
        message = (
            "first direct-to-owner report recorded.\n\n"
            "this is a WARNING."
        )

    try:
        await context.bot.send_message(user_id, message)
    except Exception:
        pass

    await update.message.reply_text(
        f"user {user_id}: {status}\n"
        f"direct-to-owner count: {count}"
    )


async def cmd_myreport(update, context):
    row = get_latest_report_for_user(update.effective_user.id)

    if not row:
        await update.message.reply_text("you don't have a report yet.")
        return

    await update.message.reply_text(
        f"your latest report\n\n"
        f"report number: {row['report_no']}\n"
        f"status: {row['status']}\n"
        f"date reported: {row['date_reported'] or 'not available'}\n"
        f"subscription days remaining: {row['subscription_remaining'] if row['subscription_remaining'] is not None else 'not available'}\n"
        f"fixing deadline: {row['fixing_deadline'] or 'not available'}"
    )


async def cmd_cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text(
        "current report session cancelled.\n\nuse /start to begin again."
    )
    return ConversationHandler.END


async def update_countdowns(context: ContextTypes.DEFAULT_TYPE):
    conn = db_connect()
    rows = conn.execute("""
        SELECT * FROM reports
        WHERE status IN ('SUBMITTED', 'WARNING')
    """).fetchall()
    conn.close()

    today = date.today()

    for row in rows:
        purchased = parse_date(row["date_purchased"]) if row["date_purchased"] else None
        reported = parse_date(row["date_reported"]) if row["date_reported"] else today
        validity = row["days_availed"]

        remaining = calculate_remaining(
            purchased,
            validity,
            today,
        )

        update_report(
            row["report_no"],
            subscription_remaining=remaining,
        )

        if row["fixing_deadline"]:
            deadline = parse_date(row["fixing_deadline"])
            if deadline and today > deadline and row["status"] == "SUBMITTED":
                update_report(row["report_no"], status="FOR REFUND")

                try:
                    await context.bot.send_message(
                        row["user_id"],
                        f"report {row['report_no']} update:\n\n"
                        "status: FOR REFUND\n\n"
                        "the 0–7 day fixing period has ended without a recorded fix or replacement.\n\n"
                        "please choose your refund reason below.",
                        reply_markup=refund_reason_keyboard(row["report_no"]),
                    )
                except Exception:
                    logger.exception("Could not notify user about refund status.")


async def error_handler(update, context):
    logger.exception("Unhandled exception", exc_info=context.error)


def build_application():
    if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        raise RuntimeError(
            "BOT_TOKEN is not set. Put your bot token in Railway Variables."
        )

    if OWNER_ID == 123456789:
        logger.warning(
            "OWNER_ID is still the placeholder 123456789. "
            "Change OWNER_ID in Railway Variables."
        )

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    report_conversation = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(category_callback, pattern=r"^cat:"),
        ],
        states={
            CHOOSING_CATEGORY: [
                CallbackQueryHandler(category_callback, pattern=r"^cat:")
            ],
            ENTERING_FORM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, form_message)
            ],
            WAITING_ISSUE_PROOF: [
                MessageHandler(
                    (filters.PHOTO | filters.Document.ALL),
                    issue_proof_message,
                )
            ],
            WAITING_VOUCH_PROOF: [
                MessageHandler(
                    (filters.PHOTO | filters.Document.ALL),
                    vouch_proof_message,
                )
            ],
            WAITING_SUBMIT: [
                CallbackQueryHandler(
                    submit_pending_callback,
                    pattern=r"^submit_pending$",
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
        ],
        allow_reentry=True,
    )

    refund_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                refund_reason_callback,
                pattern=r"^refundreason:",
            )
        ],
        states={
            REFUND_FORM: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, refund_form_message)
            ],
            WAITING_PAYMENT_PROOF: [
                MessageHandler(
                    (filters.PHOTO | filters.Document.ALL),
                    payment_proof_message,
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cmd_cancel),
        ],
        allow_reentry=True,
    )

    application.add_handler(report_conversation)
    application.add_handler(refund_conversation)

    application.add_handler(
        CallbackQueryHandler(fix_callback, pattern=r"^fix:")
    )
    application.add_handler(
        CallbackQueryHandler(replace_callback, pattern=r"^replace:")
    )
    application.add_handler(
        CallbackQueryHandler(forrefund_callback, pattern=r"^forrefund:")
    )
    application.add_handler(
        CallbackQueryHandler(reply_callback, pattern=r"^reply:")
    )

    application.add_handler(CommandHandler("report", cmd_report))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("fix", cmd_fix))
    application.add_handler(CommandHandler("replace", cmd_replace))
    application.add_handler(CommandHandler("refund", cmd_refund))
    application.add_handler(CommandHandler("reply", cmd_reply))
    application.add_handler(CommandHandler("warning", cmd_warning))
    application.add_handler(CommandHandler("directowner", cmd_direct_owner))
    application.add_handler(CommandHandler("myreport", cmd_myreport))
    application.add_handler(CommandHandler("cancel", cmd_cancel))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, owner_text_message),
        group=10,
    )

    application.add_error_handler(error_handler)

    application.job_queue.run_repeating(
        update_countdowns,
        interval=3600,
        first=60,
    )

    return application


def main():
    init_db()

    application = build_application()

    logger.info("lanayanaliv report bot is starting...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )


if __name__ == "__main__":
    main()
