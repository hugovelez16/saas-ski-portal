import os

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", ""),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", ""),
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@vesotel.com"),
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587")),
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com"), # Default to a common provider or empty
    MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Vesotel"),
    MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True").lower() == "true",
    MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False").lower() == "true",
    USE_CREDENTIALS = os.getenv("USE_CREDENTIALS", "True").lower() == "true",
    VALIDATE_CERTS = os.getenv("VALIDATE_CERTS", "True").lower() == "true",
)


def get_html_template(title: str, body_content: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .logo {{ max-width: 150px; }}
            .content {{ background: #ffffff; padding: 30px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .code {{ font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #D32F2F; text-align: center; margin: 20px 0; display: block; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #888; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #D32F2F; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; }}
            h1 {{ color: #1a1a1a; margin-top: 0; }}
            p {{ margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2 style="color: #D32F2F; font-weight: 800; font-size: 24px; margin: 0;">VESOTEL</h2>
        </div>
        <div class="content">
            <h1>{title}</h1>
            {body_content}
        </div>
        <div class="footer">
            <p>&copy; 2026 Vesotel Gestor Jornada. All rights reserved.</p>
            <p>This is an automated message, please do not reply.</p>
        </div>
    </body>
    </html>
    """

# Legacy 2FA Email removed. TOTP (Google Authenticator) is now used.

async def send_welcome_email(email: EmailStr, token: str):
    frontend_url = os.getenv("FRONTEND_URL", "https://clases.vesotel.com")
    setup_link = f"{frontend_url}/reset-password?token={token}"
    html_content = get_html_template(
        "Welcome to Vesotel",
        f"""
        <p>Hello,</p>
        <p>Welcome to <strong>Vesotel</strong>! Your account has been successfully created.</p>
        <p>Please click the button below to set up your password and access your account:</p>
        <div style="text-align: center; margin-top: 25px; margin-bottom: 25px;">
            <a href="{setup_link}" class="button" style="color: white; padding: 12px 24px; background-color: #D32F2F; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">Set Up Password</a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; font-size: 0.9em; color: #666;"><a href="{setup_link}">{setup_link}</a></p>
        <p>This link will expire in 2 hours.</p>
        """
    )

    message = MessageSchema(
        subject="Welcome to Vesotel Team",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message)


async def send_password_reset_email(email: EmailStr, token: str):
    frontend_url = os.getenv("FRONTEND_URL", "https://clases.vesotel.com")
    reset_link = f"{frontend_url}/reset-password?token={token}"
    html_content = get_html_template(
        "Reset Your Password",
        f"""
        <p>Hello,</p>
        <p>We received a request to reset your password for your <strong>Vesotel</strong> account.</p>
        <p>Please click the button below to choose a new password:</p>
        <div style="text-align: center; margin-top: 25px; margin-bottom: 25px;">
            <a href="{reset_link}" class="button" style="color: white; padding: 12px 24px; background-color: #D32F2F; text-decoration: none; border-radius: 4px; font-weight: bold; display: inline-block;">Reset Password</a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; font-size: 0.9em; color: #666;"><a href="{reset_link}">{reset_link}</a></p>
        <p>This link will expire in 2 hours.</p>
        <p>If you did not request this, you can safely ignore this email.</p>
        """
    )

    message = MessageSchema(
        subject="Reset Your Vesotel Password",
        recipients=[email],
        body=html_content,
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message)

