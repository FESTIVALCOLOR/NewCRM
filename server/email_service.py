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
        download_link: str = "#",
    ) -> bool:
        """Отправить приветственное письмо новому сотруднику с данными для входа и Telegram-ссылкой"""
        if not self.available:
            logger.warning("Email-сервис недоступен")
            return False

        first_name = employee_name.split()[1] if len(employee_name.split()) > 1 else employee_name
        subject = "Добро пожаловать в Festival Color CRM"
        telegram_link = f"https://t.me/{bot_username}?start={telegram_token}"

        copy_svg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'

        html_body = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
* {{ margin:0;padding:0;box-sizing:border-box; }}
body {{ font-family:'Segoe UI',Arial,sans-serif;background:#f0f0f0;padding:30px 15px;color:#333; }}
.wrap {{ max-width:620px;margin:0 auto; }}
.hdr {{ background:#fff;border:1px solid #e0e0e0;border-bottom:4px solid #FFD93C;border-radius:14px 14px 0 0;padding:24px 28px;display:flex;align-items:center;gap:16px; }}
.hdr-div {{ width:1px;height:40px;background:#e0e0e0;flex-shrink:0; }}
.hdr-brand {{ font-size:17px;font-weight:900;color:#1a1a1a;letter-spacing:-.3px;line-height:1.1; }}
.hdr-bureau {{ font-size:10px;font-weight:400;letter-spacing:2.5px;text-transform:uppercase;color:#888;margin-top:2px; }}
.hdr-right {{ border-left:1px solid #e8e8e8;padding-left:14px;margin-left:2px; }}
.hdr-crm {{ font-size:14px;font-weight:700;color:#1a1a1a; }}
.hdr-welcome {{ font-size:12px;color:#888;margin-top:2px; }}
.body {{ background:#fff;border:1px solid #e0e0e0;border-top:none;padding:28px 32px;border-radius:0 0 14px 14px; }}
.greet {{ font-size:20px;font-weight:700;color:#1a1a1a;margin-bottom:7px; }}
.intro {{ font-size:14px;color:#555;line-height:1.65;margin-bottom:22px; }}
.step {{ border-radius:12px;padding:22px 24px;margin-bottom:14px;display:flex;gap:16px;align-items:flex-start; }}
.num {{ display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:50%;font-size:13px;font-weight:700;flex-shrink:0;margin-top:2px; }}
.step-content {{ flex:1; }}
.step-title {{ font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:8px; }}
.step-desc {{ font-size:13px;color:#555;line-height:1.6;margin-bottom:14px; }}
.s1 {{ background:#fff0f5;border-left:4px solid #E91E8C; }}
.s1 .num {{ background:#E91E8C;color:#fff; }}
.s2 {{ background:#f0f7ff;border-left:4px solid #2AABEE; }}
.s2 .num {{ background:#2AABEE;color:#fff; }}
.s3 {{ background:#f5f0ff;border-left:4px solid #7C3AED; }}
.s3 .num {{ background:#7C3AED;color:#fff; }}
.btn {{ display:inline-block;padding:9px 20px;border-radius:7px;text-decoration:none;font-size:13px;font-weight:600; }}
.btn-pink {{ background:#E91E8C;color:#fff; }}
.btn-blue {{ background:#2AABEE;color:#fff; }}
.btn-hint {{ display:block;margin-top:8px;font-size:11px;color:#aaa; }}
.copy-field {{ position:relative;display:inline-flex;align-items:center;background:rgba(255,255,255,0.82);border:1px solid rgba(124,58,237,0.25);border-radius:8px;padding:9px 18px;min-width:160px; }}
.copy-text {{ font-family:'Courier New',monospace;font-size:15px;font-weight:700;color:#1a1a1a;letter-spacing:0.5px;flex:1; }}
hr {{ border:none;border-top:1px solid #f0f0f0;margin:22px 0; }}
.note-box {{ background:#fff;border:1px solid #e8e8e8;border-radius:10px;padding:16px 20px;margin-top:4px;text-align:center; }}
.note {{ font-size:12px;color:#bbb;line-height:1.8; }}
.note a {{ color:#2AABEE; }}
.ft-wrap {{ margin-top:16px;background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:18px 24px 20px; }}
.ft-brand-name {{ font-size:13px;font-weight:700;color:#1a1a1a;letter-spacing:.3px; }}
.ft-brand-sub {{ font-size:10px;color:#aaa;margin-top:1px; }}
.ft-contacts {{ font-size:12px;color:#555;line-height:2;padding-top:14px;border-top:1px solid #f0f0f0; }}
.ft-contacts a {{ color:#555;text-decoration:none; }}
</style>
</head>
<body>
<div class="wrap">
<div class="hdr">
  <div>
    <div class="hdr-brand">FESTIVAL<br>COLOR</div>
    <div class="hdr-bureau">Interior Design Bureau</div>
  </div>
  <div class="hdr-div"></div>
  <div class="hdr-right">
    <div class="hdr-crm">CRM — система управления заказами</div>
    <div class="hdr-welcome">Добро пожаловать в команду!</div>
  </div>
</div>
<div class="body">
  <p class="greet">Привет, {first_name}!</p>
  <p class="intro">Вы добавлены в CRM-систему интерьерного бюро <strong>Festival Color</strong>.
  Следуйте трём шагам ниже, чтобы начать работу:</p>
  <div class="step s1">
    <span class="num">1</span>
    <div class="step-content">
      <div class="step-title">Скачайте программу</div>
      <p class="step-desc">Скачайте установочный архив, распакуйте и запустите файл <strong>InteriorStudio.exe</strong></p>
      <a href="{download_link}" class="btn btn-pink">Скачать Interior Studio CRM</a>
      <span class="btn-hint">Файл .zip → распакуйте в любую папку → запустите .exe</span>
    </div>
  </div>
  <div class="step s2">
    <span class="num">2</span>
    <div class="step-content">
      <div class="step-title">Подключите Telegram-уведомления</div>
      <p class="step-desc">Нажмите кнопку ниже — откроется наш Telegram-бот. Нажмите <strong>Старт</strong> и ваш аккаунт будет автоматически привязан. Вы будете получать уведомления о дедлайнах, назначениях и изменениях.</p>
      <a href="{telegram_link}" class="btn btn-blue">Подключить Telegram</a>
      <span class="btn-hint">Ссылка действительна 7 дней. Если не успели — попросите администратора выслать приглашение повторно.</span>
    </div>
  </div>
  <div class="step s3">
    <span class="num">3</span>
    <div class="step-content">
      <div class="step-title">Войдите в программу</div>
      <p class="step-desc">Введите эти данные при первом запуске программы:</p>
      <div style="display:flex;flex-direction:column;gap:8px;margin-top:4px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="color:#aaa;font-size:12px;width:56px;flex-shrink:0;">Логин</span>
          <div class="copy-field"><span class="copy-text">{login}</span></div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="color:#aaa;font-size:12px;width:56px;flex-shrink:0;">Пароль</span>
          <div class="copy-field"><span class="copy-text">{password}</span></div>
        </div>
      </div>
    </div>
  </div>
  <hr>
  <div class="note-box">
    <p class="note">Если возникли трудности — обратитесь к руководителю или напишите на
    <a href="mailto:festivalcolor@mail.ru">festivalcolor@mail.ru</a><br>
    Это письмо отправлено автоматически — отвечать на него не нужно.</p>
  </div>
</div>
<div class="ft-wrap">
  <div class="ft-brand-name">FESTIVAL COLOR</div>
  <div class="ft-brand-sub">Interior Design Bureau</div>
  <div class="ft-contacts">
    Интерьерное бюро FESTIVAL COLOR<br>
    <a href="mailto:festivalcolor@mail.ru">festivalcolor@mail.ru</a>
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
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<style>
* {{ margin:0;padding:0;box-sizing:border-box; }}
body {{ font-family:'Segoe UI',Arial,sans-serif;background:#f0f0f0;padding:30px 15px;color:#333; }}
.wrap {{ max-width:620px;margin:0 auto; }}
.hdr {{ background:#fff;border:1px solid #e0e0e0;border-bottom:4px solid #FFD93C;border-radius:14px 14px 0 0;padding:24px 28px;display:flex;align-items:center;gap:16px; }}
.hdr-div {{ width:1px;height:40px;background:#e0e0e0;flex-shrink:0; }}
.hdr-brand {{ font-size:17px;font-weight:900;color:#1a1a1a;letter-spacing:-.3px;line-height:1.1; }}
.hdr-bureau {{ font-size:10px;font-weight:400;letter-spacing:2.5px;text-transform:uppercase;color:#888;margin-top:2px; }}
.hdr-right {{ border-left:1px solid #e8e8e8;padding-left:14px;margin-left:2px; }}
.hdr-crm {{ font-size:14px;font-weight:700;color:#1a1a1a; }}
.hdr-welcome {{ font-size:12px;color:#888;margin-top:2px; }}
.body {{ background:#fff;border:1px solid #e0e0e0;border-top:none;padding:28px 32px;border-radius:0 0 14px 14px; }}
.greet {{ font-size:20px;font-weight:700;color:#1a1a1a;margin-bottom:7px; }}
.intro {{ font-size:14px;color:#555;line-height:1.65;margin-bottom:22px; }}
.step {{ border-radius:12px;padding:22px 24px;margin-bottom:14px;display:flex;gap:16px;align-items:flex-start; }}
.num {{ display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:50%;font-size:13px;font-weight:700;flex-shrink:0;margin-top:2px; }}
.step-content {{ flex:1; }}
.step-title {{ font-size:15px;font-weight:700;color:#1a1a1a;margin-bottom:8px; }}
.step-desc {{ font-size:13px;color:#555;line-height:1.6;margin-bottom:14px; }}
.s2 {{ background:#f0f7ff;border-left:4px solid #2AABEE; }}
.s2 .num {{ background:#2AABEE;color:#fff; }}
.btn {{ display:inline-block;padding:9px 20px;border-radius:7px;text-decoration:none;font-size:13px;font-weight:600; }}
.btn-blue {{ background:#2AABEE;color:#fff; }}
.btn-hint {{ display:block;margin-top:8px;font-size:11px;color:#aaa; }}
.project-card {{ background:#fffbea;border-left:4px solid #FFD93C;border-radius:12px;padding:14px 18px;margin-bottom:18px; }}
.project-card-title {{ font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:.6px;font-weight:600;margin-bottom:10px; }}
.prow {{ display:flex;gap:8px;margin-bottom:5px; }}
.plbl {{ font-size:13px;color:#aaa;width:130px;flex-shrink:0; }}
.pval {{ font-size:13px;color:#1a1a1a;font-weight:600; }}
.features {{ list-style:none;margin:8px 0 0; }}
.features li {{ font-size:13px;color:#555;line-height:1.8;padding-left:16px;position:relative; }}
.features li::before {{ content:"•";color:#2AABEE;position:absolute;left:3px;font-size:15px;line-height:1.6; }}
hr {{ border:none;border-top:1px solid #f0f0f0;margin:22px 0; }}
.note-box {{ background:#fff;border:1px solid #e8e8e8;border-radius:10px;padding:16px 20px;margin-top:4px;text-align:center; }}
.note {{ font-size:12px;color:#bbb;line-height:1.8; }}
.note a {{ color:#2AABEE; }}
.ft-wrap {{ margin-top:16px;background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:18px 24px 20px; }}
.ft-brand-name {{ font-size:13px;font-weight:700;color:#1a1a1a;letter-spacing:.3px; }}
.ft-brand-sub {{ font-size:10px;color:#aaa;margin-top:1px; }}
.ft-contacts {{ font-size:12px;color:#555;line-height:2;padding-top:14px;border-top:1px solid #f0f0f0; }}
.ft-contacts a {{ color:#555;text-decoration:none; }}
</style>
</head>
<body>
<div class="wrap">
<div class="hdr">
  <div>
    <div class="hdr-brand">FESTIVAL<br>COLOR</div>
    <div class="hdr-bureau">Interior Design Bureau</div>
  </div>
  <div class="hdr-div"></div>
  <div class="hdr-right">
    <div class="hdr-crm">Проектный чат</div>
    <div class="hdr-welcome">Приглашение для участия в вашем проекте</div>
  </div>
</div>
<div class="body">
  <p class="greet">Добрый день, {first_name}!</p>
  <p class="intro">Для вашего проекта создан персональный рабочий чат в Telegram.
  В нём вы будете получать обновления о ходе работ, фотоотчёты
  и уведомления о завершённых этапах — напрямую от команды бюро.</p>
  <div class="project-card">
    <div class="project-card-title">Ваш проект</div>
    <div class="prow">
      <span class="plbl">Адрес объекта:</span>
      <span class="pval">{project_address}</span>
    </div>
    <div class="prow">
      <span class="plbl">Тип проекта:</span>
      <span class="pval">{project_type}</span>
    </div>
    <div class="prow">
      <span class="plbl">Старший менеджер:</span>
      <span class="pval">{manager_name}</span>
    </div>
  </div>
  <div class="step s2">
    <span class="num" style="background:#2AABEE;color:#fff;">✈</span>
    <div class="step-content">
      <div class="step-title">Присоединитесь к проектному чату</div>
      <p class="step-desc">Нажмите кнопку ниже — откроется Telegram с вашим проектным чатом.</p>
      <p class="step-desc" style="margin-bottom:11px;"><strong>В чате вы будете получать:</strong></p>
      <ul class="features">
        <li>Уведомления о завершении каждого этапа проекта</li>
        <li>Фотоотчёты о ходе работ</li>
        <li>Запросы на согласование решений</li>
        <li>Сообщения напрямую от вашего менеджера</li>
      </ul>
      <br>
      <a href="{invite_link}" class="btn btn-blue">Перейти в проектный чат</a>
      <span class="btn-hint">Ссылка действительна 7 дней. Или скопируйте: {invite_link}</span>
    </div>
  </div>
  <hr>
  <div class="note-box">
    <p class="note">Это письмо отправлено автоматически — отвечать на него не нужно.<br>
    По вопросам: <a href="mailto:festivalcolor@mail.ru">festivalcolor@mail.ru</a></p>
  </div>
</div>
<div class="ft-wrap">
  <div class="ft-brand-name">FESTIVAL COLOR</div>
  <div class="ft-brand-sub">Interior Design Bureau</div>
  <div class="ft-contacts">
    Интерьерное бюро FESTIVAL COLOR<br>
    <a href="mailto:festivalcolor@mail.ru">festivalcolor@mail.ru</a>
  </div>
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

            text_part = MIMEText(
                f"Вас пригласили. Присоединяйтесь: {subject}",
                "plain", "utf-8"
            )
            html_part = MIMEText(html_body, "html", "utf-8")

            msg.attach(text_part)
            msg.attach(html_part)

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
            raise


# Синглтон
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Получить экземпляр EmailService"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
