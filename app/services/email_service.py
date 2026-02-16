"""
Email Service
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for sending emails."""

    @staticmethod
    async def send_email(
        to_email: str,
        subject: str,
        body: str,
        html_body: str | None = None,
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
        
        Returns:
            bool: True if sent successfully
        """
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            # In development, just log the event
            if settings.is_development:
                logger.info("Email sent (development mode)")
                return True
            return False

        message = MIMEMultipart("alternative")
        message["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        message["To"] = to_email
        message["Subject"] = subject

        # Add plain text part
        message.attach(MIMEText(body, "plain"))

        # Add HTML part if provided
        if html_body:
            message.attach(MIMEText(html_body, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )
            return True
        except Exception:
            logger.error("Email sending failed")
            return False

    @classmethod
    async def send_otp_email(cls, to_email: str, otp: str) -> bool:
        """
        Send OTP verification email.

        """
        subject = f"Your MiniMart Verification Code: {otp}"
        body = f"""
Hello,

Your verification code is: {otp}

This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.

If you didn't request this code, please ignore this email.

Best regards,
The MiniMart Team
        """.strip()

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        .container {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .otp {{ font-size: 32px; font-weight: bold; color: #4F46E5; letter-spacing: 8px; text-align: center; padding: 20px; background: #F3F4F6; border-radius: 8px; margin: 20px 0; }}
        .footer {{ color: #6B7280; font-size: 14px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Verify Your Email</h1>
        <p>Hello,</p>
        <p>Your verification code is:</p>
        <div class="otp">{otp}</div>
        <p>This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.</p>
        <p class="footer">If you didn't request this code, please ignore this email.</p>
    </div>
</body>
</html>
        """.strip()

        logger.info("Sending OTP verification email")
        return await cls.send_email(to_email, subject, body, html_body)

    @classmethod
    async def send_invitation_email(
        cls,
        to_email: str,
        inviter_name: str,
        list_name: str,
        accept_url: str,
        reject_url: str,
    ) -> bool:
        """
        Send shopping list invitation email.
        
        Args:
            to_email: Recipient email
            inviter_name: Name of the person who invited
            list_name: Name of the shopping list
            accept_url: URL to accept the invitation
            reject_url: URL to reject the invitation
        
        Returns:
            bool: True if sent successfully
        """
        subject = f"{inviter_name} invited you to collaborate on '{list_name}'"
        body = f"""
Hello,

{inviter_name} has invited you to collaborate on the shopping list "{list_name}" in MiniMart.

To accept this invitation, click here:
{accept_url}

To reject this invitation, click here:
{reject_url}

This invitation will expire in {settings.INVITATION_TOKEN_EXPIRE_HOURS} hours.

Best regards,
The MiniMart Team
        """.strip()

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        .container {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{ display: inline-block; padding: 12px 24px; margin: 10px 5px; border-radius: 6px; text-decoration: none; font-weight: bold; }}
        .accept {{ background: #10B981; color: white; }}
        .reject {{ background: #EF4444; color: white; }}
        .list-name {{ background: #F3F4F6; padding: 10px 15px; border-radius: 6px; display: inline-block; }}
        .footer {{ color: #6B7280; font-size: 14px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>You're Invited! 🛒</h1>
        <p><strong>{inviter_name}</strong> has invited you to collaborate on:</p>
        <p class="list-name">{list_name}</p>
        <p>Join them to add items, mark purchases, and keep your shopping synchronized in real-time!</p>
        <div style="margin: 30px 0;">
            <p>To accept, copy this link:</p>
            <p style="font-size: 16px; word-break: break-all; background: #f4f4f4; padding: 10px; border-radius: 4px;">{accept_url}</p>
            <p>To decline, copy this link:</p>
            <p style="font-size: 16px; word-break: break-all; background: #f4f4f4; padding: 10px; border-radius: 4px;">{reject_url}</p>
        </div>
        <p class="footer">This invitation will expire in {settings.INVITATION_TOKEN_EXPIRE_HOURS} hours.</p>
    </div>
</body>
</html>
        """.strip()

        logger.info("Sending shopping list invitation email")
        return await cls.send_email(to_email, subject, body, html_body)

    @classmethod
    async def send_password_reset_email(cls, to_email: str, reset_url: str) -> bool:
        """
        Send password reset email with a reset link.
        """
        subject = "Reset Your MiniMart Password"
        body = f"""
Hello,

You requested a password reset. Click the link below to reset your password:

{reset_url}

This link will expire in 15 minutes.

If you didn't request this, please ignore this email.

Best regards,
The MiniMart Team
        """.strip()

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        .container {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #4F46E5; color: white; border-radius: 6px; text-decoration: none; font-weight: bold; }}
        .footer {{ color: #6B7280; font-size: 14px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Reset Your Password</h1>
        <p>You requested a password reset for your MiniMart account.</p>
        <div style="margin: 30px 0;">
            <p>Go to this link to reset:</p>
            <p style="font-size: 16px; word-break: break-all; background: #f4f4f4; padding: 10px; border-radius: 4px;">{reset_url}</p>
        </div>
        <p>This link will expire in 15 minutes.</p>
        <p class="footer">If you didn't request this, please ignore this email.</p>
    </div>
</body>
</html>
        """.strip()

        logger.info("Sending password reset email")
        return await cls.send_email(to_email, subject, body, html_body)
