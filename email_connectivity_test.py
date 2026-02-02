"""
Quick Gmail SMTP connectivity test (2026 version)
Uses App Password — normal password will NOT work
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import getpass
import sys

# ────────────────────────────────────────────────
# Configuration — change these values
# ────────────────────────────────────────────────

SMTP_SERVER = "smtp.gmail.com"

# Try both ports — many accounts work better with one or the other in 2026
# Start with 465 (SSL), if it fails → try 587 (STARTTLS)
USE_PORT = 465          # ← change to 587 if 465 fails
# USE_PORT = 587

YOUR_EMAIL = "yourname@gmail.com"           # ← full Gmail address

# ────────────────────────────────────────────────
# Main test function
# ────────────────────────────────────────────────

def test_gmail_smtp():
    print("\n" + "="*60)
    print("  Gmail SMTP Test Script  (App Password required)")
    print("="*60)

    if not YOUR_EMAIL or "@gmail.com" not in YOUR_EMAIL:
        print("→ Please edit YOUR_EMAIL in the script first!")
        return

    # Ask for App Password securely (don't hardcode in shared scripts)
    print(f"\nSending test email from: {YOUR_EMAIL}")
    print("Enter your **16-character App Password** (no spaces):")
    app_password = getpass.getpass("App Password: ").strip()

    if len(app_password) != 16:
        print("→ App Password should be exactly 16 characters (no spaces).")
        print("   Generate one here: https://myaccount.google.com/apppasswords")
        return

    msg = MIMEMultipart()
    msg["From"] = YOUR_EMAIL
    msg["To"] = YOUR_EMAIL               # send to yourself for quick test
    msg["Subject"] = "SMTP Test - Python Script"

    body = (
        "This is a test message from your Python SMTP script.\n\n"
        "If you see this email → SMTP connection + login is working!\n"
        f"Port used: {USE_PORT}\n"
        "Date: 2026"
    )
    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()

    try:
        print(f"\nConnecting to {SMTP_SERVER}:{USE_PORT} ...")

        if USE_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, USE_PORT, context=context)
        else:
            server = smtplib.SMTP(SMTP_SERVER, USE_PORT)
            server.starttls(context=context)

        print("→ Logging in...")
        server.login(YOUR_EMAIL, app_password)

        print("→ Sending test message...")
        server.send_message(msg)

        print("\n" + "═"*60)
        print("SUCCESS! Test email was sent.")
        print("Check your inbox/spam folder.")
        print("═"*60 + "\n")

        server.quit()

    except smtplib.SMTPAuthenticationError as e:
        print("\nERROR: Authentication failed (535)")
        print("Most common causes:")
        print("  1. Wrong App Password (copy-paste carefully — no spaces)")
        print("  2. 2-Step Verification is OFF → turn it ON first")
        print("  3. App Password was revoked or generated before 2FA was enabled")
        print("\nFix:")
        print(" → Go to https://myaccount.google.com/apppasswords")
        print(" → Revoke old ones → Generate new App Password")
        print(" → Make sure you're using the **new 16-char code**")
        sys.exit(1)

    except Exception as e:
        print("\nConnection / sending failed:")
        print(f"→ {type(e).__name__}: {e}")
        print("\nTry the other port:")
        print(f"  Change USE_PORT = {587 if USE_PORT == 465 else 465}")
        print("Then run the script again.")
        sys.exit(1)


if __name__ == "__main__":
    test_gmail_smtp()