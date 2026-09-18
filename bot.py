import os
import re
import sqlite3
import logging
import unicodedata
from datetime import datetime, date, timedelta
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "6054777664"))
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
    REFUND_FORM,
    WAITING_PAYMENT_PROOF,
) = range(7)

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

FORMS = {
    "Entertainment": """𝗘𝗡𝗧𝗘𝗥𝗧𝗔𝗜𝗡𝗠𝗘𝗡𝗧 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
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
    "Editing": """𝗘𝗗𝗜𝗧𝗜𝗡𝗚 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:

send the completed form here in one bubble chat only.""",
    "Educational": """𝗘𝗗𝗨𝗖𝗔𝗧𝗜𝗢𝗡𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦:
𝐞𝐦𝐚𝐢𝐥/𝐧𝐮𝐦𝐛𝐞𝐫:
𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:

send the completed form here in one bubble chat only.""",
    "Others": """𝗢𝗧𝗛𝗘𝗥𝗦/𝗚𝗘𝗡𝗘𝗥𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
𝐰𝐡𝐚𝐭 𝐩𝐫𝐨𝐝𝐮𝐜𝐭:
𝐩𝐫𝐨𝐝𝐮𝐜𝐭 𝐢𝐧𝐟𝐨𝐫𝐦𝐚𝐭𝐢𝐨𝐧:
𝐝𝐚𝐲𝐬 𝐚𝐯𝐚𝐢𝐥𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝:
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝐨𝐫𝐭𝐞𝐝:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:

send the completed form here in one bubble chat only.""",
}

REPLACEMENT_FORM = """𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗥𝗘𝗣𝗟𝗔𝗖𝗘𝗠𝗘𝗡𝗧
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫:
𝐧𝐞𝐰 𝐚𝐜𝐜𝐨𝐮𝐧𝐭:
𝐧𝐞𝐰 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝:
𝐧𝐞𝐰 𝐩𝐫𝐨𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐩𝐢𝐧:

𝐬𝐞𝐧𝐝 𝐲𝐨𝐮𝐫 𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐥𝐨𝐠 𝐢𝐧 𝐰𝐢𝐭𝐡𝐢𝐧 𝐟𝐨𝐮𝐫 𝐡𝐨𝐮𝐫𝐬 
𝐡𝐞𝐫𝐞 𝐢𝐧 𝐭𝐡𝐞 𝐛𝐨𝐭 𝐭𝐨 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞 𝐲𝐨𝐮𝐫 𝐰𝐚𝐫𝐫𝐚𝐧𝐭𝐲."""

CATEGORY_KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("Entertainment", callback_data="cat:Entertainment"), InlineKeyboardButton("Editing", callback_data="cat:Editing")],
    [InlineKeyboardButton("Educational", callback_data="cat:Educational"), InlineKeyboardButton("Others", callback_data="cat:Others")],
    [InlineKeyboardButton("Report Tutorial", url=TUTORIAL_URL)],
])


def db_connect():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def now_dt():
    return datetime.now()


def now_text():
    return now_dt().strftime("%Y-%m-%d %H:%M:%S")


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

    # migrations for existing reports database
    existing = {
        r[1]
        for r in conn.execute(
            "PRAGMA table_info(reports)"
        ).fetchall()
    }

    migrations = {
        "warranty_deadline":
            "ALTER TABLE reports ADD COLUMN warranty_deadline TEXT",

        "replacement_account":
            "ALTER TABLE reports ADD COLUMN replacement_account TEXT",

        "replacement_password":
            "ALTER TABLE reports ADD COLUMN replacement_password TEXT",

        "replacement_profile_pin":
            "ALTER TABLE reports ADD COLUMN replacement_profile_pin TEXT",

        "last_daily_notice":
            "ALTER TABLE reports ADD COLUMN last_daily_notice TEXT",
    }

    for col, sql in migrations.items():
        if col not in existing:
            conn.execute(sql)

    # migrations for existing refunds database
    refund_existing = {
        r[1]
        for r in conn.execute(
            "PRAGMA table_info(refunds)"
        ).fetchall()
    }

    refund_migrations = {
        "refund_receipt_file_id":
            "ALTER TABLE refunds ADD COLUMN refund_receipt_file_id TEXT",

        "refund_receipt_type":
            "ALTER TABLE refunds ADD COLUMN refund_receipt_type TEXT",
    }

    for col, sql in refund_migrations.items():
        if col not in refund_existing:
            conn.execute(sql)

    conn.commit()
    conn.close()

def get_report(report_no):
    conn = db_connect()
    row = conn.execute("SELECT * FROM reports WHERE report_no = ?", (report_no.upper(),)).fetchone()
    conn.close()
    return row


def get_report_by_id(report_id):
    conn = db_connect()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    return row


def get_latest_report_for_user(user_id):
    conn = db_connect()
    row = conn.execute("SELECT * FROM reports WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
    conn.close()
    return row


def get_active_warranty_report(user_id):
    now = now_dt()
    conn = db_connect()
    rows = conn.execute("""SELECT * FROM reports
        WHERE user_id = ?
        AND status IN ('ACCOUNT REPLACED', 'ACCOUNT FIXED')
        AND warranty_deadline IS NOT NULL
        ORDER BY id DESC""", (user_id,)).fetchall()
    conn.close()
    for row in rows:
        try:
            deadline = datetime.fromisoformat(row["warranty_deadline"])
        except (TypeError, ValueError):
            continue
        if deadline >= now:
            return row
    return None


def update_report(report_no, **fields):
    allowed = {
        "status", "issue_proof_file_id", "issue_proof_type", "vouch_proof_file_id",
        "vouch_proof_type", "subscription_remaining", "fixing_deadline", "owner_note",
        "updated_at", "warranty_deadline", "replacement_account", "replacement_password",
        "replacement_profile_pin", "last_daily_notice"
    }
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    fields["updated_at"] = now_text()
    sql = ", ".join(f"{k} = ?" for k in fields)
    conn = db_connect()
    conn.execute(f"UPDATE reports SET {sql} WHERE report_no = ?", list(fields.values()) + [report_no.upper()])
    conn.commit()
    conn.close()


def next_report_number():
    conn = db_connect()
    row = conn.execute("SELECT id FROM reports ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return f"R-{((row['id'] + 1) if row else 1):04d}"


def save_report(data):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""INSERT INTO reports (
        report_no,user_id,username,first_name,category,raw_form,product,amount_paid,
        days_availed,date_purchased,date_reported,subscription_remaining,status,
        issue_proof_file_id,issue_proof_type,vouch_proof_file_id,vouch_proof_type,
        created_at,updated_at,fixing_deadline,owner_note,warranty_deadline,
        replacement_account,replacement_password,replacement_profile_pin,last_daily_notice
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
        data["report_no"], data["user_id"], data.get("username", ""), data.get("first_name", ""),
        data["category"], data["raw_form"], data.get("product"), data.get("amount_paid"),
        data.get("days_availed"), data.get("date_purchased"), data.get("date_reported"),
        data.get("subscription_remaining"), data.get("status", "SUBMITTED"),
        data.get("issue_proof_file_id"), data.get("issue_proof_type"),
        data.get("vouch_proof_file_id"), data.get("vouch_proof_type"), now_text(), now_text(),
        data.get("fixing_deadline"), data.get("owner_note"), data.get("warranty_deadline"),
        data.get("replacement_account"), data.get("replacement_password"),
        data.get("replacement_profile_pin"), data.get("last_daily_notice")
    ))
    report_id = cur.lastrowid
    conn.commit()
    conn.close()
    return report_id


def save_user_report(user_id, report_no):
    conn = db_connect()
    conn.execute("INSERT INTO user_reports (user_id,report_no,last_contact_at) VALUES (?,?,?)", (user_id, report_no, now_text()))
    conn.commit()
    conn.close()


def norm(text):
    text = unicodedata.normalize("NFKC", text or "")
    return text.replace("’", "'").strip()


def value_after_labels(text, labels):
    for line in (text or "").splitlines():
        clean = norm(line)
        low = clean.lower()
        for label in sorted(labels, key=len, reverse=True):
            lab = norm(label).lower()
            if low.startswith(lab):
                value = clean[len(lab):].strip(" :|-\t")
                if value:
                    return value
    return None


DATE_FORMATS = ["%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%d/%Y", "%m-%d-%Y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"]


def parse_date(value):
    if not value:
        return None
    value = norm(value)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", value)
    if m:
        d, mth, y = map(int, m.groups())
        try:
            return date(y, mth, d)
        except ValueError:
            pass
    m = re.search(r"\b(\d{4})[/-](\d{1,2})[/-](\d{1,2})\b", value)
    if m:
        y, mth, d = map(int, m.groups())
        try:
            return date(y, mth, d)
        except ValueError:
            pass
    return None


def normalize_date(value):
    d = parse_date(value)
    return d.isoformat() if d else None


def parse_money(value):
    if not value:
        return None
    m = re.search(r"(\d+(?:\.\d{1,2})?)", norm(value).replace(",", ""))
    return float(m.group(1)) if m else None


def parse_days(value):
    if not value:
        return None
    m = re.search(r"\b(\d{1,4})\b", norm(value))
    if not m:
        return None
    n = int(m.group(1))
    return n if 0 < n <= 3660 else None


def calculate_remaining(purchased, validity, report_date=None):
    if not purchased or not validity:
        return None
    report_date = report_date or date.today()
    return max(0, (purchased + timedelta(days=validity) - report_date).days)


def parse_report_form(category, text):
    category = category.lower()
    r = {"product": None, "amount_paid": None, "days_availed": None, "date_purchased": None, "date_reported": None}
    if category == "entertainment":
        r.update({
            "product": value_after_labels(text, ["what premium", "premium"]),
            "email": value_after_labels(text, ["email/number", "email", "number"]),
            "password": value_after_labels(text, ["password"]),
            "profile_pin": value_after_labels(text, ["profile and pin", "profile"]),
            "days_availed": parse_days(value_after_labels(text, ["days availed", "days"])),
            "sharing": value_after_labels(text, ["shared/slp or sla", "shared/slp", "slp", "sla"]),
            "date_purchased": normalize_date(value_after_labels(text, ["date purchased", "purchase date"]) or ""),
            "amount_paid": parse_money(value_after_labels(text, ["amount paid", "amount"])),
            "specific_issue": value_after_labels(text, ["specific issue", "issue"]),
        })
    elif category in ("editing", "educational"):
        r.update({
            "product": value_after_labels(text, ["what premium", "premium"]),
            "email": value_after_labels(text, ["email/number", "email", "number"]),
            "password": value_after_labels(text, ["password"]),
            "days_availed": parse_days(value_after_labels(text, ["days availed", "days"])),
            "sharing": value_after_labels(text, ["shared/sla", "shared", "sla"]),
            "date_purchased": normalize_date(value_after_labels(text, ["date purchased", "purchase date"]) or ""),
            "amount_paid": parse_money(value_after_labels(text, ["amount paid", "amount"])),
            "specific_issue": value_after_labels(text, ["specific issue", "issue"]),
        })
    else:
        r.update({
            "product": value_after_labels(text, ["what product", "product"]),
            "product_information": value_after_labels(text, ["product information", "product info"]),
            "days_availed": parse_days(value_after_labels(text, ["days availed", "days"])),
            "date_purchased": normalize_date(value_after_labels(text, ["date purchased", "purchase date"]) or ""),
            "date_reported": normalize_date(value_after_labels(text, ["date reported", "report date"]) or ""),
            "amount_paid": parse_money(value_after_labels(text, ["amount paid", "amount"])),
            "specific_issue": value_after_labels(text, ["specific issue", "issue"]),
        })
    return r


def form_is_complete(parsed, category):
    if category == "Entertainment":
        keys = ["product", "email", "password", "profile_pin", "days_availed", "sharing", "date_purchased", "amount_paid", "specific_issue"]
    elif category in ("Editing", "Educational"):
        keys = ["product", "email", "password", "days_availed", "sharing", "date_purchased", "amount_paid", "specific_issue"]
    else:
        keys = ["product", "product_information", "days_availed", "date_purchased", "date_reported", "amount_paid", "specific_issue"]
    return all(parsed.get(k) not in (None, "") for k in keys)


REFUND_TIERS = {
    30: [(30,30,1.00),(25,29,.80),(20,24,.70),(15,19,.60),(10,14,.50),(6,9,.40)],
    60: [(60,60,1.00),(55,59,.80),(45,54,.70),(35,44,.60),(25,34,.50),(15,24,.40),(7,14,.30)],
    90: [(90,90,1.00),(78,89,.80),(69,77,.70),(59,68,.60),(49,58,.50),(39,48,.40),(29,38,.30),(19,28,.20),(7,18,.10)],
    120: [(120,120,1.00),(110,119,.80),(95,109,.70),(80,94,.60),(60,79,.50),(49,59,.40),(35,48,.30),(20,34,.20),(8,19,.10)],
    150: [(150,150,1.00),(130,149,.80),(110,129,.70),(90,109,.60),(70,89,.50),(50,69,.40),(30,49,.30),(15,29,.20),(11,14,.10)],
    180: [(180,180,1.00),(150,179,.80),(120,149,.70),(90,119,.60),(70,89,.50),(50,69,.40),(30,49,.30),(15,29,.20),(11,14,.10)],
    360: [(360,360,1.00),(340,359,.80),(320,339,.70),(300,319,.60),(250,299,.50),(200,249,.40),(150,199,.30),(100,149,.20),(50,99,.10),(11,49,.05)],
}


def refund_tier_for_validity(validity, remaining):
    if validity is None or remaining is None:
        return 0.0
    key = 30 if validity <= 30 else 60 if validity <= 60 else 90 if validity <= 90 else 120 if validity <= 120 else 150 if validity <= 150 else 180 if validity <= 180 else 360 if validity <= 360 else None
    if not key:
        return 0.0
    for low, high, fee in REFUND_TIERS[key]:
        if low <= remaining <= high:
            return fee
    return 0.0


def calculate_refund(amount, validity, remaining):
    fee = refund_tier_for_validity(validity, remaining)
    if amount is None or not validity or remaining is None:
        return fee, 0.0
    return fee, round((amount / validity) * remaining * fee, 2)


def refund_reason_keyboard(report_no):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("can't be fixed", callback_data=f"refundreason:{report_no}:cantfix")],
        [InlineKeyboardButton("can't be replaced", callback_data=f"refundreason:{report_no}:cantreplace")],
    ])


def owner_report_keyboard(report_no):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("report noted | please wait", callback_data=f"ownerstatus:{report_no}:pleasewait")],
        [InlineKeyboardButton("account replaced", callback_data=f"owner:replace:{report_no}"), InlineKeyboardButton("account fixed", callback_data=f"owner:fixed:{report_no}")],
        [InlineKeyboardButton("warning", callback_data=f"ownerstatus:{report_no}:warning"), InlineKeyboardButton("voided", callback_data=f"ownerstatus:{report_no}:voided")],
        [InlineKeyboardButton("can't fix/rep, for refund na", callback_data=f"ownerstatus:{report_no}:refund")],
        [InlineKeyboardButton("reply", callback_data=f"owner:reply:{report_no}")],
    ])


def send_choice_keyboard(report_no, action):
    return InlineKeyboardMarkup([[InlineKeyboardButton("send as is", callback_data=f"sendas:{report_no}:{action}"), InlineKeyboardButton("reply first", callback_data=f"replyfirst:{report_no}:{action}")]])


def warranty_keyboard(report_no):
    return InlineKeyboardMarkup([[InlineKeyboardButton("Warranty Activated", callback_data=f"warranty:{report_no}:activated"), InlineKeyboardButton("Warranty Voided", callback_data=f"warranty:{report_no}:voided")]])


def owner_only(user_id):
    return user_id == OWNER_ID


async def start(update, context):
    context.user_data.clear()
    await update.effective_chat.send_message(WELCOME_TEXT, reply_markup=CATEGORY_KEYBOARD)
    return CHOOSING_CATEGORY


async def category_callback(update, context):
    q = update.callback_query
    await q.answer()
    category = q.data.split(":", 1)[1]
    context.user_data["category"] = category
    await q.message.edit_text(FORMS[category])
    return ENTERING_FORM


async def form_message(update, context):
    category = context.user_data.get("category")
    if not category:
        await update.message.reply_text("please choose a report category first.", reply_markup=CATEGORY_KEYBOARD)
        return CHOOSING_CATEGORY
    parsed = parse_report_form(category, update.message.text or "")
    if not form_is_complete(parsed, category):
        await update.message.reply_text("please check your form and send the complete form again in one bubble chat only.")
        return ENTERING_FORM
    context.user_data["raw_form"] = update.message.text
    context.user_data["parsed"] = parsed
    await update.message.reply_text("form received.\n\nplease send your proof of issue screenshot.")
    return WAITING_ISSUE_PROOF


def media_file(message):
    if message.photo:
        return message.photo[-1].file_id, "photo"
    if message.document:
        return message.document.file_id, "document"
    return None, None


async def issue_proof_message(update, context):
    fid, ftype = media_file(update.message)
    if not fid:
        await update.message.reply_text("please send your proof of issue as a photo or document.")
        return WAITING_ISSUE_PROOF
    context.user_data["issue_proof_file_id"] = fid
    context.user_data["issue_proof_type"] = ftype
    await update.message.reply_text("proof of issue received.\n\nnow send your proof of vouch screenshot.")
    return WAITING_VOUCH_PROOF


async def vouch_proof_message(update, context):
    fid, ftype = media_file(update.message)
    if not fid:
        await update.message.reply_text("please send your proof of vouch as a photo or document.")
        return WAITING_VOUCH_PROOF
    context.user_data["vouch_proof_file_id"] = fid
    context.user_data["vouch_proof_type"] = ftype
    await update.message.reply_text("both proofs received.\n\nyour report is ready to submit.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("submit", callback_data="submit_pending")]]))
    return WAITING_SUBMIT


def owner_report_text(row):
    amount = f"₱{row['amount_paid']:.2f}" if row["amount_paid"] is not None else "not parsed"
    return f"""𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫𝐧𝐚𝐦𝐞: @{row['username'] or 'no_username'}
𝐛𝐮𝐲𝐞𝐫'𝐬 𝐮𝐬𝐞𝐫 𝐢𝐝: {row['user_id']}
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {row['report_no']}

𝐰𝐡𝐚𝐭 𝐩𝐫𝐞𝐦𝐢𝐮𝐦: {row['product'] or 'not parsed'}
𝐬𝐡𝐚𝐫𝐞𝐝/𝐬𝐥𝐚/𝐬𝐥𝐩: {extract_sharing(row['raw_form']) or 'not parsed'}
𝐝𝐚𝐭𝐞 𝐩𝐮𝐫𝐜𝐡𝐚𝐬𝐞𝐝: {row['date_purchased'] or 'not parsed'}
𝐫𝐞𝐦𝐚𝐢𝐧𝐢𝐧𝐠 𝐝𝐚𝐲𝐬: {row['subscription_remaining'] if row['subscription_remaining'] is not None else 'not available'}
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝: {amount}
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞: {extract_issue(row['raw_form']) or 'not parsed'}

𝐬𝐭𝐚𝐭𝐮𝐬: {row['status']}"""


def extract_sharing(raw):
    return value_after_labels(raw, ["shared/slp or sla", "shared/slp", "shared/sla", "shared"])


def extract_issue(raw):
    return value_after_labels(raw, ["specific issue", "issue"])


async def send_owner_proof(context, row, file_id, file_type, caption):
    if file_type == "photo":
        await context.bot.send_photo(OWNER_ID, file_id, caption=caption)
    else:
        await context.bot.send_document(OWNER_ID, file_id, caption=caption)


async def notify_owner(context, row):
    await context.bot.send_message(OWNER_ID, owner_report_text(row), reply_markup=owner_report_keyboard(row["report_no"]))
    if row["issue_proof_file_id"]:
        await send_owner_proof(context, row, row["issue_proof_file_id"], row["issue_proof_type"], f"{row['report_no']} - proof of issue")
    if row["vouch_proof_file_id"]:
        await send_owner_proof(context, row, row["vouch_proof_file_id"], row["vouch_proof_type"], f"{row['report_no']} - proof of vouch")


async def submit_pending_callback(update, context):
    q = update.callback_query
    await q.answer()
    user = update.effective_user
    category = context.user_data.get("category")
    parsed = context.user_data.get("parsed", {})
    raw = context.user_data.get("raw_form", "")
    if not category or not raw or not form_is_complete(parsed, category):
        await q.message.reply_text("your report session expired. please start again with /start.")
        return ConversationHandler.END
    report_no = next_report_number()
    purchased = parse_date(parsed["date_purchased"])
    reported = parse_date(parsed.get("date_reported")) or date.today()
    remaining = calculate_remaining(purchased, parsed["days_availed"], reported)
    fixing_deadline = now_dt() + timedelta(days=7)
    safe_form = re.sub(r"(?im)^(\s*password\s*:\s*).*$", r"\1[redacted]", raw)
    report_id = save_report({
        "report_no": report_no, "user_id": user.id, "username": user.username or "", "first_name": user.first_name or "",
        "category": category, "raw_form": safe_form, "product": parsed.get("product"), "amount_paid": parsed.get("amount_paid"),
        "days_availed": parsed.get("days_availed"), "date_purchased": purchased.isoformat(), "date_reported": reported.isoformat(),
        "subscription_remaining": remaining, "status": "SUBMITTED", "issue_proof_file_id": context.user_data.get("issue_proof_file_id"),
        "issue_proof_type": context.user_data.get("issue_proof_type"), "vouch_proof_file_id": context.user_data.get("vouch_proof_file_id"),
        "vouch_proof_type": context.user_data.get("vouch_proof_type"), "fixing_deadline": fixing_deadline.isoformat()
    })
    save_user_report(user.id, report_no)
    await q.message.reply_text(f"report submitted successfully.\n\nreport number: {report_no}\nstatus: SUBMITTED\nfixing period: 0-7 days\nsubscription days remaining at report: {remaining if remaining is not None else 'not available'}")
    row = get_report_by_id(report_id)
    await notify_owner(context, row)
    if remaining == 0:
        await move_to_refund(context, row)
    context.user_data.clear()
    return ConversationHandler.END


async def owner_status_callback(update, context):
    q = update.callback_query
    await q.answer()
    if not owner_only(update.effective_user.id):
        return
    _, report_no, action = q.data.split(":")
    row = get_report(report_no)
    if not row:
        await q.message.reply_text("report not found.")
        return
    if action in ("pleasewait", "warning", "voided"):
        await q.message.reply_text(f"{report_no}: choose how to send the {action} update.", reply_markup=send_choice_keyboard(report_no, action))
    elif action == "refund":
        await set_refund(context, row, q.message)


async def send_status_update(context, report_no, action, custom_text=None):
    row = get_report(report_no)
    if not row:
        return
    if action == "pleasewait":
        status = "SUBMITTED"
        default = f"report {report_no} update:\n\nstatus: REPORT NOTED | PLEASE WAIT\n\nplease wait within the 0-7 days fixing period."
    elif action == "warning":
        status = "WARNING"
        default = "first mistake and first direct to owner report = warning\n\nthis is a warning."
    else:
        status = "VOIDED"
        default = "second mistake and second direct to owner report = voided\n\nyour report/warranty is VOIDED."
    update_report(report_no, status=status)
    await context.bot.send_message(row["user_id"], custom_text or default)


async def send_as_is_callback(update, context):
    q = update.callback_query
    await q.answer()
    if not owner_only(update.effective_user.id):
        return
    _, report_no, action = q.data.split(":")
    await send_status_update(context, report_no, action)
    await q.message.reply_text(f"{report_no} update sent as is.")


async def reply_first_callback(update, context):
    q = update.callback_query
    await q.answer()
    if not owner_only(update.effective_user.id):
        return
    _, report_no, action = q.data.split(":")
    context.user_data["owner_custom_action"] = action
    context.user_data["owner_custom_report"] = report_no
    await q.message.reply_text(f"reply first for {report_no}. send your custom message now.")


async def owner_action_callback(update, context):
    q = update.callback_query
    await q.answer()
    if not owner_only(update.effective_user.id):
        return
    parts = q.data.split(":")
    action, report_no = parts[1], parts[2]
    row = get_report(report_no)
    if not row:
        await q.message.reply_text("report not found.")
        return
    if action == "replace":
        context.user_data.clear()
        context.user_data["owner_mode"] = "replacement"
        context.user_data["owner_report_number"] = report_no
        await q.message.reply_text(REPLACEMENT_FORM)
        return
    if action == "fixed":
        update_report(report_no, status="ACCOUNT FIXED")
        await context.bot.send_message(row["user_id"], f"report number: {report_no}\n\naccount fixed.")
        await q.message.reply_text(f"{report_no} marked as ACCOUNT FIXED.")
        return
    if action == "reply":
        context.user_data["owner_custom_action"] = "reply"
        context.user_data["owner_custom_report"] = report_no
        await q.message.reply_text(f"reply mode for {report_no}.\n\nsend your message now.")


async def warranty_callback(update, context):
    q = update.callback_query
    await q.answer()
    if not owner_only(update.effective_user.id):
        return
    _, report_no, action = q.data.split(":")
    row = get_report(report_no)
    if not row:
        await q.message.reply_text("report not found.")
        return
    if action == "activated":
        update_report(report_no, status="WARRANTY ACTIVATED")
        await context.bot.send_message(row["user_id"], f"report number: {report_no}\n\nwarranty activated.")
    else:
        update_report(report_no, status="WARRANTY VOIDED")
        await context.bot.send_message(row["user_id"], f"report number: {report_no}\n\nwarranty voided.")
    await q.edit_message_reply_markup(reply_markup=None)


async def warranty_proof_message(update, context):
    if update.effective_user.id == OWNER_ID:
        return
    row = get_active_warranty_report(update.effective_user.id)
    if not row:
        return
    fid, ftype = media_file(update.message)
    if not fid:
        await update.message.reply_text("please send your proof of login as a photo or document.")
        return
    try:
        await send_owner_proof(context, row, fid, ftype, f"{row['report_no']} - proof of login\nbuyer user id: {update.effective_user.id}")
        await context.bot.send_message(OWNER_ID, f"proof of login received.\n\nreport number: {row['report_no']}\nbuyer username: @{update.effective_user.username or 'no_username'}\nwarranty deadline: {row['warranty_deadline']}", reply_markup=warranty_keyboard(row["report_no"]))
        await update.message.reply_text(f"proof of login received for report {row['report_no']}. please wait for the warranty update.")
    except Exception:
        logger.exception("Could not forward proof of login")
        await update.message.reply_text("your proof of login could not be sent right now. please send it again.")


async def owner_text_message(update, context):
    if not owner_only(update.effective_user.id):
        return
    text = update.message.text or ""
    mode = context.user_data.get("owner_mode")
    if mode == "replacement":
        report_no = context.user_data.get("owner_report_number")
        fields = {
            "report_number": value_after_labels(text, ["report number"]),
            "new_account": value_after_labels(text, ["new account"]),
            "new_password": value_after_labels(text, ["new password"]),
            "new_profile_and_pin": value_after_labels(text, ["new profile and pin", "new profile pin"]),
        }
        missing = [k for k, v in fields.items() if not v]
        if missing:
            await update.message.reply_text(f"please check the account replacement form.\n\nmissing fields: {', '.join(missing)}\n\nsend the complete corrected form again.")
            return
        if fields["report_number"].strip().upper() != report_no:
            await update.message.reply_text(f"report number must be {report_no}.")
            return
        row = get_report(report_no)
        if not row:
            await update.message.reply_text("report not found.")
            context.user_data.clear()
            return
        deadline = now_dt() + timedelta(hours=4)
        update_report(report_no, status="ACCOUNT REPLACED", warranty_deadline=deadline.isoformat(), replacement_account=fields["new_account"], replacement_password=fields["new_password"], replacement_profile_pin=fields["new_profile_and_pin"])
        msg = f"""𝗔𝗖𝗖𝗢𝗨𝗡𝗧 𝗥𝗘𝗣𝗟𝗔𝗖𝗘𝗠𝗘𝗡𝗧
𝐫𝐞𝐩𝐨𝐫𝐭 𝐧𝐮𝐦𝐛𝐞𝐫: {report_no}
𝐧𝐞𝐰 𝐚𝐜𝐜𝐨𝐮𝐧𝐭: {fields['new_account']}
𝐧𝐞𝐰 𝐩𝐚𝐬𝐬𝐰𝐨𝐫𝐝: {fields['new_password']}
𝐧𝐞𝐰 𝐩𝐫𝐨𝐟𝐢𝐥𝐞 𝐚𝐧𝐝 𝐩𝐢𝐧: {fields['new_profile_and_pin']}

𝐬𝐞𝐧𝐝 𝐲𝐨𝐮𝐫 𝐩𝐫𝐨𝐨𝐟 𝐨𝐟 𝐥𝐨𝐠 𝐢𝐧 𝐰𝐢𝐭𝐡𝐢𝐧 𝐟𝐨𝐮𝐫 𝐡𝐨𝐮𝐫𝐬 
𝐡𝐞𝐫𝐞 𝐢𝐧 𝐭𝐡𝐞 𝐛𝐨𝐭 𝐭𝐨 𝐚𝐜𝐭𝐢𝐯𝐚𝐭𝐞 𝐲𝐨𝐮𝐫 𝐰𝐚𝐫𝐫𝐚𝐧𝐭𝐲."""
        await context.bot.send_message(row["user_id"], msg)
        await update.message.reply_text(f"{report_no} replacement sent to buyer. warranty deadline: {deadline.strftime('%Y-%m-%d %H:%M')}")
        context.user_data.clear()
        return
    action = context.user_data.get("owner_custom_action")
    report_no = context.user_data.get("owner_custom_report")
    if not action or not report_no:
        return
    row = get_report(report_no)
    if not row:
        await update.message.reply_text("report not found.")
        context.user_data.clear()
        return
    if action == "reply":
        await context.bot.send_message(row["user_id"], f"message from lanayanaliv regarding report {report_no}:\n\n{text}")
        await update.message.reply_text("message sent.")
    else:
        await send_status_update(context, report_no, action, custom_text=text)
        await update.message.reply_text(f"{report_no} custom update sent.")
    context.user_data.clear()


async def set_refund(context, row, message):
    update_report(row["report_no"], status="FOR REFUND")
    await context.bot.send_message(row["user_id"], f"report {row['report_no']} update:\n\nstatus: FOR REFUND\n\nplease choose your reason below.", reply_markup=refund_reason_keyboard(row["report_no"]))
    await message.reply_text(f"{row['report_no']} marked as FOR REFUND.")


async def move_to_refund(context, row):
    if row["status"] == "FOR REFUND":
        return
    update_report(row["report_no"], status="FOR REFUND")
    try:
        await context.bot.send_message(row["user_id"], f"report {row['report_no']} update:\n\nstatus: FOR REFUND\n\nthe fixing period or subscription period has ended. please choose your refund reason below.", reply_markup=refund_reason_keyboard(row["report_no"]))
        await context.bot.send_message(OWNER_ID, f"report {row['report_no']} is now FOR REFUND because the fixing/subscription period ended.")
    except Exception:
        logger.exception("refund notification failed")


async def refund_reason_callback(update, context):
    q = update.callback_query
    await q.answer()
    parts = q.data.split(":")
    report_no, code = parts[1], parts[2]
    row = get_report(report_no)
    if not row or row["user_id"] != update.effective_user.id:
        await q.message.reply_text("this refund request does not belong to you.")
        return ConversationHandler.END
    context.user_data["refund_report_no"] = report_no
    context.user_data["refund_reason"] = "can't be fixed" if code == "cantfix" else "can't be replaced"
    await q.message.reply_text("""refund form:

report number:
date purchased:
date reported:
amount paid:
account/product:
days availed:
user's bank details:

send the completed refund form in one bubble chat only.""")
    return REFUND_FORM


async def refund_form_message(update, context):
    report_no = context.user_data.get("refund_report_no")
    row = get_report(report_no) if report_no else None
    if not row:
        await update.message.reply_text("refund session expired. please contact the owner.")
        return ConversationHandler.END
    text = update.message.text or ""
    parsed = {
        "date_purchased": normalize_date(value_after_labels(text, ["date purchased", "purchase date"]) or "") or row["date_purchased"],
        "date_reported": normalize_date(value_after_labels(text, ["date reported", "report date"]) or "") or row["date_reported"],
        "amount_paid": parse_money(value_after_labels(text, ["amount paid", "amount"])) or row["amount_paid"],
        "account_product": value_after_labels(text, ["account/product", "account", "product"]) or row["product"],
        "days_availed": parse_days(value_after_labels(text, ["days availed", "days"])) or row["days_availed"],
        "bank_details": value_after_labels(text, ["user's bank details", "users bank details", "bank details", "bank"]),
    }
    required = [parsed["date_purchased"], parsed["date_reported"], parsed["amount_paid"], parsed["account_product"], parsed["days_availed"], parsed["bank_details"]]
    if any(x in (None, "") for x in required):
        await update.message.reply_text("please send the complete refund form again in one bubble chat only.")
        return REFUND_FORM
    purchased = parse_date(parsed["date_purchased"])
    reported = parse_date(parsed["date_reported"]) or date.today()
    remaining = calculate_remaining(purchased, parsed["days_availed"], reported)
    fee, refund = calculate_refund(parsed["amount_paid"], parsed["days_availed"], remaining)
    context.user_data.update(refund_form=text, refund_parsed=parsed, refund_remaining=remaining, refund_service_fee=fee, refund_amount=refund)
    await update.message.reply_text("refund form received.\n\nproof of payment\n\nsend your proof of payment screenshot or document.")
    return WAITING_PAYMENT_PROOF


async def payment_proof_message(update, context):
    report_no = context.user_data.get("refund_report_no")
    row = get_report(report_no) if report_no else None

    if not row:
        await update.message.reply_text(
            "refund session expired."
        )
        return ConversationHandler.END

    fid, ftype = media_file(update.message)

    if not fid:
        await update.message.reply_text(
            "please send your proof of payment as a photo or document."
        )
        return WAITING_PAYMENT_PROOF

    parsed = context.user_data.get("refund_parsed", {})
    remaining = context.user_data.get("refund_remaining")
    fee = context.user_data.get("refund_service_fee", 0.0)
    refund = context.user_data.get("refund_amount", 0.0)

    conn = db_connect()

    conn.execute(
        """INSERT INTO refunds
        (
            report_id,
            report_no,
            reason,
            refund_form,
            amount_paid,
            validity_days,
            remaining_days,
            service_fee,
            refund_amount,
            bank_details,
            payment_proof_file_id,
            payment_proof_type,
            status,
            created_at,
            updated_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            row["id"],
            report_no,
            context.user_data.get("refund_reason"),
            context.user_data.get("refund_form", ""),
            parsed.get("amount_paid"),
            parsed.get("days_availed"),
            remaining,
            fee,
            refund,
            parsed.get("bank_details"),
            fid,
            ftype,
            "PENDING OWNER REVIEW",
            now_text(),
            now_text()
        )
    )

    conn.commit()
    conn.close()

    update_report(
        report_no,
        status="FOR REFUND"
    )

    await update.message.reply_text(
        f"""refund request submitted.

report number: {report_no}
reason: {context.user_data.get('refund_reason')}
remaining days: {remaining}
service fee: {fee:.2f}
computed refund: ₱{refund:.2f}

your refund request and proof of payment have been sent to the owner for review."""
    )

    await context.bot.send_message(
        OWNER_ID,
        f"""refund request

report number: {report_no}
buyer username: @{row['username'] or 'no_username'}
buyer user id: {row['user_id']}
reason: {context.user_data.get('refund_reason')}
date purchased: {parsed['date_purchased']}
date reported: {parsed['date_reported']}
amount paid: ₱{parsed['amount_paid']:.2f}
account/product: {parsed['account_product']}
days availed: {parsed['days_availed']}
remaining days: {remaining}
service fee: {fee:.2f}
async def payment_proof_message(update, context):
    report_no = context.user_data.get("refund_report_no")
    row = get_report(report_no) if report_no else None

    if not row:
        await update.message.reply_text(
            "refund session expired."
        )
        return ConversationHandler.END

    fid, ftype = media_file(update.message)

    if not fid:
        await update.message.reply_text(
            "please send your proof of payment as a photo or document."
        )
        return WAITING_PAYMENT_PROOF

    parsed = context.user_data.get("refund_parsed", {})
    remaining = context.user_data.get("refund_remaining")
    fee = context.user_data.get("refund_service_fee", 0.0)
    refund = context.user_data.get("refund_amount", 0.0)
    reason = context.user_data.get("refund_reason")

    conn = db_connect()

    conn.execute(
        """
        INSERT INTO refunds (
            report_id,
            report_no,
            reason,
            refund_form,
            amount_paid,
            validity_days,
            remaining_days,
            service_fee,
            refund_amount,
            bank_details,
            payment_proof_file_id,
            payment_proof_type,
            status,
            created_at,
            updated_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            row["id"],
            report_no,
            reason,
            context.user_data.get("refund_form", ""),
            parsed.get("amount_paid"),
            parsed.get("days_availed"),
            remaining,
            fee,
            refund,
            parsed.get("bank_details"),
            fid,
            ftype,
            "PENDING OWNER REVIEW",
            now_text(),
            now_text(),
        ),
    )

    conn.commit()
    conn.close()

    update_report(
        report_no,
        status="FOR REFUND"
    )

    await update.message.reply_text(
        f"""refund request submitted.

report number: {report_no}
reason: {reason}
remaining days: {remaining}
service fee: {fee:.2f}
computed refund: ₱{refund:.2f}

your refund request and proof of payment have been sent to the owner for review."""
    )

    owner_refund_text = (
        f"""refund request

report number: {report_no}
buyer username: @{row['username'] or 'no_username'}
buyer user id: {row['user_id']}

reason: {reason}

date purchased: {parsed.get('date_purchased', 'not available')}
date reported: {parsed.get('date_reported', 'not available')}
amount paid: ₱{float(parsed.get('amount_paid', 0)):.2f}
account/product: {parsed.get('account_product', 'not available')}
days availed: {parsed.get('days_availed', 'not available')}
remaining days: {remaining}
service fee: {fee:.2f}
computed refund: ₱{refund:.2f}
bank details: {parsed.get('bank_details', 'not available')}

status: PENDING OWNER REVIEW"""
    )

    await context.bot.send_message(
        chat_id=OWNER_ID,
        text=owner_refund_text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "refund sent",
                        callback_data=f"refundaction:{report_no}:sent",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "warning, wrong details/format",
                        callback_data=f"refundaction:{report_no}:warning",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "voided, wrong details/format",
                        callback_data=f"refundaction:{report_no}:voided",
                    )
                ],
            ]
        ),
    )

    await send_owner_proof(
        context,
        row,
        fid,
        ftype,
        f"{report_no} - proof of payment",
    )

    context.user_data.clear()

    return ConversationHandler.END


async def update_countdowns(context):
    conn = db_connect()
    rows = conn.execute("SELECT * FROM reports WHERE status IN ('SUBMITTED','WARNING')").fetchall()
    conn.close()
    today = date.today()
    for row in rows:
        purchased = parse_date(row["date_purchased"])
        remaining = calculate_remaining(purchased, row["days_availed"], today)
        update_report(row["report_no"], subscription_remaining=remaining)
        if remaining == 0:
            await move_to_refund(context, get_report(row["report_no"]))
            continue
        deadline = None
        try:
            deadline = datetime.fromisoformat(row["fixing_deadline"]) if row["fixing_deadline"] else None
        except ValueError:
            pass
        if deadline and now_dt() >= deadline:
            await move_to_refund(context, get_report(row["report_no"]))
            continue
        last = row["last_daily_notice"]
        if row["status"] == "SUBMITTED" and (not last or last != today.isoformat()):
            try:
                await context.bot.send_message(row["user_id"], f"report {row['report_no']} update:\n\nstatus: REPORT NOTED | PLEASE WAIT\nsubscription days remaining: {remaining}\nfixing period: 0-7 days")
                update_report(row["report_no"], last_daily_notice=today.isoformat())
            except Exception:
                logger.exception("daily update failed")


async def error_handler(update, context):
    logger.exception("Unhandled exception", exc_info=context.error)


def build_application():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set in Railway Variables.")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    report_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start), CallbackQueryHandler(category_callback, pattern=r"^cat:")],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(category_callback, pattern=r"^cat:")],
            ENTERING_FORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, form_message)],
            WAITING_ISSUE_PROOF: [MessageHandler(filters.PHOTO | filters.Document.ALL, issue_proof_message)],
            WAITING_VOUCH_PROOF: [MessageHandler(filters.PHOTO | filters.Document.ALL, vouch_proof_message)],
            WAITING_SUBMIT: [CallbackQueryHandler(submit_pending_callback, pattern=r"^submit_pending$")],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )
    refund_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(refund_reason_callback, pattern=r"^refundreason:")],
        states={
            REFUND_FORM: [MessageHandler(filters.TEXT & ~filters.COMMAND, refund_form_message)],
            WAITING_PAYMENT_PROOF: [MessageHandler(filters.PHOTO | filters.Document.ALL, payment_proof_message)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )
    app.add_handler(report_conv)
    app.add_handler(refund_conv)
    app.add_handler(CallbackQueryHandler(owner_status_callback, pattern=r"^ownerstatus:"))
    app.add_handler(CallbackQueryHandler(send_as_is_callback, pattern=r"^sendas:"))
    app.add_handler(CallbackQueryHandler(reply_first_callback, pattern=r"^replyfirst:"))
    app.add_handler(CallbackQueryHandler(owner_action_callback, pattern=r"^owner:"))
    app.add_handler(CallbackQueryHandler(warranty_callback, pattern=r"^warranty:"))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, warranty_proof_message), group=5)
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("reply", cmd_reply))
    app.add_handler(CommandHandler("myreport", cmd_myreport))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, owner_text_message), group=10)
    app.add_error_handler(error_handler)
    app.job_queue.run_repeating(update_countdowns, interval=3600, first=60)
    return app


def main():
    init_db()
    app = build_application()
    logger.info("lanayanaliv report bot is online")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=False)


if __name__ == "__main__":
    main()
