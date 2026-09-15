import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_ID = 6054777664
DB_FILE = "reports.db"
TUTORIAL_URL = "https://t.me/lanareports"

WELCOME = """welcome to lanayanaliv's report page
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
report directly to the owner = voided
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
    "educational": """𝗘𝗗𝗨𝗖𝗔𝗧𝗜𝗢𝗡𝗔𝗟 𝗥𝗘𝗣𝗢𝗥𝗧 𝗙𝗢𝗥𝗠
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
𝐝𝐚𝐭𝐞 𝐫𝐞𝐩𝗼𝗿𝘁𝗲𝗱:
𝐚𝐦𝐨𝐮𝐧𝐭 𝐩𝐚𝐢𝐝:
𝐬𝐩𝐞𝐜𝐢𝐟𝐢𝐜 𝐢𝐬𝐬𝐮𝐞:""",
}

CATEGORY_LABELS = {
    "entertainment": "entertainment",
    "editing": "editing",
    "educational": "educational",
    "others": "others",
}

def db():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        warnings INTEGER NOT NULL DEFAULT 0,
        voided INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        category TEXT NOT NULL,
        form_text TEXT NOT NULL,
        password TEXT,
        amount_paid REAL,
        days_availed INTEGER,
        date_purchased TEXT,
        date_reported TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'SUBMITTED',
        fixing_until TEXT,
        proof_vouch_file_id TEXT,
        proof_issue_file_id TEXT,
        refund_submitted INTEGER NOT NULL DEFAULT 0,
        refund_bank_details TEXT,
        refund_proof_file_id TEXT,
        created_at TEXT NOT NULL
    );
    """)
    con.commit()
    con.close()

def ensure_user(user):
    con = db()
    con.execute(
        """INSERT INTO users(user_id, username) VALUES(?, ?)
           ON CONFLICT(user_id) DO UPDATE SET username=excluded.username""",
        (user.id, user.username or ""),
    )
    con.commit()
    con.close()

def get_user(user_id):
    con = db()
    row = con.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    return row

def add_warning(user_id, username):
    con = db()
    con.execute(
        """INSERT INTO users(user_id, username, warnings)
           VALUES(?, ?, 1)
           ON CONFLICT(user_id) DO UPDATE SET
           warnings=warnings+1, username=excluded.username""",
        (user_id, username or ""),
    )
    row = con.execute("SELECT warnings FROM users WHERE user_id=?", (user_id,)).fetchone()
    warnings = row["warnings"]
    voided = 1 if warnings >= 2 else 0
    con.execute("UPDATE users SET voided=? WHERE user_id=?", (voided, user_id))
    con.commit()
    con.close()
    return warnings, voided

def normalize_text(s):
    # Unicode mathematical bold/italic letters are converted to their normal forms
    return s.translate(str.maketrans(
        "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙",
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )).replace("𝗼", "o").replace("𝗿", "r")

def parse_form(text, category):
    n = normalize_text(text).lower()
    lines = [x.strip() for x in n.splitlines() if x.strip()]
    data = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()

    if category == "others":
        required = [
            "what product", "product information", "days availed",
            "date purchased", "date reported", "amount paid", "specific issue"
        ]
    elif category == "entertainment":
        required = [
            "what premium", "email/number", "password", "profile and pin",
            "days availed", "shared/slp or sla", "date purchased",
            "amount paid", "specific issue"
        ]
    else:
        required = [
            "what premium", "email/number", "password", "days availed",
            "shared/slp", "date purchased", "amount paid", "specific issue"
        ]

    missing = [k for k in required if not data.get(k)]
    return data, missing

def parse_amount(value):
    m = re.search(r"[\d,]+(?:\.\d+)?", value.replace("₱", ""))
    return float(m.group().replace(",", "")) if m else None

def parse_days(value):
    m = re.search(r"\d+", value)
    return int(m.group()) if m else None

def parse_date(value):
    formats = [
        "%B %d, %Y", "%b %d, %Y",
        "%B %d %Y", "%b %d %Y",
        "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y",
        "%d/%m/%Y", "%d-%m-%Y",
    ]
    v = value.strip()
    for fmt in formats:
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    return None

def fmt_money(x):
    return f"₱{x:,.2f}".replace(".00", "")

def remaining_days(date_purchased, days_availed, date_reported):
    if not date_purchased or not days_availed or not date_reported:
        return None
    expiration = date_purchased + timedelta(days=days_availed)
    return max(0, (expiration - date_reported).days)

SERVICE_FEES = {
    1: [(30, 30, 1.00), (25, 29, .80), (20, 24, .70), (15, 19, .60), (10, 14, .50), (6, 9, .40)],
    2: [(60, 60, 1.00), (55, 59, .80), (45, 54, .70), (35, 44, .60), (25, 34, .50), (15, 24, .40), (7, 14, .30)],
    3: [(90, 90, 1.00), (78, 89, .80), (69, 77, .70), (59, 68, .60), (49, 58, .50), (39, 48, .40), (29, 38, .30), (19, 28, .20), (7, 18, .10)],
    4: [(120, 120, 1.00), (110, 119, .80), (95, 109, .70), (80, 94, .60), (60, 79, .50), (49, 59, .40), (35, 48, .30), (20, 34, .20), (8, 19, .10)],
    5: [(150, 150, 1.00), (130, 149, .80), (110, 129, .70), (90, 109, .60), (70, 89, .50), (50, 69, .40), (30, 49, .30), (15, 29, .20), (11, 14, .10)],
}

def service_fee(months, remaining):
    for lo, hi, fee in SERVICE_FEES.get(months, []):
        if lo <= remaining <= hi:
            return fee
    return None

def detect_months(days):
    if days is None:
        return None
    if days <= 30:
        return 1
    if days <= 60:
        return 2
    if days <= 90:
        return 3
    if days <= 120:
        return 4
    if days <= 150:
        return 5
    return None

def refund_calc(amount, validity, remaining):
    months = detect_months(validity)
    if amount is None or not validity or remaining is None or months is None:
        return None, None, "unable to determine refund parameters"
    fee = service_fee(months, remaining)
    if fee is None:
        return None, None, "no service-fee rule exists for this remaining-day range"
    refund = (amount / validity) * remaining * fee
    return refund, fee, None

def days_left_from_iso(iso):
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso)
        return max(0, (dt.date() - datetime.now(timezone.utc).date()).days)
    except Exception:
        return None

def category_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("entertainment", callback_data="cat:entertainment")],
        [InlineKeyboardButton("editing", callback_data="cat:editing")],
        [InlineKeyboardButton("educational", callback_data="cat:educational")],
        [InlineKeyboardButton("others", callback_data="cat:others")],
        [InlineKeyboardButton("report tutorial", url=TUTORIAL_URL)],
    ])

def admin_keyboard(report_id, fixing=False):
    buttons = [
        [InlineKeyboardButton("NOTED", callback_data=f"admin:noted:{report_id}")],
        [InlineKeyboardButton("PLEASE WAIT", callback_data=f"admin:wait:{report_id}")],
        [InlineKeyboardButton("ACCOUNT REPLACED", callback_data=f"admin:replaced:{report_id}")],
        [InlineKeyboardButton("ACCOUNT FIXED", callback_data=f"admin:fixed:{report_id}")],
    ]
    return InlineKeyboardMarkup(buttons)

def wait_keyboard(report_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("0 DAYS", callback_data=f"wait:0:{report_id}"),
         InlineKeyboardButton("1 DAY", callback_data=f"wait:1:{report_id}")],
        [InlineKeyboardButton("2 DAYS", callback_data=f"wait:2:{report_id}"),
         InlineKeyboardButton("3 DAYS", callback_data=f"wait:3:{report_id}")],
        [InlineKeyboardButton("4 DAYS", callback_data=f"wait:4:{report_id}"),
         InlineKeyboardButton("5 DAYS", callback_data=f"wait:5:{report_id}")],
        [InlineKeyboardButton("6 DAYS", callback_data=f"wait:6:{report_id}"),
         InlineKeyboardButton("7 DAYS", callback_data=f"wait:7:{report_id}")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user(update.effective_user)
    context.user_data.clear()
    await update.message.reply_text(WELCOME, reply_markup=category_keyboard())

async def category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    cat = q.data.split(":", 1)[1]
    context.user_data.clear()
    context.user_data["category"] = cat
    await q.message.reply_text(FORMS[cat])

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user)

    # Owner commands are handled separately.
    if user.id == OWNER_ID and update.message.text.startswith("/"):
        return

    if context.user_data.get("stage") == "refund_form":
        context.user_data["refund_form"] = update.message.text
        context.user_data["stage"] = "refund_proof"
        await update.message.reply_text(
            "your refund form has been submitted.\n\n"
            "please send your proof of payment showing the payment made for this purchase."
        )
        return

    if "category" not in context.user_data:
        await update.message.reply_text("please choose a report category first.", reply_markup=category_keyboard())
        return

    if context.user_data.get("stage") == "proofs":
        await update.message.reply_text("please send the two required screenshots before submitting.")
        return

    category = context.user_data["category"]
    data, missing = parse_form(update.message.text, category)
    if missing:
        warnings, voided = add_warning(user.id, user.username or "")
        if voided:
            await update.message.reply_text(
                "your report format is invalid for the second time.\n\nstatus: VOIDED"
            )
        else:
            await update.message.reply_text(
                "your report format is invalid.\n\n"
                "this is your first warning.\n"
                "please follow the form exactly and send it in one bubble chat only."
            )
        context.user_data.clear()
        return

    context.user_data["form_text"] = update.message.text
    context.user_data["parsed"] = data
    context.user_data["stage"] = "proofs"
    context.user_data["proofs"] = []
    await update.message.reply_text(
        "send the screenshot of your proof of vouch and proof of issue."
    )

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("stage") == "refund_proof":
        report_id = context.user_data.get("refund_report_id")
        if not report_id:
            await update.message.reply_text("no active refund request was found.")
            return

        con = db()
        con.execute(
            "UPDATE reports SET refund_proof_file_id=? WHERE id=?",
            (update.message.photo[-1].file_id, report_id),
        )
        con.commit()
        row = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
        con.close()

        await send_refund_to_owner(context.application, row, context.user_data.get("refund_form", ""), update.message.photo[-1].file_id)
        await update.message.reply_text(
            "your refund request and proof of payment have been submitted for review."
        )
        context.user_data.clear()
        return

    if context.user_data.get("stage") != "proofs":
        return

    proofs = context.user_data.setdefault("proofs", [])
    if len(proofs) >= 2:
        return

    proofs.append(update.message.photo[-1].file_id)

    if len(proofs) == 1:
        await update.message.reply_text("proof 1 received. please send the other screenshot.")
    else:
        context.user_data["stage"] = "ready"
        await update.message.reply_text(
            "both proofs received.\n\nplease click submit.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("submit", callback_data="submit")]
            ])
        )

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user

    if context.user_data.get("stage") != "ready":
        await q.message.reply_text("please complete the report form and send both proofs first.")
        return

    data = context.user_data["parsed"]
    category = context.user_data["category"]
    form_text = context.user_data["form_text"]
    proofs = context.user_data["proofs"]

    days = parse_days(data.get("days availed", ""))
    purchased = parse_date(data.get("date purchased", ""))
    amount = parse_amount(data.get("amount paid", ""))
    reported = datetime.now(timezone.utc).date()

    remaining = remaining_days(purchased, days, reported)

    # We keep the password out of permanent storage.
    password = data.get("password", "")

    con = db()
    cur = con.execute(
        """INSERT INTO reports(
            user_id, username, category, form_text, password, amount_paid,
            days_availed, date_purchased, date_reported, status,
            proof_vouch_file_id, proof_issue_file_id, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'SUBMITTED', ?, ?, ?)""",
        (
            user.id, user.username or "", category, form_text, password,
            amount, days,
            purchased.isoformat() if purchased else None,
            reported.isoformat(),
            proofs[0], proofs[1],
            datetime.now(timezone.utc).isoformat(),
        )
    )
    report_id = cur.lastrowid
    con.commit()
    row = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    con.close()

    # Remove password from the saved row immediately.
    con = db()
    con.execute("UPDATE reports SET password=NULL WHERE id=?", (report_id,))
    con.commit()
    con.close()

    await send_report_to_owner(context.application, row, remaining)
    await q.message.reply_text(
        f"your report #{report_id:04d} has been submitted.\n"
        "please wait for the report to be reviewed."
    )
    context.user_data.clear()

async def send_report_to_owner(app, row, remaining=None):
    user_label = f"@{row['username']}" if row["username"] else str(row["user_id"])
    text = (
        f"NEW REPORT #{row['id']:04d}\n\n"
        f"reporter: {user_label}\n"
        f"user id: {row['user_id']}\n"
        f"category: {row['category']}\n"
        f"amount paid: {fmt_money(row['amount_paid']) if row['amount_paid'] is not None else 'not parsed'}\n"
        f"days availed: {row['days_availed'] or 'not parsed'}\n"
        f"date purchased: {row['date_purchased'] or 'not parsed'}\n"
        f"date reported: {row['date_reported']}\n"
        f"subscription days remaining at report: {remaining if remaining is not None else 'not available'}\n"
        f"status: {row['status']}\n\n"
        f"report form:\n{row['form_text']}\n\n"
        "proof of vouch: attached below\n"
        "proof of issue: attached below"
    )
    await app.bot.send_message(OWNER_ID, text, reply_markup=admin_keyboard(row["id"]))

    if row["proof_vouch_file_id"]:
        await app.bot.send_photo(OWNER_ID, row["proof_vouch_file_id"], caption=f"report #{row['id']:04d} - proof of vouch")
    if row["proof_issue_file_id"]:
        await app.bot.send_photo(OWNER_ID, row["proof_issue_file_id"], caption=f"report #{row['id']:04d} - proof of issue")

async def send_refund_to_owner(app, row, refund_form, proof_file_id):
    purchased = parse_date(row["date_purchased"]) if row["date_purchased"] else None
    reported = parse_date(row["date_reported"]) if row["date_reported"] else None
    remaining = remaining_days(purchased, row["days_availed"], reported)

    refund, fee, error = refund_calc(row["amount_paid"], row["days_availed"], remaining)

    text = (
        f"REFUND REQUEST #{row['id']:04d}\n\n"
        f"reporter: @{row['username']}" if row["username"] else f"reporter: {row['user_id']}"
    )
    text += (
        f"\nuser id: {row['user_id']}\n"
        f"amount paid: {fmt_money(row['amount_paid']) if row['amount_paid'] is not None else 'not parsed'}\n"
        f"account/product: {row['category']}\n"
        f"date purchased: {row['date_purchased']}\n"
        f"days availed: {row['days_availed']}\n"
        f"date reported: {row['date_reported']}\n\n"
        f"refund form:\n{refund_form}\n\n"
    )

    if error:
        text += f"refund computation: {error}\n"
    else:
        text += (
            "refund computation:\n"
            f"remaining days: {remaining}\n"
            f"service fee: {fee:.2f}\n"
            f"formula: {fmt_money(row['amount_paid'])} ÷ {row['days_availed']} × {remaining} × {fee:.2f}\n"
            f"estimated refund: {fmt_money(refund)}\n"
        )

    await app.bot.send_message(OWNER_ID, text)
    await app.bot.send_photo(OWNER_ID, proof_file_id, caption=f"report #{row['id']:04d} - proof of payment")

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != OWNER_ID:
        await q.answer("owner only", show_alert=True)
        return

    await q.answer()
    _, action, report_id_s = q.data.split(":")
    report_id = int(report_id_s)

    if action == "wait":
        await q.message.reply_text(
            f"select the PLEASE WAIT period for report #{report_id:04d}:",
            reply_markup=wait_keyboard(report_id)
        )
        return

    con = db()
    row = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        con.close()
        await q.message.reply_text("report not found.")
        return

    status_map = {
        "noted": "NOTED",
        "replaced": "ACCOUNT REPLACED",
        "fixed": "ACCOUNT FIXED",
    }
    status = status_map[action]
    con.execute(
        "UPDATE reports SET status=?, fixing_until=NULL WHERE id=?",
        (status, report_id)
    )
    con.commit()
    con.close()

    await q.message.reply_text(f"report #{report_id:04d} updated to {status}.")
    await context.bot.send_message(
        row["user_id"],
        f"report #{report_id:04d}\n\nstatus: {status}"
    )

async def wait_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != OWNER_ID:
        await q.answer("owner only", show_alert=True)
        return
    await q.answer()

    _, days_s, report_id_s = q.data.split(":")
    days = int(days_s)
    report_id = int(report_id_s)

    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=days)

    con = db()
    row = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if not row:
        con.close()
        await q.message.reply_text("report not found.")
        return

    if days == 0:
        status = "FOR REFUND"
        fixing_until = now.isoformat()
    else:
        status = "PLEASE WAIT"
        fixing_until = deadline.isoformat()

    con.execute(
        "UPDATE reports SET status=?, fixing_until=? WHERE id=?",
        (status, fixing_until, report_id)
    )
    con.commit()
    con.close()

    await q.message.reply_text(
        f"report #{report_id:04d}\n\n"
        f"status: {status}\n"
        f"fixing period: {days} day(s)"
        )

    if status == "FOR REFUND":
        await trigger_refund(context.application, report_id)
    else:
        await context.bot.send_message(
            row["user_id"],
            f"report #{report_id:04d}\n\n"
            f"status: PLEASE WAIT\n"
            f"fixing period: {days} day(s)\n"
            f"fixing deadline: {deadline.date().isoformat()}"
        )

async def trigger_refund(app, report_id):
    con = db()
    row = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    con.close()
    if not row:
        return

    await app.bot.send_message(
        row["user_id"],
        """your report has reached 0 days, and the issue has
not been resolved.

status: FOR REFUND

please fill out the refund form below:

refund form
report number:
your username:
amount paid:
account/product:
date purchased:
days availed:
date reported:
bank details for refund:"""
    )

async def countdown_job(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(timezone.utc)
    con = db()
    rows = con.execute(
        """SELECT * FROM reports
           WHERE status='PLEASE WAIT' AND fixing_until IS NOT NULL"""
    ).fetchall()

    for row in rows:
        try:
            deadline = datetime.fromisoformat(row["fixing_until"])
        except Exception:
            continue

        if now >= deadline:
            con.execute(
                "UPDATE reports SET status='FOR REFUND' WHERE id=?",
                (row["id"],)
            )
            await trigger_refund(context.application, row["id"])

    con.commit()
    con.close()

async def refund_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Optional command for the buyer if they need to resume a refund form.
    if update.effective_user.id == OWNER_ID:
        return
    report_id = context.user_data.get("refund_report_id")
    if not report_id:
        await update.message.reply_text("please use the refund form sent to you after your report reaches 0 days.")
        return
    context.user_data["stage"] = "refund_form"

async def owner_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    if not context.args:
        await update.message.reply_text("usage: /report <user_id> <reason>")
        return
    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("invalid user id.")
        return
    reason = " ".join(context.args[1:]) or "direct-to-owner report"
    row = get_user(uid)
    username = row["username"] if row else ""
    warnings, voided = add_warning(uid, username)
    status = "VOIDED" if voided else "WARNING"
    await update.message.reply_text(
        f"user {uid}: {status}\n"
        f"offense count: {warnings}\n"
        f"reason: {reason}"
    )
    try:
        await context.bot.send_message(
            uid,
            f"your direct-to-owner report was recorded as a {status.lower()}.\n"
            f"offense count: {warnings}."
        )
    except Exception:
        pass

def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", owner_report))
    app.add_handler(CallbackQueryHandler(category, pattern=r"^cat:"))
    app.add_handler(CallbackQueryHandler(submit, pattern=r"^submit$"))
    app.add_handler(CallbackQueryHandler(admin_action, pattern=r"^admin:"))
    app.add_handler(CallbackQueryHandler(wait_select, pattern=r"^wait:"))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))

    # Check fixing deadlines regularly. This requires the job-queue extra.
    if app.job_queue:
        app.job_queue.run_repeating(countdown_job, interval=60, first=10)

    print("bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
