"""
Email-сервис для отправки invite-ссылок на чат.
Поддерживает SMTP с SSL/TLS (Mail.ru, Yandex, Gmail и др.)
"""
import logging
import ssl
from typing import Optional, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# Флаг доступности aiosmtplib
AIOSMTPLIB_AVAILABLE = False
try:
    import aiosmtplib
    AIOSMTPLIB_AVAILABLE = True
except ImportError:
    logger.info("aiosmtplib не установлен — email-рассылка недоступна")


class EmailService:
    """SMTP-сервис для отправки email"""

    def __init__(self):
        self._host: str = ""
        self._port: int = 465
        self._username: str = ""
        self._password: str = ""
        self._use_tls: bool = True
        self._from_name: str = "Festival Color CRM"
        self._configured = False

    def configure(self, settings: Dict[str, str]):
        """Конфигурация из настроек БД"""
        self._host = settings.get("smtp_host", "")
        port_str = settings.get("smtp_port", "465")
        self._port = int(port_str) if port_str else 465
        self._username = settings.get("smtp_username", "")
        self._password = settings.get("smtp_password", "")
        self._use_tls = settings.get("smtp_use_tls", "true").lower() == "true"
        self._from_name = settings.get("smtp_from_name", "Festival Color CRM")
        self._configured = bool(self._host and self._username and self._password)

        if self._configured:
            logger.info(f"Email сервис настроен: {self._host}:{self._port}")
        else:
            logger.info("Email сервис не настроен (отсутствуют SMTP-данные)")

    @property
    def available(self) -> bool:
        """Email-сервис готов к работе"""
        return self._configured and AIOSMTPLIB_AVAILABLE

    async def send_chat_invite(
        self,
        to_email: str,
        recipient_name: str,
        chat_title: str,
        invite_link: str,
        project_info: str = "",
    ) -> bool:
        """Отправить email с invite-ссылкой на чат"""
        if not self.available:
            logger.warning("Email-сервис недоступен")
            return False

        subject = f"Приглашение в проектный чат: {chat_title}"

        html_body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background: #ffd93c; padding: 15px 20px; border-radius: 8px 8px 0 0;">
                    <h2 style="margin: 0; color: #333;">Festival Color</h2>
                </div>
                <div style="background: #fff; border: 1px solid #E0E0E0; border-top: none;
                            padding: 20px; border-radius: 0 0 8px 8px;">
                    <p>Здравствуйте, {recipient_name}!</p>
                    <p>Вас пригласили в рабочий чат проекта <b>{chat_title}</b>.</p>
                    {f'<p style="color: #666;">{project_info}</p>' if project_info else ''}
                    <p>Для присоединения нажмите на кнопку ниже:</p>
                    <div style="text-align: center; margin: 25px 0;">
                        <a href="{invite_link}"
                           style="background: #ffd93c; color: #333; padding: 12px 30px;
                                  border-radius: 6px; text-decoration: none; font-weight: 600;
                                  display: inline-block;">
                            Присоединиться к чату
                        </a>
                    </div>
                    <p style="color: #999; font-size: 12px;">
                        Если кнопка не работает, скопируйте ссылку:<br>
                        <a href="{invite_link}">{invite_link}</a>
                    </p>
                </div>
                <p style="color: #999; font-size: 11px; text-align: center; margin-top: 15px;">
                    Это автоматическое уведомление от CRM Festival Color.
                </p>
            </div>
        </body>
        </html>
        """

        return await self._send_email(to_email, subject, html_body)

    async def _send_email(
        self, to_email: str, subject: str, html_body: str
    ) -> bool:
        """Отправить email через SMTP"""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self._from_name} <{self._username}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            # Текстовая версия
            text_part = MIMEText(
                f"Вас пригласили в проектный чат. "
                f"Присоединяйтесь: {subject}",
                "plain", "utf-8"
            )
            html_part = MIMEText(html_body, "html", "utf-8")

            msg.attach(text_part)
            msg.attach(html_part)

            # SSL контекст
            tls_context = ssl.create_default_context()

            if self._use_tls and self._port == 465:
                # SSL/TLS (порт 465)
                await aiosmtplib.send(
                    msg,
                    hostname=self._host,
                    port=self._port,
                    username=self._username,
                    password=self._password,
                    use_tls=True,
                    tls_context=tls_context,
                )
            else:
                # STARTTLS (порт 587)
                await aiosmtplib.send(
                    msg,
                    hostname=self._host,
                    port=self._port,
                    username=self._username,
                    password=self._password,
                    start_tls=True,
                    tls_context=tls_context,
                )

            logger.info(f"Email отправлен на {to_email}")
            return True

        except Exception as e:
            logger.error(f"Ошибка отправки email на {to_email}: {e}")
            return False


# Синглтон
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Получить экземпляр EmailService"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
