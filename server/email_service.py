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

    async def send_welcome_email(
        self,
        to_email: str,
        employee_name: str,
        login: str,
        password: str,
        telegram_token: str,
        bot_username: str = "festival_color_crm_bot",
    ) -> bool:
        """Отправить приветственное письмо новому сотруднику с данными для входа и Telegram-ссылкой"""
        if not self.available:
            logger.warning("Email-сервис недоступен")
            return False

        first_name = employee_name.split()[1] if len(employee_name.split()) > 1 else employee_name
        subject = "Добро пожаловать в Festival Color CRM"
        telegram_link = f"https://t.me/{bot_username}?start={telegram_token}"

        html_body = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<style>
* {{ margin:0;padding:0;box-sizing:border-box; }}
body {{ font-family:'Segoe UI',Arial,sans-serif;background:#f0f0f0;padding:30px 15px;color:#333; }}
.wrap {{ max-width:620px;margin:0 auto; }}
.hdr {{ background:#fff;border:1px solid #e0e0e0;border-bottom:4px solid #FFD93C;border-radius:14px 14px 0 0;padding:24px 28px; }}
.hdr-brand {{ font-size:17px;font-weight:900;color:#1a1a1a; }}
.hdr-bureau {{ font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#888;margin-top:2px; }}
.body {{ background:#fff;border:1px solid #e0e0e0;border-top:none;padding:28px 32px;border-radius:0 0 14px 14px; }}
.greet {{ font-size:20px;font-weight:700;color:#1a1a1a;margin-bottom:7px; }}
.sub {{ font-size:14px;color:#888;margin-bottom:20px; }}
.step {{ background:#f8f9fa;border-radius:12px;padding:22px 24px;margin-bottom:14px; }}
.step-num {{ display:inline-block;width:28px;height:28px;border-radius:50%;background:#FFD93C;color:#1a1a1a;font-weight:700;font-size:13px;text-align:center;line-height:28px;margin-bottom:10px; }}
.step-title {{ font-size:14px;font-weight:700;color:#1a1a1a;margin-bottom:8px; }}
.copy-field {{ background:#fff;border:1.5px solid #e0e0e0;border-radius:8px;padding:12px 16px;font-family:monospace;font-size:14px;color:#1a1a1a;margin-bottom:8px;word-break:break-all; }}
.label {{ font-size:11px;color:#888;margin-bottom:4px; }}
.btn {{ display:inline-block;background:#2AABEE;color:#fff;padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px;margin-top:10px; }}
.ft {{ margin-top:20px;background:#fff;border:1px solid #e0e0e0;border-radius:10px;padding:16px 20px;display:flex;gap:12px;align-items:center; }}
.ft-info {{ font-size:11px;color:#888; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <div class="hdr-brand">Festival Color</div>
    <div class="hdr-bureau">Дизайн-бюро интерьера</div>
  </div>
  <div class="body">
    <div class="greet">Добро пожаловать, {first_name}!</div>
    <div class="sub">Ваш аккаунт в CRM Festival Color создан. Ниже — всё необходимое для начала работы.</div>
    <div class="step">
      <div class="step-num">1</div>
      <div class="step-title">Данные для входа в CRM</div>
      <div class="label">Логин</div>
      <div class="copy-field">{login}</div>
      <div class="label">Пароль (смените при первом входе)</div>
      <div class="copy-field">{password}</div>
    </div>
    <div class="step">
      <div class="step-num">2</div>
      <div class="step-title">Подключите Telegram для уведомлений</div>
      <p style="font-size:14px;color:#555;margin-bottom:12px;">Нажмите кнопку ниже, чтобы подключить наш Telegram-бот. После этого вы будете получать уведомления о новых задачах и изменениях по проектам.</p>
      <a href="{telegram_link}" class="btn">Подключить Telegram</a>
      <p style="font-size:11px;color:#aaa;margin-top:10px;">Или скопируйте ссылку: {telegram_link}</p>
    </div>
  </div>
  <div class="ft">
    <div class="ft-info">
      Это автоматическое письмо от CRM Festival Color.<br>
      Если у вас есть вопросы — обратитесь к администратору.
    </div>
  </div>
</div>
</body>
</html>"""

        return await self._send_email(to_email, subject, html_body)

    async def send_client_chat_invite(
        self,
        to_email: str,
        client_name: str,
        project_address: str,
        project_type: str,
        manager_name: str,
        invite_link: str,
    ) -> bool:
        """Отправить email-приглашение клиенту в проектный Telegram-чат"""
        if not self.available:
            logger.warning("Email-сервис недоступен")
            return False

        first_name = client_name.split()[1] if len(client_name.split()) > 1 else client_name
        subject = f"Приглашение в проектный чат: {project_address}"

        html_body = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<style>
* {{ margin:0;padding:0;box-sizing:border-box; }}
body {{ font-family:'Segoe UI',Arial,sans-serif;background:#f0f0f0;padding:30px 15px;color:#333; }}
.wrap {{ max-width:620px;margin:0 auto; }}
.hdr {{ background:#fff;border:1px solid #e0e0e0;border-bottom:4px solid #FFD93C;border-radius:14px 14px 0 0;padding:24px 28px; }}
.hdr-brand {{ font-size:17px;font-weight:900;color:#1a1a1a; }}
.hdr-bureau {{ font-size:10px;letter-spacing:2.5px;text-transform:uppercase;color:#888;margin-top:2px; }}
.body {{ background:#fff;border:1px solid #e0e0e0;border-top:none;padding:28px 32px;border-radius:0 0 14px 14px; }}
.greet {{ font-size:20px;font-weight:700;color:#1a1a1a;margin-bottom:7px; }}
.sub {{ font-size:14px;color:#888;margin-bottom:20px; }}
.info-card {{ background:#f8f9fa;border-radius:12px;padding:18px 20px;margin-bottom:20px; }}
.info-row {{ display:flex;justify-content:space-between;margin-bottom:8px;font-size:14px; }}
.info-label {{ color:#888; }}
.info-value {{ font-weight:600;color:#1a1a1a; }}
.btn {{ display:inline-block;background:#2AABEE;color:#fff;padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:700;font-size:15px; }}
.ft {{ margin-top:20px;background:#fff;border:1px solid #e0e0e0;border-radius:10px;padding:16px 20px; }}
.ft-info {{ font-size:11px;color:#888; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="hdr">
    <div class="hdr-brand">Festival Color</div>
    <div class="hdr-bureau">Дизайн-бюро интерьера</div>
  </div>
  <div class="body">
    <div class="greet">Здравствуйте, {first_name}!</div>
    <div class="sub">Вас приглашают в закрытый Telegram-чат вашего проекта.</div>
    <div class="info-card">
      <div class="info-row"><span class="info-label">Объект</span><span class="info-value">{project_address}</span></div>
      <div class="info-row"><span class="info-label">Тип проекта</span><span class="info-value">{project_type}</span></div>
      <div class="info-row"><span class="info-label">Ваш менеджер</span><span class="info-value">{manager_name}</span></div>
    </div>
    <p style="font-size:14px;color:#555;margin-bottom:20px;">В чате вы сможете задавать вопросы по проекту, получать обновления и обсуждать детали напрямую с командой.</p>
    <div style="text-align:center;">
      <a href="{invite_link}" class="btn">Присоединиться к чату</a>
    </div>
    <p style="font-size:11px;color:#aaa;margin-top:12px;text-align:center;">Или скопируйте ссылку: {invite_link}</p>
  </div>
  <div class="ft">
    <div class="ft-info">Это автоматическое письмо от CRM Festival Color.</div>
  </div>
</div>
</body>
</html>"""

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
