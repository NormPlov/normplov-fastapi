import smtplib
import os
import asyncio

from email.message import EmailMessage
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader


load_dotenv()
env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), '../templates')))


async def send_verification_email(email: str, username: str, verification_code: str):
    template = env.get_template('email_verification.html')
    html_content = template.render(username=username, verification_code=verification_code)

    msg = EmailMessage()
    msg.set_content(f"Hi {username}, your verification code is: {verification_code}")
    msg.add_alternative(html_content, subtype='html')
    msg["Subject"] = "Email Verification"
    msg["From"] = os.getenv("EMAIL_SENDER")
    msg["To"] = email

    # Synchronous email-sending logic
    def send_email():
        try:
            with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT"))) as server:
                server.starttls()
                server.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
                server.send_message(msg)
                print("Verification email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")

    await asyncio.to_thread(send_email)


def send_reset_email(email: str, reset_code: str, username: str):

    template = env.get_template('password_reset.html')
    html_content = template.render(username=username, reset_code=reset_code)

    msg = EmailMessage()
    msg.set_content(f"Hi {username}, use the following code to reset your password: {reset_code}")
    msg.add_alternative(html_content, subtype='html')
    msg["Subject"] = "Password Reset Code"
    msg["From"] = os.getenv("EMAIL_SENDER")
    msg["To"] = email

    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_SENDER"), os.getenv("EMAIL_PASSWORD"))
            server.send_message(msg)
            print("Password reset email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


