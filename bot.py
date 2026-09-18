import os
import re
import sqlite3
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 6054777664
TUTORIAL_URL = "https://t.me/lanareports"
DB_FILE = "report_bot.db"

TZ = ZoneInfo("Asia/Manila")


START_TEXT = """welcome to lanayanaliv's report page!
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
owner report = voided
"""


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
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:

send the completed form here in one bubble chat only.""",

    "educational": """𝗘𝗗𝗨𝗖𝗔𝗧𝗜𝗢𝗡𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:

send the completed form here in one bubble chat only.""",

    "editing": """𝗘𝗗𝗜𝗧𝗜𝗡𝗚 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:

send the completed form here in one bubble chat only.""",

    "others": """𝗢𝗧𝗛𝗘𝗥𝗦/𝗚𝗘𝗡𝗘𝗥𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐨𝐝𝐮𝐜𝐭:
𝐩𝐫𝐨𝐝𝐮𝐜𝐭 𝐢𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:

send the completed form here in one bubble chat only."""
}


REPLACEMENT_FORM = """𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗥𝗘𝗣𝗟𝗔𝗖𝗘𝗠𝗘𝗡𝗧
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫:
𝐧𝐞𝐰 𝐚𝐜𝐜𝐨𝐮𝐧𝐭:
𝐧𝐞𝐰 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐧𝐞𝐰 𝐩𝐫𝐨𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐩𝐢𝐧:

𝐜𝐥𝐢𝐜𝐤 𝐨𝐫 𝐭𝐚𝐩 𝐭𝐡𝐞 𝐥𝐢𝐧𝐤 𝐛𝐞𝐥𝐨𝐰 𝐚𝐧𝐝 𝐢-𝐬𝐞𝐧𝐝 𝐝𝐨𝐨𝐧 𝐚𝐧𝐠
𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐥𝐨𝐠 𝐢𝐧 𝐰𝐢𝐭𝐡𝐢𝐧 𝐟𝐨𝐮𝐫 𝐡𝐨𝐮𝐫𝐬 𝐭𝐨 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞
𝐰𝐚𝐫𝐫𝐚𝐧𝐭𝐲 𝐟𝐨𝐫 𝐭𝐡𝐢𝐬 𝐚𝐜𝐜𝐨𝐮𝐧𝐭. 𝐭𝐡𝐚𝐧𝐤 𝐲𝐨𝐮 𝐬𝐨 𝐦𝐮𝐜𝐡!

tap the link:
http://t.me/lanareports?direct"""

REFUND_GUIDE = """why refund?
can't be fixed / can't be replaced
━━━━━━━━⊱⋆⊰━━━━━━━━
guide:
~ first, fill out and submit the form
~ second step, send your bank details
and it can be a photo of your qr code
or your bank number and initials
~ last step is provide your proof of
payment. screenshot mo yung convo
natin sa part kung nasaan yung receipt
na sinend mo noong nag bayad ka"""


REFUND_FORM = """𝗥𝗘𝗙𝗨𝗡𝗗 𝗙𝗢𝗥𝗠
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:"""


def now_ph():
    return datetime.now(TZ)


def today_ph():
    return now_ph().date()


def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_number TEXT UNIQUE,
            buyer_id INTEGER NOT NULL,
            buyer_username TEXT,
            category TEXT,
            form_text TEXT,
            data_json TEXT,
            date_purchased TEXT,
            date_reported TEXT,
            days_availed INTEGER,
            amount_paid REAL,
            status TEXT,
            fixing_deadline TEXT,
            warranty_deadline TEXT,
            last_update_date TEXT,
            owner_message_id INTEGER,
            refund_reason TEXT,
            refund_bank_details TEXT,
            refund_bank_file_id TEXT,
            refund_payment_proof_file_id TEXT,
            refund_owner_message_id INTEGER,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_report(report_number):
    conn = db()
    row = conn.execute(
        "SELECT * FROM reports WHERE report_number = ?",
        (report_number,)
    ).fetchone()
    conn.close()
    return row


def get_report_by_owner_message(message_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM reports WHERE owner_message_id = ? OR refund_owner_message_id = ?",
        (message_id, message_id)
    ).fetchone()
    conn.close()
    return row


def update_report(report_number, **values):
    if not values:
        return

    fields = []
    params = []

    for key, value in values.items():
        fields.append(f"{key} = ?")
        params.append(value)

    params.append(report_number)

    conn = db()
    conn.execute(
        f"UPDATE reports SET {', '.join(fields)} WHERE report_number = ?",
        params
    )
    conn.commit()
    conn.close()


def create_report(data):
    conn = db()

    next_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) + 1 FROM reports"
    ).fetchone()[0]

    report_number = f"R-{next_id:04d}"

    conn.execute("""
        INSERT INTO reports (
            report_number,
            buyer_id,
            buyer_username,
            category,
            form_text,
            data_json,
            date_purchased,
            date_reported,
            days_availed,
            amount_paid,
            status,
            fixing_deadline,
            warranty_deadline,
            last_update_date,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        report_number,
        data["buyer_id"],
        data["buyer_username"],
        data["category"],
        data["form_text"],
        data["data_json"],
        data["date_purchased"],
        data["date_reported"],
        data["days_availed"],
        data["amount_paid"],
        "SUBMITTED",
        data["fixing_deadline"],
        None,
        str(today_ph()),
        now_ph().isoformat()
    ))

    conn.commit()
    conn.close()

    return report_number


def normalize_label(label):
    label = label.lower().strip()
    label = label.replace("𝐰", "w")
    label = label.replace("𝐡", "h")
    label = label.replace("𝐚", "a")
    label = label.replace("𝐭", "t")
    label = label.replace("𝐩", "p")
    label = label.replace("𝐫", "r")
    label = label.replace("𝐞", "e")
    label = label.replace("𝐦", "m")
    label = label.replace("𝐢", "i")
    label = label.replace("𝐮", "u")
    label = label.replace("𝐧", "n")
    label = label.replace("𝐥", "l")
    label = label.replace("𝐬", "s")
    label = label.replace("𝐝", "d")
    label = label.replace("𝐜", "c")
    label = label.replace("𝐨", "o")
    label = label.replace("𝐯", "v")
    label = label.replace("𝐟", "f")
    label = label.replace("𝐛", "b")
    label = label.replace("𝐲", "y")
    label = label.replace("𝐠", "g")
    label = label.replace("𝐱", "x")
    label = label.replace("𝐤", "k")
    label = label.replace("𝐪", "q")
    label = label.replace("𝐣", "j")
    label = label.replace("𝐰", "w")

    label = re.sub(r"[^a-z0-9]+", "_", label)
    return label.strip("_")


LABEL_MAP = {
    "what_premium": "what_premium",
    "what_premium_": "what_premium",
    "email_number": "email_number",
    "email": "email_number",
    "password": "password",
    "profile_and_pin": "profile_pin",
    "profile_pin": "profile_pin",
        "days_availed": "days_availed",
        "shared_slp_or_sla": "shared_type",
        "shared_sla": "shared_type",
        "shared_slp": "shared_type",
        "shared": "shared_type",
        "shared_account_or_profile": "shared_type",
        "date_purchased": "date_purchased",
    "amount_paid": "amount_paid",
    "specific_issue": "specific_issue",
    "what_product": "what_product",
    "product_information": "product_information",
    "date_reported": "date_reported",
}


def parse_lines(text):
    result = {}

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line or ":" not in line:
            continue

        label, value = line.split(":", 1)

        key = normalize_label(label)
        key = LABEL_MAP.get(key, key)

        value = value.strip()

        if value:
            result[key] = value

    return result


def parse_date_value(value):
    value = value.strip()

    value = value.replace(".", "/")
    value = value.replace("-", "/")
    value = re.sub(r"\s+", "", value)

    parts = value.split("/")

    if len(parts) != 3:
        return None

    try:
        a, b, c = [int(x) for x in parts]
    except ValueError:
        return None

    try:
        if len(parts[0]) == 4:
            year = a

            if 1 <= b <= 12 and 1 <= c <= 31:
                return date(year, b, c)

            if 1 <= c <= 12 and 1 <= b <= 31:
                return date(year, c, b)

        year = c + 2000 if c < 100 else c

        if 1 <= a <= 12 and 1 <= b <= 31:
            return date(year, a, b)

        if 1 <= b <= 12 and 1 <= a <= 31:
            return date(year, b, a)

    except ValueError:
        return None

    return None


def parse_money(value):
    value = value.strip()
    value = value.replace("₱", "")
    value = value.replace(",", "")
    value = value.replace("php", "")
    value = value.strip()

    try:
        return float(Decimal(value))
    except (InvalidOperation, ValueError):
        return None


def parse_int(value):
    match = re.search(r"\d+", value or "")

    if not match:
        return None

    try:
        return int(match.group())
    except ValueError:
        return None


def calculate_remaining_days(date_purchased, days_availed):
    if not date_purchased or not days_availed:
        return None

    remaining = days_availed - (today_ph() - date_purchased).days

    return max(0, remaining)


def fixing_days_remaining(deadline_string):
    if not deadline_string:
        return 0

    try:
        deadline = date.fromisoformat(deadline_string)
    except ValueError:
        return 0

    remaining = (deadline - today_ph()).days

    return max(0, remaining)


def service_fee(validity, remaining):
    remaining = int(remaining)

    if remaining <= 0:
        return 0.0

    if validity == 30:
        if remaining == 30:
            return 1.0
        if 25 <= remaining <= 29:
            return 0.80
        if 20 <= remaining <= 24:
            return 0.70
        if 15 <= remaining <= 19:
            return 0.60
        if 10 <= remaining <= 14:
            return 0.50
        if 6 <= remaining <= 9:
            return 0.40

    if validity == 60:
        if remaining == 60:
            return 1.0
        if 55 <= remaining <= 59:
            return 0.80
        if 45 <= remaining <= 54:
            return 0.70
        if 35 <= remaining <= 44:
            return 0.60
        if 25 <= remaining <= 34:
            return 0.50
        if 15 <= remaining <= 24:
            return 0.40
        if 7 <= remaining <= 14:
            return 0.30

    if validity == 90:
        if remaining == 90:
            return 1.0
        if 78 <= remaining <= 89:
            return 0.80
        if 69 <= remaining <= 77:
            return 0.70
        if 59 <= remaining <= 68:
            return 0.60
        if 49 <= remaining <= 58:
            return 0.50
        if 39 <= remaining <= 48:
            return 0.40
        if 29 <= remaining <= 38:
            return 0.30
        if 19 <= remaining <= 28:
            return 0.20
        if 7 <= remaining <= 18:
            return 0.10

    if validity == 120:
        if remaining == 120:
            return 1.0
        if 110 <= remaining <= 119:
            return 0.80
        if 95 <= remaining <= 109:
            return 0.70
        if 80 <= remaining <= 94:
            return 0.60
        if 60 <= remaining <= 79:
            return 0.50
        if 49 <= remaining <= 59:
            return 0.40
        if 35 <= remaining <= 48:
            return 0.30
        if 20 <= remaining <= 34:
            return 0.20
        if 8 <= remaining <= 19:
            return 0.10

    if validity == 150:
        if remaining == 150:
            return 1.0
        if 130 <= remaining <= 149:
            return 0.80
        if 110 <= remaining <= 129:
            return 0.70
        if 90 <= remaining <= 109:
            return 0.60
        if 70 <= remaining <= 89:
            return 0.50
        if 50 <= remaining <= 69:
            return 0.40
        if 30 <= remaining <= 49:
            return 0.30
        if 15 <= remaining <= 29:
            return 0.20
        if 11 <= remaining <= 14:
            return 0.10

    if validity == 180:
        if remaining == 180:
            return 1.0
        if 150 <= remaining <= 179:
            return 0.80
        if 120 <= remaining <= 149:
            return 0.70
        if 90 <= remaining <= 119:
            return 0.60
        if 70 <= remaining <= 89:
            return 0.50
        if 50 <= remaining <= 69:
            return 0.40
        if 30 <= remaining <= 49:
            return 0.30
        if 15 <= remaining <= 29:
            return 0.20
        if 11 <= remaining <= 14:
            return 0.10

    if validity == 360:
        if remaining == 360:
            return 1.0
        if 340 <= remaining <= 359:
            return 0.80
        if 320 <= remaining <= 339:
            return 0.70
        if 300 <= remaining <= 319:
            return 0.60
        if 250 <= remaining <= 299:
            return 0.50
        if 200 <= remaining <= 249:
            return 0.40
        if 150 <= remaining <= 199:
            return 0.30
        if 100 <= remaining <= 149:
            return 0.20
        if 50 <= remaining <= 99:
            return 0.10
        if 11 <= remaining <= 49:
            return 0.05

    return None


def calculate_refund(amount_paid, validity, remaining):
    fee = service_fee(validity, remaining)

    if fee is None:
        return None, None

    refund = (amount_paid / validity) * remaining * fee

    return round(refund, 2), fee


def buyer_name(user):
    if user.username:
        return f"@{user.username}"

    return user.full_name or str(user.id)


def category_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("entertainment", callback_data="cat_entertainment"),
            InlineKeyboardButton("editing", callback_data="cat_editing"),
        ],
        [
            InlineKeyboardButton("educational", callback_data="cat_educational"),
            InlineKeyboardButton("others", callback_data="cat_others"),
        ],
        [
            InlineKeyboardButton(
                "report step-by-step tutorial",
                url=TUTORIAL_URL
            )
        ]
    ])


def submit_keyboard(report_number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "submit",
                callback_data=f"submit_report:{report_number}"
            )
        ]
    ])


def owner_action_keyboard(report_number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "report noted",
                callback_data=f"owner_action:{report_number}:noted"
            ),
            InlineKeyboardButton(
                "please wait",
                callback_data=f"owner_action:{report_number}:wait"
            ),
        ],
        [
            InlineKeyboardButton(
                "account replaced",
                callback_data=f"owner_action:{report_number}:replace"
            ),
            InlineKeyboardButton(
                "account fixed",
                callback_data=f"owner_action:{report_number}:fixed"
            ),
        ],
        [
            InlineKeyboardButton(
                "warning",
                callback_data=f"owner_action:{report_number}:warning"
            ),
            InlineKeyboardButton(
                "voided",
                callback_data=f"owner_action:{report_number}:voided"
            ),
        ],
        [
            InlineKeyboardButton(
                "can't fix/rep, for refund na",
                callback_data=f"refund_reason:{report_number}"
            )
        ]
    ])


def send_as_keyboard(report_number, action):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "send as is",
                callback_data=f"send_action:{report_number}:{action}"
            ),
            InlineKeyboardButton(
                "reply first",
                callback_data=f"reply_action:{report_number}:{action}"
            )
        ]
    ])


def warranty_keyboard(report_number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "warranty activated",
                callback_data=f"warranty:{report_number}:activated"
            ),
            InlineKeyboardButton(
                "warranty voided",
                callback_data=f"warranty:{report_number}:voided"
            )
        ]
    ])


def refund_reason_keyboard(report_number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "can't be fixed",
                callback_data=f"refund_set:{report_number}:can't be fixed"
            )
        ],
        [
            InlineKeyboardButton(
                "can't be replaced",
                callback_data=f"refund_set:{report_number}:can't be replaced"
            )
        ]
    ])


def refund_submit_keyboard(report_number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "submit",
                callback_data=f"refund_submit:{report_number}"
            )
        ]
    ])


def refund_owner_keyboard(report_number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "refund sent",
                callback_data=f"refund_owner:{report_number}:sent"
            )
        ],
        [
            InlineKeyboardButton(
                "warning, wrong details/format",
                callback_data=f"refund_owner:{report_number}:warning"
            )
        ],
        [
            InlineKeyboardButton(
                "voided, wrong details/format",
                callback_data=f"refund_owner:{report_number}:voided"
            )
        ]
    ])


def parse_report_form(text, category):
    fields = parse_lines(text)

    if category == "entertainment":
        required = [
            "what_premium",
            "email_number",
            "password",
            "profile_pin",
            "days_availed",
            "shared_type",
            "date_purchased",
            "amount_paid",
            "specific_issue",
        ]

    elif category in ("educational", "editing"):
        required = [
            "what_premium",
            "email_number",
            "password",
            "days_availed",
            "shared_type",
            "date_purchased",
            "amount_paid",
            "specific_issue",
        ]

    else:
        required = [
            "what_product",
            "product_information",
            "days_availed",
            "date_purchased",
            "date_reported",
            "amount_paid",
            "specific_issue",
        ]

    missing = [
        field for field in required
        if not fields.get(field)
    ]

    if missing:
        return None, missing

    days = parse_int(fields["days_availed"])

    if days is None or days <= 0:
        return None, ["days_availed must be a valid number"]

    date_purchased = parse_date_value(fields["date_purchased"])

    if date_purchased is None:
        return None, ["date_purchased"]

    amount = parse_money(fields["amount_paid"])

    if amount is None:
        return None, ["amount_paid"]

    if category == "others":
        date_reported = parse_date_value(fields["date_reported"])

        if date_reported is None:
            return None, ["date_reported"]
    else:
        date_reported = today_ph()

    fields["date_purchased_parsed"] = date_purchased.isoformat()
    fields["date_reported_parsed"] = date_reported.isoformat()
    fields["days_availed_parsed"] = days
    fields["amount_paid_parsed"] = amount

    return fields, []


def report_product(data, category):
    if category == "others":
        return data.get("what_product", "")
    return data.get("what_premium", "")


def report_shared(data, category):
    if category == "others":
        return ""
    return data.get("shared_type", "")


def owner_report_text(report):
    data = __import__("json").loads(report["data_json"])

    purchase = parse_date_value(report["date_purchased"])
    if purchase:
        purchase_display = purchase.strftime("%m.%d.%y")
    else:
        purchase_display = report["date_purchased"]

    remaining = calculate_remaining_days(
        purchase,
        report["days_availed"]
    )

    fixing = fixing_days_remaining(
        report["fixing_deadline"]
    )

    product = report_product(
        data,
        report["category"]
    )

    shared = report_shared(
        data,
        report["category"]
    )

    return f"""𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫𝐧𝐚𝐦𝐞: {report["buyer_username"]}
𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫 𝐢𝐝: {report["buyer_id"]}
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {report["report_number"]}

𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦: {product}
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚/𝐬𝐥𝐩: {shared}
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝: {purchase_display}
𝐫𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐝𝐚𝐲𝐬: {remaining if remaining is not None else "not available"}
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝: {report["amount_paid"]}
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞: {data.get("specific_issue", "")}

𝐟𝐢𝐱𝐢𝐧𝐠 𝐝𝐚𝐲𝐬 𝐫𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠: {fixing}
𝐬𝐭𝐚𝐭𝐮𝐬: {report["status"]}

𝐩𝐫𝐨𝐨𝐟 𝐢𝐬𝐬𝐮𝐞:
𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐯𝐨𝐮𝐜𝐡:"""


def buyer_status_text(report):
    data = __import__("json").loads(report["data_json"])

    purchase = parse_date_value(report["date_purchased"])

    remaining = calculate_remaining_days(
        purchase,
        report["days_availed"]
    )

    fixing = fixing_days_remaining(
        report["fixing_deadline"]
    )

    return f"""report number: {report["report_number"]}
status: {report["status"]}
remaining subscription days: {remaining if remaining is not None else "not available"}
fixing days remaining: {fixing}

please wait 0–7 days fixing days."""


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        START_TEXT,
        reply_markup=category_keyboard()
    )


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.replace("cat_", "")

    context.user_data.clear()
    context.user_data["report_category"] = category

    await query.message.reply_text(FORMS[category])


async def parse_and_store_buyer_form(update, context):
    category = context.user_data.get("report_category")

    if not category:
        return False

    text = update.message.text

    data, missing = parse_report_form(
        text,
        category
    )

    if data is None:
        missing_text = ", ".join(missing)

        await update.message.reply_text(
            f"""please check your report form.

missing or invalid fields: {missing_text}

send the complete corrected form again in one bubble chat."""
        )

        return True

    context.user_data["report_form"] = data
    context.user_data["report_form_text"] = text
    context.user_data["proof_issue"] = None
    context.user_data["proof_vouch"] = None

    await update.message.reply_text(
        """correct format.

now send your proof of issue and proof of vouch.

send both screenshots here."""
    )

    return True


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    photo = update.message.photo[-1]
    file_id = photo.file_id

    if user.id == OWNER_ID:
        return await handle_owner_photo(update, context, file_id)

    if context.user_data.get("refund_mode") == "bank":
        context.user_data["refund_bank_file_id"] = file_id
        context.user_data["refund_mode"] = "payment_proof"

        await update.message.reply_text(
            """𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐩𝐚𝐲𝐦𝐞𝐧𝐭:

send a screenshot of our conversation showing the receipt you sent when you paid."""
        )

        return

    if context.user_data.get("refund_mode") == "payment_proof":
        context.user_data["refund_payment_proof_file_id"] = file_id
        context.user_data["refund_mode"] = "ready"

        report_number = context.user_data.get("refund_report_number")

        await update.message.reply_text(
            "proof of payment received.\n\nclick submit when everything is complete.",
            reply_markup=refund_submit_keyboard(report_number)
        )

        return

    if context.user_data.get("warranty_waiting"):
        report_number = context.user_data["warranty_report_number"]

        report = get_report(report_number)

        if not report:
            return

        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"""proof of login received.

report number: {report_number}
buyer: {report["buyer_username"]}
buyer user id: {report["buyer_id"]}

the buyer has sent their proof of login below.

choose the warranty result:"""
        )

        await context.bot.copy_message(
            chat_id=OWNER_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )

        await context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"warranty decision for report {report_number}:",
            reply_markup=warranty_keyboard(report_number)
        )

        context.user_data["warranty_waiting"] = False

        await update.message.reply_text(
            "proof of login received. wait for my approval if warranty activated or warranty voided."
        )

        return

    if context.user_data.get("proof_issue") is None:
        if context.user_data.get("report_form"):
            context.user_data["proof_issue"] = file_id

            await update.message.reply_text(
                "proof of issue received. now send your proof of vouch."
            )

            return

    if context.user_data.get("proof_vouch") is None:
        if context.user_data.get("proof_issue"):
            context.user_data["proof_vouch"] = file_id

            await update.message.reply_text(
                "proof of vouch received.\n\nclick submit when everything is complete.",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            "submit",
                            callback_data="submit_new_report"
                        )
                    ]
                ])
            )

            return


async def handle_owner_photo(update, context, file_id):
    owner_mode = context.user_data.get("owner_mode")

    if owner_mode == "refund_receipt":
        report_number = context.user_data.get("owner_report_number")

        report = get_report(report_number)

        if not report:
            context.user_data.clear()
            return

        await context.bot.send_photo(
            chat_id=report["buyer_id"],
            photo=file_id,
            caption=f"""refund receipt

report number: {report_number}

refund receipt sent. thank you."""
        )

        update_report(
            report_number,
            status="REFUND SENT"
        )

        context.user_data.clear()

        await update.message.reply_text(
            "refund receipt sent to the buyer."
        )

        return

    if owner_mode == "manual_reply":
        report_number = context.user_data.get("owner_report_number")
        action = context.user_data.get("owner_pending_action")

        report = get_report(report_number)

        if report:
            await context.bot.send_photo(
                chat_id=report["buyer_id"],
                photo=file_id
            )

            await finish_owner_action(
                context,
                report_number,
                action
            )

        context.user_data.clear()

        await update.message.reply_text(
            "your reply has been sent to the buyer."
        )

        return


async def submit_new_report(update, context):
    query = update.callback_query
    await query.answer()

    data = context.user_data.get("report_form")
    category = context.user_data.get("report_category")
    form_text = context.user_data.get("report_form_text")

    if not data or not category:
        await query.message.reply_text(
            "your report session expired. please press /start and fill out the form again."
        )
        return

    purchase = parse_date_value(
        data["date_purchased"]
    )

    report_date = parse_date_value(
        data["date_reported_parsed"]
    ) or today_ph()

    days = data["days_availed_parsed"]
    amount = data["amount_paid_parsed"]

    fixing_deadline = today_ph() + timedelta(days=7)

    payload = {
        "buyer_id": query.from_user.id,
        "buyer_username": buyer_name(query.from_user),
        "category": category,
        "form_text": form_text,
        "data_json": __import__("json").dumps(
            data,
            ensure_ascii=False
        ),
        "date_purchased": purchase.isoformat(),
        "date_reported": report_date.isoformat(),
        "days_availed": days,
        "amount_paid": amount,
        "fixing_deadline": fixing_deadline.isoformat(),
    }

    report_number = create_report(payload)

    update_report(
        report_number,
        data_json=__import__("json").dumps(
            data,
            ensure_ascii=False
        )
    )

    proof_issue = context.user_data.get("proof_issue")
    proof_vouch = context.user_data.get("proof_vouch")

    report = get_report(report_number)

    owner_message = await context.bot.send_message(
        OWNER_ID,
        owner_report_text(report),
        reply_markup=owner_action_keyboard(report_number)
    )

    update_report(
        report_number,
        owner_message_id=owner_message.message_id
    )

    if proof_issue:
        await context.bot.send_photo(
            OWNER_ID,
            proof_issue,
            caption=f"proof of issue\nreport number: {report_number}"
        )

    if proof_vouch:
        await context.bot.send_photo(
            OWNER_ID,
            proof_vouch,
            caption=f"proof of vouch\nreport number: {report_number}"
        )

    report = get_report(report_number)

    remaining = calculate_remaining_days(
        purchase,
        days
    )

    await query.message.reply_text(
        f"""report submitted.

report number: {report_number}
status: SUBMITTED
remaining subscription days: {remaining}
fixing days: 0–7 days

please wait for an update."""
    )

    context.user_data.clear()


async def owner_action_callback(update, context):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    report_number = parts[1]
    action = parts[2]

    report = get_report(report_number)

    if not report:
        await query.message.reply_text(
            "report not found."
        )
        return

if action == "replace":
    context.user_data.clear()
    context.user_data["owner_mode"] = "replacement"
    context.user_data["owner_report_number"] = report_number

    await query.message.reply_text(
        REPLACEMENT_FORM
    )

    return

        return

    if action == "wait":
        await query.message.reply_text(
            "choose how to send the please wait update:",
            reply_markup=send_as_keyboard(
                report_number,
                "wait"
            )
        )
        return

    if action == "noted":
        await query.message.reply_text(
            "choose how to send the report noted update:",
            reply_markup=send_as_keyboard(
                report_number,
                "noted"
            )
        )
        return

    if action == "fixed":
        await query.message.reply_text(
            "choose how to send the account fixed update:",
            reply_markup=send_as_keyboard(
                report_number,
                "fixed"
            )
        )
        return

    if action == "warning":
        await query.message.reply_text(
            "choose how to send the warning:",
            reply_markup=send_as_keyboard(
                report_number,
                "warning"
            )
        )
        return

    if action == "voided":
        await query.message.reply_text(
            "choose how to send the voided update:",
            reply_markup=send_as_keyboard(
                report_number,
                "voided"
            )
        )
        return


async def send_action_callback(update, context):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    report_number = parts[1]
    action = parts[2]

    await send_default_owner_action(
        context,
        report_number,
        action
    )

    await query.message.reply_text(
        "sent to the buyer."
    )


async def reply_action_callback(update, context):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    report_number = parts[1]
    action = parts[2]

    context.user_data["owner_mode"] = "manual_reply"
    context.user_data["owner_report_number"] = report_number
    context.user_data["owner_pending_action"] = action

    await query.message.reply_text(
        "send your custom reply now. it will be sent directly to the buyer."
    )


async def send_default_owner_action(context, report_number, action):
    report = get_report(report_number)

    if not report:
        return

    remaining = calculate_remaining_days(
        parse_date_value(report["date_purchased"]),
        report["days_availed"]
    )

    fixing = fixing_days_remaining(
        report["fixing_deadline"]
    )

    if action == "noted":
        message = f"""report number: {report_number}

report noted."""

        status = "REPORT NOTED"

    elif action == "wait":
        message = f"""report number: {report_number}

please wait 0–7 days fixing days.

fixing days remaining: {fixing}
remaining subscription days: {remaining}

we are currently checking/fixing your report."""

        status = "PLEASE WAIT"

    elif action == "fixed":
        message = f"""report number: {report_number}

same account fixed.

𝐬𝐞𝐧𝐝 𝐲𝐨𝐮𝐫 𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐥𝐨𝐠 𝐢𝐧 𝐰𝐢𝐭𝐡𝐢𝐧 𝐬𝐢𝐱 𝐡𝐨𝐮𝐫𝐬 𝐡𝐞𝐫𝐞 𝐢𝐧 𝐭𝐡𝐞 𝐛𝐨𝐭 𝐭𝐨 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞 𝐲𝐨𝐮𝐫 𝐰𝐚𝐫𝐫𝐚𝐧𝐭𝐲. 𝐭𝐲𝐬𝐦!"""

        status = "ACCOUNT FIXED"

    elif action == "warning":
        message = f"""report number: {report_number}

warning.

please make sure your future reports follow the correct report format and process."""

        status = "WARNING"

    elif action == "voided":
        message = f"""report number: {report_number}

voided.

this report has been voided."""

        status = "VOIDED"

    else:
        return

    if action == "fixed":
        warranty_deadline = now_ph() + timedelta(hours=6)

        update_report(
            report_number,
            status="ACCOUNT REPLACED",
            warranty_deadline=warranty_deadline.isoformat()
        )

        await context.bot.send_message(
            report["buyer_id"],
            replacement_message,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "send proof of log in here",
                        url="https://t.me/lanareports?direct"
                    )
                ]
            ])
        )

        await context.bot.send_message(
            OWNER_ID,
            f"""report number: {report_number}

waiting for buyer proof of login within six hours.

warranty deadline: {warranty_deadline.strftime("%Y-%m-%d %H:%M")}""",
            reply_markup=warranty_keyboard(report_number)
        )

    else:
        update_report(
            report_number,
            status=status
        )

        await context.bot.send_message(
            report["buyer_id"],
            message
        )


async def finish_owner_action(context, report_number, action):
    if action == "fixed":
        update_report(
            report_number,
            status="ACCOUNT FIXED",
            warranty_deadline=(
                now_ph() + timedelta(hours=6)
            ).isoformat()
        )

    elif action == "noted":
        update_report(
            report_number,
            status="REPORT NOTED"
        )

    elif action == "wait":
        update_report(
            report_number,
            status="PLEASE WAIT"
        )

    elif action == "warning":
        update_report(
            report_number,
            status="WARNING"
        )

    elif action == "voided":
        update_report(
            report_number,
            status="VOIDED"
        )


async def handle_owner_text(update, context):
    text = update.message.text or ""
    mode = context.user_data.get("owner_mode")

    if not mode:
        if update.message.reply_to_message:
            replied_id = update.message.reply_to_message.message_id
            report = get_report_by_owner_message(replied_id)

            if report:
                await context.bot.send_message(
                    report["buyer_id"],
                    text
                )

                await update.message.reply_text(
                    "your reply has been sent to the buyer."
                )

                return True

        return False

    report_number = context.user_data.get("owner_report_number")

    if mode == "replacement":
        fields = parse_lines(text)

        required = [
            "report_number",
            "new_account",
            "new_password",
            "new_profile_and_pin"
        ]

        aliases = {
            "report_number": "report_number",
            "new_account": "new_account",
            "new_password": "new_password",
            "new_profile_and_pin": "new_profile_and_pin",
            "new_profile_pin": "new_profile_and_pin",
        }

        normalized = {}

        for key, value in fields.items():
            normalized[aliases.get(key, key)] = value

        missing = [
            x for x in required
            if not normalized.get(x)
        ]

        if missing:
            await update.message.reply_text(
                f"""please check the account replacement form.

missing fields: {", ".join(missing)}

send the complete corrected form again."""
            )
            return True

        form_report_number = normalized["report_number"].strip()

        if form_report_number != report_number:
            await update.message.reply_text(
                f"report number must be {report_number}."
            )
            return True

        report = get_report(report_number)

        if not report:
            await update.message.reply_text(
                "report not found."
            )
            return True

        replacement_message = f"""𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗥𝗘𝗣𝗟𝗔𝗖𝗘𝗠𝗘𝗡𝗧
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {report_number}
𝐧𝐞𝐰 𝐚𝐜𝐜𝐨𝐮𝐧𝐭: {normalized["new_account"]}
𝐧𝐞𝐰 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝: {normalized["new_password"]}
𝐧𝐞𝐰 𝐩𝐫𝐨𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐩𝐢𝐧: {normalized["new_profile_and_pin"]}

𝐜𝐥𝐢𝐜𝐤 𝐨𝐫 𝐭𝐚𝐩 𝐭𝐡𝐞 𝐥𝐢𝐧𝐤 𝐛𝐞𝐥𝐨𝐰 𝐚𝐧𝐝 𝐢-𝐬𝐞𝐧𝐝 𝐝𝐨𝐨𝐧 𝐚𝐧𝐠
𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐥𝐨𝐠 𝐢𝐧 𝐰𝐢𝐭𝐡𝐢𝐧 𝐟𝐨𝐮𝐫 𝐡𝐨𝐮𝐫𝐬 𝐭𝐨 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞
𝐰𝐚𝐫𝐫𝐚𝐧𝐭𝐲 𝐟𝐨𝐫 𝐭𝐡𝐢𝐬 𝐚𝐜𝐜𝐨𝐮𝐧𝐭. 𝐭𝐡𝐚𝐧𝐤 𝐲𝐨𝐮 𝐬𝐨 𝐦𝐮𝐜𝐡!

tap the link: http://t.me/lanareports?direct"""

        warranty_deadline = now_ph() + timedelta(hours=4)

        update_report(
            report_number,
            status="ACCOUNT REPLACED",
            warranty_deadline = now_ph() + timedelta(hours=4)
        )

        await context.bot.send_message(
            report["buyer_id"],
            f"""report number: {report_number}

waiting for proof of login within four hours."""
        )

        await context.bot.send_message(
            OWNER_ID,
            f"""report number: {report_number}

buyer is now required to send proof of login within four hours.

warranty deadline: {warranty_deadline.strftime("%Y-%m-%d %H:%M")}""",
            reply_markup=warranty_keyboard(report_number)
        )

        context.user_data.clear()
        return True

    if mode == "manual_reply":
        report = get_report(report_number)

        if report:
            await context.bot.send_message(
                report["buyer_id"],
                text
            )

            await finish_owner_action(
                context,
                report_number,
                context.user_data.get("owner_pending_action")
            )

        context.user_data.clear()

        await update.message.reply_text(
            "your custom reply has been sent to the buyer."
        )

        return True

    if mode == "refund_reason":
        return True

    if mode == "refund_warning":
        report = get_report(report_number)

        if report:
            await context.bot.send_message(
                report["buyer_id"],
                f"""report number: {report_number}

warning, wrong details/format.

reason:
{text}"""
            )

            update_report(
                report_number,
                status="REFUND WARNING"
            )

        context.user_data.clear()

        await update.message.reply_text(
            "warning reason sent to the buyer."
        )

        return True

    if mode == "refund_voided":
        report = get_report(report_number)

        if report:
            await context.bot.send_message(
                report["buyer_id"],
                f"""report number: {report_number}

voided, wrong details/format.

reason:
{text}"""
            )

            update_report(
                report_number,
                status="REFUND VOIDED"
            )

        context.user_data.clear()

        await update.message.reply_text(
            "void reason sent to the buyer."
        )

        return True

    if mode == "refund_receipt":
        report = get_report(report_number)

        if report:
            await context.bot.send_message(
                report["buyer_id"],
                f"""refund receipt

report number: {report_number}

{text}"""
            )

            update_report(
                report_number,
                status="REFUND SENT"
            )

        context.user_data.clear()

        await update.message.reply_text(
            "refund receipt sent to the buyer."
        )

        return True

    return False


async def refund_reason_callback(update, context):
    query = update.callback_query
    await query.answer()

    report_number = query.data.split(":")[1]

    report = get_report(report_number)

    if not report:
        await query.message.reply_text(
            "report not found."
        )
        return

    await query.message.reply_text(
        "choose the reason for refund:",
        reply_markup=refund_reason_keyboard(report_number)
    )


async def refund_set_callback(update, context):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    report_number = parts[1]
    reason = parts[2]

    report = get_report(report_number)

    if not report:
        await query.message.reply_text(
            "report not found."
        )
        return

    update_report(
        report_number,
        status="FOR REFUND",
        refund_reason=reason
    )

    await context.bot.send_message(
        report["buyer_id"],
        REFUND_GUIDE,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "refund form",
                    callback_data=f"refund_form:{report_number}"
                )
            ]
        ])
    )

    await query.message.reply_text(
        f"""report {report_number} is now FOR REFUND.

reason: {reason}

refund guide sent to the buyer."""
    )


async def refund_form_callback(update, context):
    query = update.callback_query
    await query.answer()

    report_number = query.data.split(":")[1]

    report = get_report(report_number)

    if not report:
        await query.message.reply_text(
            "report not found."
        )
        return

    if report["buyer_id"] != query.from_user.id:
        return

    context.user_data.clear()

    context.user_data["refund_mode"] = "form"
    context.user_data["refund_report_number"] = report_number

    await query.message.reply_text(
        REFUND_FORM
    )


def parse_refund_form(text):
    fields = parse_lines(text)

    required = [
        "report_number",
        "date_purchased",
        "date_reported",
        "amount_paid"
    ]

    missing = [
        field for field in required
        if not fields.get(field)
    ]

    if missing:
        return None, missing

    purchase = parse_date_value(
        fields["date_purchased"]
    )

    reported = parse_date_value(
        fields["date_reported"]
    )

    amount = parse_money(
        fields["amount_paid"]
    )

    if purchase is None:
        return None, ["date_purchased"]

    if reported is None:
        return None, ["date_reported"]

    if amount is None:
        return None, ["amount_paid"]

    fields["purchase_parsed"] = purchase.isoformat()
    fields["reported_parsed"] = reported.isoformat()
    fields["amount_parsed"] = amount

    return fields, []


async def refund_submit_callback(update, context):
    query = update.callback_query
    await query.answer()

    report_number = query.data.split(":")[1]

    report = get_report(report_number)

    if not report:
        await query.message.reply_text(
            "report not found."
        )
        return

    if report["buyer_id"] != query.from_user.id:
        return

    if context.user_data.get("refund_report_number") != report_number:
        await query.message.reply_text(
            "your refund session expired. please open the refund form again."
        )
        return

    if not context.user_data.get("refund_form_data"):
        await query.message.reply_text(
            "refund form is incomplete."
        )
        return

    if (
        not context.user_data.get("refund_bank_file_id")
        and not context.user_data.get("refund_bank_text")
    ):
        await query.message.reply_text(
            "please send your bank details first."
        )
        return

    if not context.user_data.get(
        "refund_payment_proof_file_id"
    ):
        await query.message.reply_text(
            "please send your proof of payment first."
        )
        return

    form = context.user_data["refund_form_data"]

    purchase = parse_date_value(
        form["date_purchased"]
    )

    amount_paid = form["amount_parsed"]

    remaining = calculate_remaining_days(
        purchase,
        report["days_availed"]
    )

    refund_amount, fee = calculate_refund(
        amount_paid,
        report["days_availed"],
        remaining
    )

    if refund_amount is None:
        refund_text = f"""𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {report_number}

the remaining-day service-fee tier is not defined for {remaining} remaining days.

please have the owner review the refund manually."""

    else:
        refund_text = f"""𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {report_number}

refund computation:

amount paid: ₱{amount_paid:.2f}
validity: {report["days_availed"]} days
remaining days: {remaining}
service fee: {fee:.2f}

amount to be refunded: ₱{refund_amount:.2f}"""

    update_report(
        report_number,
        date_purchased=purchase.isoformat(),
        date_reported=form["reported_parsed"],
        amount_paid=amount_paid,
        refund_bank_details=context.user_data.get(
            "refund_bank_text"
        ),
        refund_bank_file_id=context.user_data.get(
            "refund_bank_file_id"
        ),
        refund_payment_proof_file_id=context.user_data.get(
            "refund_payment_proof_file_id"
        ),
        status="REFUND FOR REVIEW"
    )

    report = get_report(report_number)

    owner_text = f"""𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫𝐧𝐚𝐦𝐞: {report["buyer_username"]}
𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫 𝐢𝐝: {report["buyer_id"]}
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {report_number}

𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝: {form["date_purchased"]}
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝: {form["date_reported"]}
𝐫𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐝𝐚𝐲𝐬: {remaining}
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝: ₱{amount_paid:.2f}
𝐚𝐦𝐨𝐮𝐧𝐭 𝐭𝐨 𝐛𝐞 𝐫𝐞𝐟𝐮𝐧𝐝𝐞𝐝: {("₱" + format(refund_amount, ".2f")) if refund_amount is not None else "manual review"}

𝐛𝐮𝐲𝐞𝐫'𝐬 𝐛𝐚𝐧𝐤 𝐝𝐞𝐭𝐚𝐢𝐥𝐬:
{context.user_data.get("refund_bank_text") or "bank details sent as photo"}

𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐩𝐚𝐲𝐦𝐞𝐧𝐭:
attached below

{refund_text}"""

    owner_message = await context.bot.send_message(
        OWNER_ID,
        owner_text,
        reply_markup=refund_owner_keyboard(report_number)
    )

    update_report(
        report_number,
        refund_owner_message_id=owner_message.message_id
    )

    bank_file = context.user_data.get(
        "refund_bank_file_id"
    )

    payment_file = context.user_data.get(
        "refund_payment_proof_file_id"
    )

    if bank_file:
        await context.bot.send_photo(
            OWNER_ID,
            bank_file,
            caption=f"buyer's bank details\nreport number: {report_number}"
        )

    if payment_file:
        await context.bot.send_photo(
            OWNER_ID,
            payment_file,
            caption=f"proof of payment\nreport number: {report_number}"
        )

    await query.message.reply_text(
        refund_text
    )

    context.user_data.clear()


async def refund_owner_callback(update, context):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    report_number = parts[1]
    action = parts[2]

    report = get_report(report_number)

    if not report:
        await query.message.reply_text(
            "report not found."
        )
        return

    if action == "sent":
        context.user_data.clear()
        context.user_data["owner_mode"] = "refund_receipt"
        context.user_data["owner_report_number"] = report_number

        await query.message.reply_text(
            """refund sent.

now send the refund receipt here as proof."""
        )

        return

    if action == "warning":
        context.user_data.clear()
        context.user_data["owner_mode"] = "refund_warning"
        context.user_data["owner_report_number"] = report_number

        await query.message.reply_text(
            "send the reason for the warning."
        )

        return

    if action == "voided":
        context.user_data.clear()
        context.user_data["owner_mode"] = "refund_voided"
        context.user_data["owner_report_number"] = report_number

        await query.message.reply_text(
            "send the reason for voiding the refund request."
        )

        return


async def warranty_callback(update, context):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")

    report_number = parts[1]
    action = parts[2]

    report = get_report(report_number)

    if not report:
        await query.message.reply_text(
            "report not found."
        )
        return

    if action == "activated":
        update_report(
            report_number,
            status="WARRANTY ACTIVATED"
        )

        await context.bot.send_message(
            report["buyer_id"],
            f"""report number: {report_number}

warranty activated.

thank you."""
        )

        await query.message.reply_text(
            "warranty activated and buyer notified."
        )

    elif action == "voided":
        update_report(
            report_number,
            status="WARRANTY VOIDED"
        )

        await context.bot.send_message(
            report["buyer_id"],
            f"""report number: {report_number}

warranty voided."""
        )

        await query.message.reply_text(
            "warranty voided and buyer notified."
        )


async def handle_buyer_text(update, context):
    text = update.message.text or ""

    # refund form
    if context.user_data.get("refund_mode") == "form":
        report_number = context.user_data.get(
            "refund_report_number"
        )

        data, missing = parse_refund_form(text)

        if data is None:
            await update.message.reply_text(
                f"""please check your refund form.

missing or invalid fields: {", ".join(missing)}

send the complete corrected refund form again."""
            )
            return True

        if data["report_number"].strip() != report_number:
            await update.message.reply_text(
                f"report number must be {report_number}."
            )
            return True

        context.user_data["refund_form_data"] = data
        context.user_data["refund_mode"] = "bank"

        await update.message.reply_text(
            """𝐲𝐨𝐮𝐫 𝐛𝐚𝐧𝐤 𝐝𝐞𝐭𝐚𝐢𝐥𝐬:

send a photo of your qr code or send your bank number and initials."""
        )

        return True

    # bank details as text
    if context.user_data.get("refund_mode") == "bank":
        context.user_data["refund_bank_text"] = text
        context.user_data["refund_mode"] = "payment_proof"

        await update.message.reply_text(
            """𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐩𝐚𝐲𝐦𝐞𝐧𝐭:

send a screenshot of our conversation showing the receipt you sent when you paid."""
        )

        return True

    # IMPORTANT:
    # if buyer selected a report category, treat the next text
    # message as the completed report form
    if context.user_data.get("report_category"):
        return await parse_and_store_buyer_form(
            update,
            context
        )

    return False


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if user.id == OWNER_ID:
        handled = await handle_owner_text(
            update,
            context
        )

        if handled:
            return

    handled = await handle_buyer_text(
        update,
        context
    )

    if handled:
        return

    if user.id == OWNER_ID:
        return


async def daily_status_job(context: ContextTypes.DEFAULT_TYPE):
    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM reports
        WHERE status IN ('SUBMITTED', 'PLEASE WAIT')
    """).fetchall()

    conn.close()

    today = today_ph()

    for report in rows:
        purchase = parse_date_value(
            report["date_purchased"]
        )

        remaining = calculate_remaining_days(
            purchase,
            report["days_availed"]
        )

        fixing = fixing_days_remaining(
            report["fixing_deadline"]
        )

        should_refund = (
            remaining is not None and remaining <= 0
        ) or fixing <= 0

        if should_refund:
            update_report(
                report["report_number"],
                status="FOR REFUND",
                last_update_date=str(today)
            )

            await context.bot.send_message(
                report["buyer_id"],
                f"""report number: {report["report_number"]}

status: FOR REFUND

the fixing period has ended or the subscription has reached 0 remaining days.

please wait for the refund instructions."""
            )

            await context.bot.send_message(
                OWNER_ID,
                f"""report number: {report["report_number"]}

status automatically changed to FOR REFUND.

remaining subscription days: {remaining}
fixing days remaining: {fixing}"""
            )

            continue

        last_update = report["last_update_date"]

        if last_update == str(today):
            continue

        update_report(
            report["report_number"],
            last_update_date=str(today)
        )

        await context.bot.send_message(
            report["buyer_id"],
            f"""report number: {report["report_number"]}

daily report update

status: {report["status"]}
fixing days remaining: {fixing}
remaining subscription days: {remaining}"""
        )

        await context.bot.send_message(
            OWNER_ID,
            f"""daily report update

report number: {report["report_number"]}
buyer: {report["buyer_username"]}
status: {report["status"]}
fixing days remaining: {fixing}
remaining subscription days: {remaining}"""
        )


async def warranty_deadline_job(context: ContextTypes.DEFAULT_TYPE):
    conn = db()

    rows = conn.execute("""
        SELECT *
        FROM reports
        WHERE status IN ('ACCOUNT FIXED', 'ACCOUNT REPLACED')
        AND warranty_deadline IS NOT NULL
    """).fetchall()

    conn.close()

    current = now_ph()

    for report in rows:
        try:
            deadline = datetime.fromisoformat(
                report["warranty_deadline"]
            )

            if deadline.tzinfo is None:
                deadline = deadline.replace(
                    tzinfo=TZ
                )

        except Exception:
            continue

        if current >= deadline:
            update_report(
                report["report_number"],
                status="WARRANTY VOIDED",
                warranty_deadline=None
            )

            await context.bot.send_message(
                report["buyer_id"],
                f"""report number: {report["report_number"]}

warranty voided.

the proof of login was not received within six hours."""
            )

            await context.bot.send_message(
                OWNER_ID,
                f"""report number: {report["report_number"]}

warranty automatically voided because the six-hour proof-of-login period ended."""
            )


async def error_handler(update, context):
    print(f"error: {context.error}")


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Add BOT_TOKEN in Railway Variables."
        )

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
        CallbackQueryHandler(
            category_callback,
            pattern=r"^cat_"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            submit_new_report,
            pattern=r"^submit_new_report$"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            owner_action_callback,
            pattern=r"^owner_action:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            send_action_callback,
            pattern=r"^send_action:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            reply_action_callback,
            pattern=r"^reply_action:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            refund_reason_callback,
            pattern=r"^refund_reason:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            refund_set_callback,
            pattern=r"^refund_set:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            refund_form_callback,
            pattern=r"^refund_form:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            refund_submit_callback,
            pattern=r"^refund_submit:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            refund_owner_callback,
            pattern=r"^refund_owner:"
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            warranty_callback,
            pattern=r"^warranty:"
        )
    )

    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            handle_photo
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text
        )
    )

    application.add_error_handler(error_handler)

    application.job_queue.run_repeating(
        daily_status_job,
        interval=3600,
        first=30
    )

    application.job_queue.run_repeating(
        warranty_deadline_job,
        interval=300,
        first=60
    )

    print("welcome to lanayanaliv's report area — the report bot is currently online.")

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
    
