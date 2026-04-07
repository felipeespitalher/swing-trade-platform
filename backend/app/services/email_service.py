"""
Email sending service.

Priority:
1. Resend (https://resend.com) — when RESEND_API_KEY is set
2. SMTP fallback — when SMTP_HOST is set
3. Development console log — default (no external service required)
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def _from_address() -> str:
    name = settings.resend_from_name or settings.smtp_from_name
    email = settings.resend_from_email or settings.smtp_from_email
    return f"{name} <{email}>"


def _send(to_email: str, subject: str, html: str, text: str) -> bool:
    """
    Dispatch email via Resend → SMTP → console log (in that priority order).
    """
    # ── 1. Resend ────────────────────────────────────────────────────────────
    if settings.resend_api_key:
        try:
            import resend  # type: ignore
            resend.api_key = settings.resend_api_key
            params: resend.Emails.SendParams = {
                "from": _from_address(),
                "to": [to_email],
                "subject": subject,
                "html": html,
                "text": text,
            }
            resend.Emails.send(params)
            logger.info(f"Email sent via Resend to {to_email}")
            return True
        except Exception as exc:
            logger.error(f"Resend error sending to {to_email}: {exc}")
            return False

    # ── 2. SMTP ──────────────────────────────────────────────────────────────
    if settings.smtp_host:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            msg["To"] = to_email
            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent via SMTP to {to_email}")
            return True
        except Exception as exc:
            logger.error(f"SMTP error sending to {to_email}: {exc}")
            return False

    # ── 3. Dev console log ───────────────────────────────────────────────────
    logger.info(
        f"[EMAIL — DEV MODE | configure RESEND_API_KEY to send for real]\n"
        f"To: {to_email}\nSubject: {subject}\n---\n{text}\n---"
    )
    return True


class EmailService:
    """Service for sending transactional emails."""

    @staticmethod
    def send_verification_email(
        email: str,
        user_id: str,
        verification_token: str,
        first_name: str,
    ) -> bool:
        frontend_url = getattr(settings, "frontend_url", "http://localhost:5173")
        url = f"{frontend_url}/auth/verify?token={verification_token}"

        subject = "Verifique seu e-mail — Swing Trade Platform"
        html = f"""
<html><body style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
<h2 style="color:#3b82f6">Bem-vindo à Swing Trade Platform!</h2>
<p>Olá, {first_name}!</p>
<p>Clique no botão abaixo para verificar seu endereço de e-mail:</p>
<p style="text-align:center;margin:32px 0">
  <a href="{url}" style="background:#3b82f6;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
    Verificar E-mail
  </a>
</p>
<p style="color:#6b7280;font-size:13px">
  O link expira em <strong>24 horas</strong>.<br>
  Se você não criou esta conta, ignore este e-mail.
</p>
<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
<p style="color:#9ca3af;font-size:12px">Swing Trade Automation Platform</p>
</body></html>"""

        text = (
            f"Bem-vindo à Swing Trade Platform!\n\n"
            f"Olá, {first_name}!\n\n"
            f"Verifique seu e-mail acessando:\n{url}\n\n"
            f"O link expira em 24 horas."
        )

        return _send(email, subject, html, text)

    @staticmethod
    def send_password_reset_email(
        email: str,
        first_name: str,
        reset_token: str,
    ) -> bool:
        frontend_url = getattr(settings, "frontend_url", "http://localhost:5173")
        url = f"{frontend_url}/auth/reset-password?token={reset_token}"

        subject = "Redefinição de Senha — Swing Trade Platform"
        html = f"""
<html><body style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:24px">
<h2 style="color:#3b82f6">Redefinição de Senha</h2>
<p>Olá, {first_name}!</p>
<p>Recebemos uma solicitação para redefinir a senha da sua conta.
Clique no botão abaixo para criar uma nova senha:</p>
<p style="text-align:center;margin:32px 0">
  <a href="{url}" style="background:#3b82f6;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
    Redefinir Senha
  </a>
</p>
<p style="color:#6b7280;font-size:13px">
  O link expira em <strong>15 minutos</strong>.<br>
  Se você não solicitou a redefinição, ignore este e-mail.
</p>
<hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
<p style="color:#9ca3af;font-size:12px">Swing Trade Automation Platform</p>
</body></html>"""

        text = (
            f"Redefinição de Senha\n\n"
            f"Olá, {first_name}!\n\n"
            f"Redefina sua senha (válido por 15 min):\n{url}\n\n"
            f"Se você não solicitou a redefinição, ignore este e-mail."
        )

        return _send(email, subject, html, text)
