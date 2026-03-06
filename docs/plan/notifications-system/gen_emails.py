"""Генератор HTML писем — Interior Studio CRM."""
import base64, os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

def b64img(rel_path, mime):
    with open(os.path.join(ROOT, rel_path), "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()

LOGO   = b64img("resources/festival_logo.png", "image/png")
FOOTER = b64img("resources/footer.jpg",         "image/jpeg")

# ─────────────────────────────────────────────────────────────────────────────
# Общие стили (шапка, футер, body-оболочка)
# ─────────────────────────────────────────────────────────────────────────────
COMMON_CSS = f"""
* {{ margin:0;padding:0;box-sizing:border-box; }}
body {{ font-family:'Segoe UI',Arial,sans-serif;background:#f0f0f0;
        padding:30px 15px;color:#333; }}
.wrap {{ max-width:620px;margin:0 auto; }}

/* ── ШАПКА: белый фон, желтая линия снизу ── */
.hdr {{
  background:#fff;
  border:1px solid #e0e0e0;
  border-bottom:4px solid #FFD93C;
  border-radius:14px 14px 0 0;
  padding:24px 28px;
  display:flex; align-items:center; gap:16px;
}}
.hdr-logo {{
  width:52px; height:52px; border-radius:50%;
  object-fit:cover; flex-shrink:0;
  box-shadow:0 2px 10px rgba(0,0,0,.15);
}}
.hdr-div {{
  width:1px; height:40px;
  background:#e0e0e0; flex-shrink:0;
}}
.hdr-brand {{
  font-size:17px; font-weight:900; color:#1a1a1a;
  letter-spacing:-.3px; line-height:1.1;
}}
.hdr-bureau {{
  font-size:10px; font-weight:400; letter-spacing:2.5px;
  text-transform:uppercase; color:#888; margin-top:2px;
}}
.hdr-right {{ border-left:1px solid #e8e8e8; padding-left:14px; margin-left:2px; }}
.hdr-crm {{ font-size:14px; font-weight:700; color:#1a1a1a; }}
.hdr-welcome {{ font-size:12px; color:#888; margin-top:2px; }}

/* ── ТЕЛО ── */
.body {{
  background:#fff;
  border:1px solid #e0e0e0; border-top:none;
  padding:28px 32px;
  border-radius:0 0 14px 14px;
}}
.greet {{ font-size:20px; font-weight:700; color:#1a1a1a; margin-bottom:7px; }}
.intro {{ font-size:14px; color:#555; line-height:1.65; margin-bottom:22px; }}

/* ── ШАГИ: просторные, одинаковая структура ── */
.step {{
  border-radius:12px;
  padding:22px 24px; margin-bottom:14px;
  display:flex; gap:16px; align-items:flex-start;
}}
.num {{
  display:flex; align-items:center; justify-content:center;
  width:30px; height:30px; border-radius:50%;
  font-size:13px; font-weight:700; flex-shrink:0; margin-top:2px;
}}
.step-content {{ flex:1; }}
.step-title {{
  font-size:15px; font-weight:700; color:#1a1a1a; margin-bottom:8px;
}}
.step-desc {{
  font-size:13px; color:#555; line-height:1.6; margin-bottom:14px;
}}

.s1 {{ background:#fff0f5; border-left:4px solid #E91E8C; }}
.s1 .num {{ background:#E91E8C; color:#fff; }}
.s2 {{ background:#f0f7ff; border-left:4px solid #2AABEE; }}
.s2 .num {{ background:#2AABEE; color:#fff; }}
.s3 {{ background:#f5f0ff; border-left:4px solid #7C3AED; }}
.s3 .num {{ background:#7C3AED; color:#fff; }}

/* ── КНОПКИ ── */
.btn {{
  display:inline-block; padding:9px 20px; border-radius:7px;
  text-decoration:none; font-size:13px; font-weight:600;
}}
.btn-pink {{ background:#E91E8C; color:#fff; }}
.btn-blue {{ background:#2AABEE; color:#fff; }}
.btn-hint {{
  display:block; margin-top:8px; font-size:11px; color:#aaa;
}}

/* ── УЧЁТНЫЕ ДАННЫЕ ── */
.creds {{
  width:100%; border-collapse:collapse;
  border:1px solid #e8e8e8; border-radius:7px;
  overflow:hidden; margin-top:8px;
}}
.creds td {{ padding:9px 13px; font-size:13px; }}
.creds tr + tr td {{ border-top:1px solid #f0f0f0; }}
.lbl {{ color:#aaa; width:75px; font-size:12px; }}
.val {{
  font-family:'Courier New',monospace; font-size:15px;
  font-weight:700; color:#1a1a1a; letter-spacing:.5px;
}}

/* ── ПОЛЯ С КОПИРОВАНИЕМ ── */
.copy-field {{
  position:relative; display:inline-flex; align-items:center;
  background:rgba(255,255,255,0.82);
  border:1px solid rgba(124,58,237,0.25);
  border-radius:8px; padding:9px 18px;
  cursor:default; transition:border-color .15s, box-shadow .15s;
  min-width:160px;
}}
.copy-field:hover {{
  border-color:rgba(124,58,237,0.55);
  box-shadow:0 2px 8px rgba(124,58,237,0.12);
}}
.copy-text {{
  font-family:'Courier New',monospace; font-size:15px;
  font-weight:700; color:#1a1a1a; letter-spacing:0.5px; flex:1;
}}
.copy-btn {{
  opacity:0; pointer-events:none;
  margin-left:10px; flex-shrink:0;
  background:rgba(124,58,237,0.10);
  border:1px solid rgba(124,58,237,0.25);
  border-radius:6px; padding:4px 6px;
  cursor:pointer; color:#7C3AED;
  display:flex; align-items:center; justify-content:center;
  transition:opacity .15s, background .15s;
}}
.copy-field:hover .copy-btn {{
  opacity:1; pointer-events:auto;
}}
.copy-btn:hover {{
  background:rgba(124,58,237,0.22);
}}
.copy-btn.copied {{
  color:#16a34a; background:rgba(22,163,74,0.12);
  border-color:rgba(22,163,74,0.3);
}}

/* ── РАЗДЕЛИТЕЛЬ + NOTE-блок с рамкой ── */
hr {{ border:none; border-top:1px solid #f0f0f0; margin:22px 0; }}
.note-box {{
  background:#fff; border:1px solid #e8e8e8; border-radius:10px;
  padding:16px 20px; margin-top:4px; text-align:center;
}}
.note {{ font-size:12px; color:#bbb; line-height:1.8; }}
.note a {{ color:#2AABEE; }}

/* ── ФУТЕР: белый блок с контактами ── */
.ft-wrap {{
  margin-top:16px;
  background:#fff;
  border:1px solid #e0e0e0;
  border-bottom:none;
  border-radius:12px 12px 0 0;
  padding:18px 24px 20px;
}}
.ft-brand-row {{
  display:flex; align-items:center; gap:10px; margin-bottom:14px;
}}
.ft-logo {{
  width:32px; height:32px; border-radius:50%;
  object-fit:cover; flex-shrink:0;
}}
.ft-brand-name {{
  font-size:13px; font-weight:700; color:#1a1a1a; letter-spacing:.3px;
}}
.ft-brand-sub {{ font-size:10px; color:#aaa; margin-top:1px; }}
.ft-contacts {{
  font-size:12px; color:#555; line-height:2;
  padding-top:14px; border-top:1px solid #f0f0f0;
}}
.ft-contacts a {{ color:#555; text-decoration:none; }}

/* ── ФУТЕР: тонкая полоска footer.jpg (полупрозрачная) ── */
.ft-strip {{
  position:relative; height:40px; overflow:hidden;
  border-radius:0 0 12px 12px;
}}
.ft-strip-bg {{
  background-image:url('{FOOTER}');
  background-size:cover; background-position:center;
  width:100%; height:100%;
  position:absolute; top:0; left:0;
}}
.ft-strip-box {{
  position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
  background:rgba(255,255,255,0.75);
  border:1px solid rgba(200,200,200,0.6);
  border-radius:4px; padding:3px 18px;
  font-size:10px; color:#555; white-space:nowrap;
  font-family:'Segoe UI',Arial,sans-serif;
  backdrop-filter:blur(2px);
}}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Письмо СОТРУДНИКУ (онбординг)
# ─────────────────────────────────────────────────────────────────────────────
EMPLOYEE = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Добро пожаловать в Festival Color CRM</title>
<style>{COMMON_CSS}</style>
</head>
<body>
<div class="wrap">

<!-- шапка -->
<div class="hdr">
  <img src="{LOGO}" class="hdr-logo" alt="FC">
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

<!-- тело -->
<div class="body">
  <p class="greet">Привет, Мария! 👋</p>
  <p class="intro">
    Вы добавлены в CRM-систему интерьерного бюро <strong>Festival Color</strong>.
    Следуйте трём шагам ниже, чтобы начать работу:
  </p>

  <!-- шаг 1 -->
  <div class="step s1">
    <span class="num">1</span>
    <div class="step-content">
      <div class="step-title">Скачайте программу</div>
      <p class="step-desc">
        Скачайте установочный архив, распакуйте и запустите файл
        <strong>InteriorStudio.exe</strong>
      </p>
      <a href="#" class="btn btn-pink">⬇ Скачать Interior Studio CRM</a>
      <span class="btn-hint">Файл .zip → распакуйте в любую папку → запустите .exe</span>
    </div>
  </div>

  <!-- шаг 2 -->
  <div class="step s2">
    <span class="num">2</span>
    <div class="step-content">
      <div class="step-title">Подключите Telegram-уведомления</div>
      <p class="step-desc">
        Нажмите кнопку ниже — откроется наш Telegram-бот. Нажмите
        <strong>Старт</strong> и ваш аккаунт будет автоматически привязан.
        Вы будете получать уведомления о дедлайнах, назначениях и изменениях.
      </p>
      <a href="https://t.me/festival_color_crm_bot?start=TOKEN_PLACEHOLDER"
         class="btn btn-blue">✈ Подключить Telegram</a>
      <span class="btn-hint">
        Ссылка действительна 7 дней. Если не успели — попросите администратора
        выслать приглашение повторно.
      </span>
    </div>
  </div>

  <!-- шаг 3 -->
  <div class="step s3">
    <span class="num">3</span>
    <div class="step-content">
      <div class="step-title">Войдите в программу</div>
      <p class="step-desc">Введите эти данные при первом запуске программы:</p>
      <div style="display:flex;flex-direction:column;gap:8px;margin-top:4px;">
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="color:#aaa;font-size:12px;width:56px;flex-shrink:0;">Логин</span>
          <div class="copy-field" data-value="ivanova_m">
            <span class="copy-text">ivanova_m</span>
            <button class="copy-btn" onclick="copyField(this)" title="Скопировать">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:12px;">
          <span style="color:#aaa;font-size:12px;width:56px;flex-shrink:0;">Пароль</span>
          <div class="copy-field" data-value="Qwe12345!">
            <span class="copy-text">Qwe12345!</span>
            <button class="copy-btn" onclick="copyField(this)" title="Скопировать">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <hr>
  <div class="note-box">
    <p class="note">
      Если возникли трудности — обратитесь к руководителю или напишите на
      <a href="mailto:festivalcolor@mail.ru">festivalcolor@mail.ru</a><br>
      Это письмо отправлено автоматически — отвечать на него не нужно.
    </p>
  </div>
</div>

<!-- футер: белый блок -->
<div class="ft-wrap">
  <div class="ft-brand-row">
    <img src="{LOGO}" class="ft-logo" alt="FC">
    <div>
      <div class="ft-brand-name">FESTIVAL COLOR</div>
      <div class="ft-brand-sub">Interior Design Bureau</div>
    </div>
  </div>
  <div class="ft-contacts">
    Интерьерное бюро FESTIVAL COLOR<br>
    📍 Санкт-Петербург, ул. Плуталова 23<br>
    📞 <a href="tel:+79992800700">+7 (999) 2 800 700</a><br>
    ✉ <a href="mailto:festivalcolor@mail.ru">festivalcolor@mail.ru</a>
  </div>
</div>

<!-- футер: полоска footer.jpg -->
<div class="ft-strip">
  <div class="ft-strip-bg"></div>
  <div class="ft-strip-box">Интерьерное бюро FESTIVAL COLOR — 2026</div>
</div>

</div><!-- /wrap -->
<script>
function copyField(btn) {{
  var field = btn.closest('.copy-field');
  var text = field.getAttribute('data-value');
  navigator.clipboard.writeText(text).then(function() {{
    btn.classList.add('copied');
    btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
    setTimeout(function() {{
      btn.classList.remove('copied');
      btn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
    }}, 1800);
  }});
}}
</script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
# Письмо КЛИЕНТУ (приглашение в чат)
# ─────────────────────────────────────────────────────────────────────────────
CLIENT = f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Приглашение в проектный чат — Festival Color</title>
<style>
{COMMON_CSS}

/* Карточка проекта */
.project-card {{
  background:#fffbea; border-left:4px solid #FFD93C;
  border-radius:12px; padding:14px 18px; margin-bottom:18px;
}}
.project-card-title {{
  font-size:11px; color:#aaa; text-transform:uppercase;
  letter-spacing:.6px; font-weight:600; margin-bottom:10px;
}}
.prow {{ display:flex; gap:8px; margin-bottom:5px; }}
.plbl {{ font-size:13px; color:#aaa; width:130px; flex-shrink:0; }}
.pval {{ font-size:13px; color:#1a1a1a; font-weight:600; }}

/* Блок чата */
.chat-block {{
  background:#f0f7ff; border-left:4px solid #2AABEE;
  border-radius:0 8px 8px 0; padding:16px 18px; margin-bottom:18px;
}}
.chat-block p {{ font-size:13px; color:#444; line-height:1.65; margin-bottom:11px; }}
.chat-block p:last-child {{ margin-bottom:0; }}

/* Список */
.features {{ list-style:none; margin:8px 0 0; }}
.features li {{
  font-size:13px; color:#555; line-height:1.8;
  padding-left:16px; position:relative;
}}
.features li::before {{
  content:"•"; color:#2AABEE; position:absolute;
  left:3px; font-size:15px; line-height:1.6;
}}
</style>
</head>
<body>
<div class="wrap">

<!-- шапка -->
<div class="hdr">
  <img src="{LOGO}" class="hdr-logo" alt="FC">
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

<!-- тело -->
<div class="body">
  <p class="greet">Добрый день, Александр!</p>
  <p class="intro">
    Для вашего проекта создан персональный рабочий чат в Telegram.
    В нём вы будете получать обновления о ходе работ, фотоотчёты
    и уведомления о завершённых этапах — напрямую от команды бюро.
  </p>

  <!-- карточка проекта -->
  <div class="project-card">
    <div class="project-card-title">Ваш проект</div>
    <div class="prow">
      <span class="plbl">Адрес объекта:</span>
      <span class="pval">Москва, Кутузовский пр. 220</span>
    </div>
    <div class="prow">
      <span class="plbl">Тип проекта:</span>
      <span class="pval">Индивидуальный дизайн-проект</span>
    </div>
    <div class="prow">
      <span class="plbl">Старший менеджер:</span>
      <span class="pval">Иванова Мария Сергеевна</span>
    </div>
  </div>

  <!-- блок приглашения -->
  <div class="step s2">
    <span class="num" style="background:#2AABEE;color:#fff;">✈</span>
    <div class="step-content">
      <div class="step-title">Присоединитесь к проектному чату</div>
      <p class="step-desc">
        Нажмите кнопку ниже — откроется Telegram с вашим проектным чатом.
        Если Telegram ещё не установлен —
        <a href="https://telegram.org" style="color:#2AABEE;">скачайте его</a>
        и затем перейдите по ссылке.
      </p>
      <p class="step-desc" style="margin-bottom:11px;">
        <strong>В чате вы будете получать:</strong>
      </p>
      <ul class="features">
        <li>Уведомления о завершении каждого этапа проекта</li>
        <li>Фотоотчёты о ходе работ</li>
        <li>Запросы на согласование решений</li>
        <li>Сообщения напрямую от вашего менеджера</li>
      </ul>
      <br>
      <a href="INVITE_LINK_PLACEHOLDER" class="btn btn-blue">
        ✈ Перейти в проектный чат
      </a>
      <span class="btn-hint">
        Ссылка действительна 7 дней. По вопросам:
        <a href="tel:+79992800700" style="color:#aaa;">+7 (999) 2 800 700</a>
      </span>
    </div>
  </div>

  <hr>
  <div class="note-box">
    <p class="note">
      Это письмо отправлено автоматически — отвечать на него не нужно.<br>
      По вопросам: <a href="mailto:festivalcolor@mail.ru">festivalcolor@mail.ru</a>
    </p>
  </div>
</div>

<!-- футер: белый блок -->
<div class="ft-wrap">
  <div class="ft-brand-row">
    <img src="{LOGO}" class="ft-logo" alt="FC">
    <div>
      <div class="ft-brand-name">FESTIVAL COLOR</div>
      <div class="ft-brand-sub">Interior Design Bureau</div>
    </div>
  </div>
  <div class="ft-contacts">
    Интерьерное бюро FESTIVAL COLOR<br>
    📍 Санкт-Петербург, ул. Плуталова 23<br>
    📞 <a href="tel:+79992800700">+7 (999) 2 800 700</a><br>
    ✉ <a href="mailto:festivalcolor@mail.ru">festivalcolor@mail.ru</a>
  </div>
</div>

<!-- футер: полоска footer.jpg -->
<div class="ft-strip">
  <div class="ft-strip-bg"></div>
  <div class="ft-strip-box">Интерьерное бюро FESTIVAL COLOR — 2026</div>
</div>

</div><!-- /wrap -->
</body>
</html>"""

out_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(out_dir, "welcome_email_preview.html"), "w", encoding="utf-8") as f:
    f.write(EMPLOYEE)
print("OK: welcome_email_preview.html")

with open(os.path.join(out_dir, "client_invite_email_preview.html"), "w", encoding="utf-8") as f:
    f.write(CLIENT)
print("OK: client_invite_email_preview.html")
