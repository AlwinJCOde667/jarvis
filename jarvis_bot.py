import os
import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from google import genai

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


# =========================
# CONFIGURATION
# =========================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

OWNER_CHAT_ID = 2009288738

MODEL = "gemini-3.8-flash"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly"
]

CREDENTIALS_FILE = r"C:\jarvis\credentials.json"
TOKEN_FILE = r"C:\jarvis\gmail_token.json"


# =========================
# GEMINI
# =========================

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing.")

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# =========================
# GMAIL CONNECTION
# =========================

def get_gmail_service():

    creds = None

    if os.path.exists(TOKEN_FILE):

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:

            creds.refresh(Request())

        else:

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            creds = flow.run_local_server(
                port=0
            )

        with open(TOKEN_FILE, "w") as token:

            token.write(
                creds.to_json()
            )

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


# =========================
# GMAIL SEARCH TOOL
# =========================

def search_gmail(query):

    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=10
    ).execute()

    messages = results.get(
        "messages",
        []
    )

    if not messages:
        return "No emails found."

    output = []

    for msg in messages:

        email = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="metadata",
            metadataHeaders=[
                "From",
                "Subject",
                "Date"
            ]
        ).execute()

        headers = email.get(
            "payload",
            {}
        ).get(
            "headers",
            []
        )

        data = {}

        for header in headers:

            data[
                header["name"]
            ] = header["value"]

        output.append(
            f"From: {data.get('From', 'Unknown')}\n"
            f"Subject: {data.get('Subject', '(No subject)')}\n"
            f"Date: {data.get('Date', '')}"
        )

    return "\n\n".join(output)

def read_gmail_message(message_id):
    service = get_gmail_service()

    email = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    headers = email.get(
        "payload",
        {}
    ).get(
        "headers",
        []
    )

    data = {}

    for header in headers:
        data[header["name"]] = header["value"]

    sender = data.get(
        "From",
        "Unknown"
    )

    subject = data.get(
        "Subject",
        "(No subject)"
    )

    date = data.get(
        "Date",
        ""
    )

    body = ""

    payload = email.get(
        "payload",
        {}
    )

    parts = payload.get(
        "parts",
        []
    )

    for part in parts:

        if part.get("mimeType") == "text/plain":

            import base64

            body_data = part.get(
                "body",
                {}
            ).get(
                "data"
            )

            if body_data:

                body = base64.urlsafe_b64decode(
                    body_data
                ).decode(
                    "utf-8",
                    errors="ignore"
                )

                break

    if not body:

        body = "(Email body could not be extracted.)"

    return (
        f"From: {sender}\n"
        f"Subject: {subject}\n"
        f"Date: {date}\n\n"
        f"{body}"
    )

def find_and_read_email(request):
    service = get_gmail_service()

    lower = request.lower()

    # Decide what Gmail should search for
    if "amazon" in lower:
        query = "from:amazon"

    elif "linkedin" in lower:
        query = "from:linkedin"

    elif "today" in lower:
        query = "newer_than:1d"

    elif "yesterday" in lower:
        query = "newer_than:2d older_than:1d"

    else:
        query = "newer_than:7d"

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=5
    ).execute()

    messages = results.get(
        "messages",
        []
    )

    if not messages:
        return "I couldn't find any matching emails."

    # Use the newest matching email
    message_id = messages[0]["id"]

    return read_gmail_message(
        message_id
    )


# =========================
# START
# =========================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "Jarvis is online. 🤖"
    )


# =========================
# MY ID
# =========================

async def my_id(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        f"Your Telegram chat ID is: "
        f"{update.effective_chat.id}"
    )


# =========================
# EMAIL COMMAND
# =========================

async def check_email(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        result = search_gmail(
            "newer_than:1d"
        )

        await update.message.reply_text(
            f"📧 Recent emails:\n\n{result}"
        )

    except Exception as e:

        print("Gmail error:", e)

        await update.message.reply_text(
            f"Gmail error:\n{e}"
        )


# =========================
# SEARCH COMMAND
# =========================

async def search_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        query = " ".join(
            context.args
        ).strip()

        if not query:

            await update.message.reply_text(
                "Usage:\n"
                "/search from:amazon\n\n"
                "or\n"
                "/search subject:invoice"
            )

            return

        result = search_gmail(
            query
        )

        await update.message.reply_text(
            f"🔎 Search results:\n\n{result}"
        )

    except Exception as e:

        print(
            "Gmail search error:",
            e
        )

        await update.message.reply_text(
            f"Gmail search error:\n{e}"
        )

async def read_command(update, context):
    try:

        message_id = " ".join(
            context.args
        ).strip()

        if not message_id:

            await update.message.reply_text(
                "Usage:\n/read EMAIL_MESSAGE_ID"
            )

            return

        result = read_gmail_message(
            message_id
        )

        # Telegram has a message size limit,
        # so keep very long emails manageable.

        if len(result) > 4000:

            result = result[:4000] + "\n\n[Email truncated]"

        await update.message.reply_text(
            f"📖 Email:\n\n{result}"
        )

    except Exception as e:

        print(
            "Gmail read error:",
            e
        )

        await update.message.reply_text(
            f"Gmail read error:\n{e}"
        )

# =========================
# GEMINI CHAT
# =========================

async def chat(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        user_message = update.message.text

        lower = user_message.lower()

        # -------------------------
        # Natural Gmail requests
        # -------------------------

        gmail_words = [
            "email",
            "emails",
            "mail",
            "inbox",
            "gmail"
        ]

        if any(
            word in lower
            for word in gmail_words
        ):

            result = find_and_read_email(
                user_message
            )

            message = f"📧 Here's what I found:\n\n{result}"

            for i in range(0, len(message), 4000):
                await update.message.reply_text(
                    message[i:i + 4000]
                )

            return

        # -------------------------
        # Normal Gemini chat
        # -------------------------

        for attempt in range(3):

            try:

                response = client.models.generate_content(
                    model=MODEL,
                    contents=user_message
                )

                await update.message.reply_text(
                    response.text
                )

                return

            except Exception as e:

                error_text = str(e)

                if (
                    "503" in error_text
                    or "UNAVAILABLE" in error_text
                ):

                    if attempt < 2:

                        await asyncio.sleep(5)

                        continue

                raise

    except Exception as e:

        print(
            "Chat error:",
            e
        )

        await update.message.reply_text(
            f"Jarvis error:\n{e}"
        )

# =========================
# GMAIL AUTO MONITOR
# =========================

seen_messages = set()


async def monitor_gmail(
    application: Application
):

    global seen_messages

    print("Gmail monitor started.")

    try:

        # Get the emails that already exist when Jarvis starts.
        # These will NOT trigger notifications.

        service = get_gmail_service()

        results = service.users().messages().list(
            userId="me",
            q="newer_than:1d"
        ).execute()

        existing_messages = results.get(
            "messages",
            []
        )

        seen_messages = {
            msg["id"]
            for msg in existing_messages
        }

        print(
            f"Marked {len(seen_messages)} existing emails as seen."
        )

    except Exception as e:

        print(
            "Gmail startup error:",
            e
        )

    # Now monitor for genuinely new emails.

    while True:

        try:

            service = get_gmail_service()

            results = service.users().messages().list(
                userId="me",
                q="newer_than:1d"
            ).execute()

            messages = results.get(
                "messages",
                []
            )

            for msg in messages:

                message_id = msg["id"]

                if message_id in seen_messages:

                    continue

                email = service.users().messages().get(
                    userId="me",
                    id=message_id,
                    format="metadata",
                    metadataHeaders=[
                        "From",
                        "Subject",
                        "Date"
                    ]
                ).execute()

                headers = email.get(
                    "payload",
                    {}
                ).get(
                    "headers",
                    []
                )

                data = {}

                for header in headers:

                    data[
                        header["name"]
                    ] = header["value"]

                sender = data.get(
                    "From",
                    "Unknown"
                )

                subject = data.get(
                    "Subject",
                    "(No subject)"
                )

                date = data.get(
                    "Date",
                    ""
                )

                message = (
                    "📧 New email received!\n\n"
                    f"From: {sender}\n"
                    f"Subject: {subject}\n"
                    f"Date: {date}"
                )

                await application.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=message
                )

                seen_messages.add(
                    message_id
                )

        except Exception as e:

            print(
                "Gmail monitor error:",
                e
            )

        await asyncio.sleep(60)

# =========================
# STARTUP
# =========================

async def post_init(
    application: Application
):

    asyncio.create_task(
        monitor_gmail(application)
    )


# =========================
# MAIN
# =========================

def main():

    if not TELEGRAM_TOKEN:

        raise RuntimeError(
            "TELEGRAM_TOKEN is missing."
        )

    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY is missing."
        )

    application = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .post_init(post_init)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "myid",
            my_id
        )
    )

    application.add_handler(
        CommandHandler(
            "email",
            check_email
        )
    )

    application.add_handler(
        CommandHandler(
            "search",
            search_command
        )
    )
    application.add_handler(
        CommandHandler(
            "read", 
            read_command
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            chat
        )
    )

    print(
        "Jarvis is running..."
    )

    application.run_polling()


if __name__ == "__main__":

    main()