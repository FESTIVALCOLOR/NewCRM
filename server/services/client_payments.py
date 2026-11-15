"""
Оплаты клиента по договору: план платежей, проведение оплаты, документ об оплате, доп. соглашения
(увеличение и уменьшение стоимости), расчёт при расторжении, возвраты.

Источник правды — таблица contract_client_payments. Первые три платежа (аванс, 2-й, 3-й) зеркалируются
в старые поля договора (advance_payment / *_paid_date и т.д.): на них опираются сроки проекта, дашборды, отчёты.

Документ об оплате — «Документ, подтверждающий расчёт» (п. 2.1 ст. 2 54-ФЗ, ИП на ПСН, дизайн — пп. 27 п. 2 ст. 346.43 НК):
сквозной порядковый номер в пределах года, реквизиты фиксируются в момент выдачи.
"""

from datetime import datetime, timedelta
import logging
import secrets

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError

from database import Client, ClientPaymentDoc, ClientPaymentSetting, Contract, ContractClientPayment, Employee

logger = logging.getLogger(__name__)

MSK = timedelta(hours=3)
BASE_KINDS = ("advance", "additional", "third")
AMOUNT_FIELDS = {"advance": "advance_payment", "additional": "additional_payment", "third": "third_payment"}
PAID_DATE_FIELDS = {k: f"{k}_payment_paid_date" for k in BASE_KINDS}
INDIVIDUAL_TITLES = {"advance": "1 платёж (Аванс)", "additional": "2 платёж (Доплата)", "third": "3 платёж (Доплата)"}
OPEN_STATUSES = ("planned", "link_sent")
METHODS = {
    "sbp": "безналичный расчёт (СБП)",
    "cash": "наличные денежные средства",
    "transfer": "безналичный расчёт (перевод на расчётный счёт)",
    "card": "безналичный расчёт (банковская карта)",
}
LOCKED_CONTRACT_FIELDS = ("total_amount", "advance_payment", "additional_payment", "third_payment")

DEFAULT_SETTINGS = {
    "sbp_link": "",
    "message_template": ("Здравствуйте, {клиент}!\nОплата по договору № {договор} ({платёж}): {сумма}.\nОплатить по СБП: {ссылка}\nПри оплате, пожалуйста, укажите сумму {сумма}."),
    "seller_name": "",
    "seller_inn": "",
    "seller_ogrnip": "",
    "tax_system": "Патентная система налогообложения (ПСН)",
    "service_name": "Услуги по разработке дизайн-проекта интерьера",
    "place_remote": "https://festivalcolor.ru",
    "place_office": "",
    "cashier": "",  # «Расчёт осуществил»: всегда руководитель; пусто — берём действующего «Руководителя студии»
    "public_base_url": "https://crm.festivalcolor.ru",
}


def _round(value):
    return round(float(value or 0), 2)


# ── Настройки ────────────────────────────────────────────────────────────────


def get_settings(db):
    stored = {s.key: s.value for s in db.query(ClientPaymentSetting).all()}
    return {key: stored.get(key, default) if stored.get(key) is not None else default for key, default in DEFAULT_SETTINGS.items()}


def save_settings(db, data):
    for key, value in data.items():
        if key not in DEFAULT_SETTINGS:
            continue
        row = db.query(ClientPaymentSetting).filter(ClientPaymentSetting.key == key).first()
        value = (value or "").strip() if isinstance(value, str) else value
        if row:
            row.value = value
        else:
            db.add(ClientPaymentSetting(key=key, value=value))
    db.commit()
    return get_settings(db)


def director_cashier(db, settings):
    """«Расчёт осуществил» в документе — всегда руководитель студии (не менеджер, нажавший кнопку)."""
    if (settings.get("cashier") or "").strip():
        return settings["cashier"].strip()
    from constants import POSITION_STUDIO_DIRECTOR

    director = db.query(Employee).filter(Employee.position == POSITION_STUDIO_DIRECTOR, Employee.status == "активный").order_by(Employee.id).first()
    return f"{POSITION_STUDIO_DIRECTOR} {director.full_name}" if director else ""


def requisites_missing(settings):
    names = {"seller_name": "ФИО ИП", "seller_inn": "ИНН", "tax_system": "система налогообложения", "service_name": "наименование услуги"}
    return [label for key, label in names.items() if not (settings.get(key) or "").strip()]


# ── План платежей и синхронизация со старыми полями договора ──────────────────


def _uses_plan(contract):
    return contract.project_type in ("Индивидуальный", "Шаблонный")


def _base_amount(contract, kind):
    if contract.project_type == "Шаблонный":
        return _round(contract.advance_payment or contract.total_amount)
    return _round(getattr(contract, AMOUNT_FIELDS[kind]))


def _base_kinds(contract):
    return ("advance",) if contract.project_type == "Шаблонный" else BASE_KINDS


def _rows(db, contract_id):
    return db.query(ContractClientPayment).filter(ContractClientPayment.contract_id == contract_id).order_by(ContractClientPayment.sort_order, ContractClientPayment.id).all()


def ensure_rows(db, contract):
    """Создать план платежей для договора (один раз): из сумм и дат оплат, уже записанных в договоре."""
    if not _uses_plan(contract):
        return
    if db.query(ContractClientPayment.id).filter(ContractClientPayment.contract_id == contract.id).first():
        return
    try:
        # Сервер работает в нескольких процессах — не даём создать план дважды
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 7_700_000_000 + contract.id})
        if db.query(ContractClientPayment.id).filter(ContractClientPayment.contract_id == contract.id).first():
            return
    except Exception:
        db.rollback()  # не PostgreSQL (тесты на SQLite) — без блокировки
    if contract.project_type == "Шаблонный" and not contract.advance_payment and contract.total_amount:
        # Закрепляем сумму единственного платежа: иначе доплаты по доп. соглашениям «перетекут» в него из total_amount
        contract.advance_payment = _round(contract.total_amount)
    for order, kind in enumerate(_base_kinds(contract)):
        amount = _base_amount(contract, kind)
        paid_date = getattr(contract, PAID_DATE_FIELDS[kind])
        title = "Оплата по договору" if contract.project_type == "Шаблонный" else INDIVIDUAL_TITLES[kind]
        db.add(
            ContractClientPayment(
                contract_id=contract.id,
                kind=kind,
                direction="in",
                title=title,
                amount=amount,
                sort_order=order,
                status="paid" if paid_date else "planned",
                paid_date=paid_date or None,
                paid_amount=amount if paid_date else None,
                legacy=bool(paid_date),
            )
        )
    db.commit()


def sync_from_contract(db, contract):
    """После правки договора формой: неоплаченные плановые платежи берут суммы из договора."""
    if not _uses_plan(contract):
        return
    ensure_rows(db, contract)
    changed = False
    rows = _rows(db, contract.id)
    extras = sum(_round(r.amount) for r in rows if r.kind == "extra" and r.status != "cancelled")
    for row in rows:
        if row.kind not in BASE_KINDS or row.direction != "in":
            continue
        # Дата оплаты записана в договор старым способом (в обход блока «Оплаты») — отражаем как старую оплату без документа
        legacy_date = getattr(contract, PAID_DATE_FIELDS[row.kind])
        if row.status in OPEN_STATUSES and legacy_date:
            row.status, row.paid_date, row.paid_amount, row.legacy = "paid", legacy_date, row.amount, True
            changed = True
            continue
        if row.status == "paid" and row.legacy and not row.doc_id and not legacy_date:
            row.status, row.paid_date, row.paid_amount, row.legacy = "planned", None, None, False
            changed = True
        if row.status in OPEN_STATUSES:
            if contract.project_type == "Шаблонный":
                # Один платёж = общая сумма договора без доплат по доп. соглашениям
                amount = _round(_round(contract.total_amount) - extras) if contract.total_amount else _round(contract.advance_payment)
                contract.advance_payment = amount
                changed = True
            else:
                amount = _base_amount(contract, row.kind)
            if _round(row.amount) != amount:
                row.amount = amount
                changed = True
    if changed:
        db.commit()


def mirror_to_contract(db, contract):
    """Плановые платежи → старые поля договора (суммы и даты оплат). Возвращает True, если сменилась дата аванса."""
    rows = {r.kind: r for r in _rows(db, contract.id) if r.kind in BASE_KINDS and r.direction == "in"}
    advance_before = contract.advance_payment_paid_date
    for kind, row in rows.items():
        # Уменьшение стоимости обнуляет сумму строки; аннулирование при расторжении сумму сохраняет (для истории)
        setattr(contract, AMOUNT_FIELDS[kind], _round(row.amount))
        setattr(contract, PAID_DATE_FIELDS[kind], row.paid_date if row.status == "paid" else None)
    db.commit()
    if contract.advance_payment_paid_date != advance_before:
        try:
            from services.timeline_service import refresh_timeline_start_date

            refresh_timeline_start_date(db, contract.id)
        except Exception as e:
            logger.warning(f"Оплаты: не удалось обновить старт таймлайна договора {contract.id}: {e}")
        return True
    return False


def has_paid(db, contract_id):
    return (
        db.query(ContractClientPayment.id).filter(ContractClientPayment.contract_id == contract_id, ContractClientPayment.direction == "in", ContractClientPayment.status == "paid").first() is not None
    )


def check_contract_update(db, contract, update_data):
    """Сумму договора и суммы платежей нельзя править формой, если клиент уже платил: только через доп. соглашение."""
    if not _uses_plan(contract) or not has_paid(db, contract.id):
        return
    for field in LOCKED_CONTRACT_FIELDS:
        if field in update_data and abs(_round(update_data[field]) - _round(getattr(contract, field))) >= 0.01:
            raise HTTPException(
                409,
                "Клиент уже вносил оплату — стоимость и суммы платежей меняются только через блок «Оплаты» («Дополнительный платёж» или «Уменьшение стоимости»).",
            )


# ── Сводка ───────────────────────────────────────────────────────────────────


def summary(db, contract):
    rows = _rows(db, contract.id)
    paid_in = sum(_round(r.paid_amount) for r in rows if r.direction == "in" and r.status == "paid")
    refunded = sum(_round(r.paid_amount) for r in rows if r.direction == "out" and r.status == "paid")
    due = sum(_round(r.amount) for r in rows if r.direction == "in" and r.status in OPEN_STATUSES)
    to_refund = sum(_round(r.amount) for r in rows if r.direction == "out" and r.status in OPEN_STATUSES)
    return {
        "total": _round(contract.total_amount),
        "paid": _round(paid_in),
        "refunded": _round(refunded),
        "due": _round(due),
        "to_refund": _round(to_refund),
        "net_paid": _round(paid_in - refunded),
    }


def serialize_doc(doc, settings=None):
    if not doc:
        return None
    base = (settings or {}).get("public_base_url") or DEFAULT_SETTINGS["public_base_url"]
    return {
        "id": doc.id,
        "number": doc.number,
        "token": doc.token,
        "public_url": f"{base.rstrip('/')}/p/{doc.token}",
        "issued_at": doc.issued_at.isoformat() + "Z" if doc.issued_at else None,
        "annulled": doc.annulled_at is not None,
        "calc_sign": (doc.data or {}).get("calc_sign"),
        "amount": (doc.data or {}).get("amount"),
    }


def serialize_payment(db, row, settings=None, names=None):
    doc = db.query(ClientPaymentDoc).filter(ClientPaymentDoc.id == row.doc_id).first() if row.doc_id else None
    annulled = db.query(ClientPaymentDoc).filter(ClientPaymentDoc.payment_id == row.id, ClientPaymentDoc.annulled_at.isnot(None)).order_by(ClientPaymentDoc.id).all()
    return {
        "id": row.id,
        "kind": row.kind,
        "direction": row.direction,
        "title": row.title,
        "basis": row.basis,
        "amount": _round(row.amount),
        "status": row.status,
        "link_sent_at": row.link_sent_at.isoformat() + "Z" if row.link_sent_at else None,
        "paid_amount": row.paid_amount,
        "paid_date": row.paid_date,
        "paid_time": row.paid_time,
        "method": row.method,
        "paid_by_name": (names or {}).get(row.paid_by),
        "legacy": bool(row.legacy),
        "doc": serialize_doc(doc, settings),
        "annulled_docs": [serialize_doc(d, settings) for d in annulled],
    }


def contract_payments(db, contract):
    ensure_rows(db, contract)
    rows = _rows(db, contract.id)
    settings = get_settings(db)
    ids = {r.paid_by for r in rows if r.paid_by}
    names = dict(db.query(Employee.id, Employee.full_name).filter(Employee.id.in_(ids)).all()) if ids else {}
    return {
        "contract_id": contract.id,
        "uses_plan": _uses_plan(contract),
        "summary": summary(db, contract),
        "payments": [serialize_payment(db, r, settings, names) for r in rows],
        "sbp_configured": bool(settings.get("sbp_link")),
        "requisites_missing": requisites_missing(settings),
    }


# ── Помощники операций ────────────────────────────────────────────────────────


def get_contract_or_404(db, contract_id):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(404, "Договор не найден")
    return contract


def get_payment_or_404(db, payment_id):
    row = db.query(ContractClientPayment).filter(ContractClientPayment.id == payment_id).first()
    if not row:
        raise HTTPException(404, "Платёж не найден")
    return row


def _next_order(db, contract_id):
    value = db.query(func.max(ContractClientPayment.sort_order)).filter(ContractClientPayment.contract_id == contract_id).scalar()
    return (value or 0) + 1


def _log(db, employee, contract_id, action, details):
    try:
        from database import ActionHistory

        db.add(ActionHistory(user_id=employee.id, action_type=action, entity_type="contract", entity_id=contract_id, description=details))
    except Exception as e:
        logger.warning(f"Оплаты: история действий не записана ({e})")


def _client_name(db, contract):
    client = db.query(Client).filter(Client.id == contract.client_id).first() if contract.client_id else None
    if not client:
        return ""
    return client.organization_name or client.full_name or ""


def _fmt_money(value):
    return f"{_round(value):,.0f}".replace(",", " ") + " ₽"


def _fmt_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (TypeError, ValueError):
        return value or ""


# ── Сформировать оплату (СБП-ссылка) ─────────────────────────────────────────


def payment_link(db, row, employee):
    if row.direction != "in" or row.status not in OPEN_STATUSES:
        raise HTTPException(400, "Ссылку можно сформировать только для неоплаченного платежа")
    if _round(row.amount) <= 0:
        raise HTTPException(400, "У платежа не указана сумма")
    settings = get_settings(db)
    link = settings.get("sbp_link") or ""
    if not link:
        raise HTTPException(400, "СБП-ссылка не настроена: Админка → Оплаты (СБП)")
    contract = get_contract_or_404(db, row.contract_id)
    message = settings.get("message_template") or DEFAULT_SETTINGS["message_template"]
    replacements = {
        "{клиент}": _client_name(db, contract) or "",
        "{договор}": contract.contract_number or "",
        "{платёж}": row.title,
        "{сумма}": _fmt_money(row.amount),
        "{ссылка}": link,
    }
    for key, value in replacements.items():
        message = message.replace(key, value)
    message = message.replace("Здравствуйте, !", "Здравствуйте!")
    row.status = "link_sent"
    row.link_sent_at = datetime.utcnow()
    db.commit()
    from services.payment_doc_pdf import qr_svg

    return {"amount": _round(row.amount), "sbp_link": link, "message": message, "qr_svg": qr_svg(link)}


# ── Документ об оплате ────────────────────────────────────────────────────────


def _issue_doc(db, row, contract, employee, settings):
    missing = requisites_missing(settings)
    if missing:
        raise HTTPException(400, f"Заполните реквизиты для документа (Админка → Оплаты): {', '.join(missing)}")
    year = int((row.paid_date or datetime.utcnow().strftime("%Y"))[:4])
    cashier = director_cashier(db, settings)
    if not cashier:
        raise HTTPException(400, "Не задан руководитель для документа (Админка → Оплаты: «Расчёт осуществил»)")
    data = {
        "date_text": _fmt_date(row.paid_date),
        "time": row.paid_time or "",
        "place": settings.get("place_office") if row.method == "cash" and settings.get("place_office") else settings.get("place_remote"),
        "seller_name": f"Индивидуальный предприниматель {settings['seller_name']}" if not settings["seller_name"].upper().startswith("ИП") else settings["seller_name"],
        "seller_inn": settings["seller_inn"],
        "seller_ogrnip": settings.get("seller_ogrnip") or "",
        "tax_system": settings["tax_system"],
        "calc_sign": "Возврат прихода" if row.direction == "out" else "Приход",
        "client_name": _client_name(db, contract),
        "basis": f"Договор № {contract.contract_number}" + (f" от {_fmt_date(contract.contract_date)}" if contract.contract_date else "") + f" — {row.title}",
        "service": (f"Возврат денежных средств: {settings['service_name']}" if row.direction == "out" else settings["service_name"]) + f" по договору № {contract.contract_number}",
        "amount": _round(row.paid_amount),
        "method": row.method,
        "method_text": METHODS.get(row.method, row.method or ""),
        "cashier": cashier,
        "contract_number": contract.contract_number,
    }
    for _attempt in range(5):
        seq = (db.query(func.max(ClientPaymentDoc.seq)).filter(ClientPaymentDoc.year == year).scalar() or 0) + 1
        number = f"{year}-{seq:04d}"
        token = secrets.token_urlsafe(24)
        base = settings.get("public_base_url") or DEFAULT_SETTINGS["public_base_url"]
        doc = ClientPaymentDoc(
            number=number,
            year=year,
            seq=seq,
            token=token,
            payment_id=row.id,
            contract_id=contract.id,
            data={**data, "number": number, "public_url": f"{base.rstrip('/')}/p/{token}"},
            issued_by=employee.id,
        )
        try:
            # Точка сохранения: при занятом номере откатываем только документ, а не всю оплату
            with db.begin_nested():
                db.add(doc)
                db.flush()
        except IntegrityError:
            continue  # номер занят параллельной выдачей — берём следующий
        row.doc_id = doc.id
        return doc
    raise HTTPException(409, "Не удалось присвоить номер документу, повторите")


def doc_pdf_bytes(db, doc):
    from services.payment_doc_pdf import build_payment_doc_pdf, festival_logo_bytes

    return build_payment_doc_pdf(doc.data or {}, festival_logo_bytes(db), annulled=doc.annulled_at is not None)


def doc_filename(doc):
    kind = "Возврат" if (doc.data or {}).get("calc_sign") == "Возврат прихода" else "Оплата"
    contract = (doc.data or {}).get("contract_number") or ""
    return f"{kind}_№{doc.number}_договор_{contract}.pdf".replace("/", "-")


def upload_doc_to_disk(doc_id):
    """Фоном: копия PDF в папку договора на Яндекс.Диске (Документы/Оплаты). Ошибка не мешает выдаче документа."""
    from database import SessionLocal

    db = SessionLocal()
    try:
        doc = db.query(ClientPaymentDoc).filter(ClientPaymentDoc.id == doc_id).first()
        contract = db.query(Contract).filter(Contract.id == doc.contract_id).first() if doc else None
        if not doc or not contract or not contract.yandex_folder_path:
            return
        from yandex_disk_service import YandexDiskService

        path = f"{contract.yandex_folder_path}/Документы/Оплаты/{doc_filename(doc)}"
        YandexDiskService().upload_file_from_bytes(doc_pdf_bytes(db, doc), path)
        doc.yandex_path = path
        db.commit()
    except Exception as e:
        logger.warning(f"Документ об оплате {doc_id}: копия на ЯД не сохранена ({e})")
    finally:
        db.close()


# ── Провести оплату / возврат ─────────────────────────────────────────────────


def _validate_paid(data):
    amount = _round(data.get("amount"))
    if amount <= 0:
        raise HTTPException(400, "Укажите сумму")
    if data.get("method") not in METHODS:
        raise HTTPException(400, "Выберите способ оплаты")
    try:
        datetime.strptime(data.get("date") or "", "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Укажите дату")
    time_value = (data.get("time") or "").strip() or (datetime.utcnow() + MSK).strftime("%H:%M")
    try:
        datetime.strptime(time_value, "%H:%M")
    except ValueError:
        raise HTTPException(400, "Время в формате ЧЧ:ММ")
    return amount, time_value


def pay(db, row, data, employee):
    """Провести оплату клиента (direction=in) или возврат клиенту (direction=out) и выдать документ."""
    if row.status not in OPEN_STATUSES:
        raise HTTPException(400, "Платёж уже проведён или аннулирован")
    amount, time_value = _validate_paid(data)
    contract = get_contract_or_404(db, row.contract_id)
    settings = get_settings(db)
    if row.direction == "out" and amount - _round(row.amount) > 0.01:
        raise HTTPException(400, f"Сумма возврата больше суммы к возврату ({_fmt_money(row.amount)})")

    row.status = "paid"
    row.paid_amount = amount
    row.paid_date = data["date"]
    row.paid_time = time_value
    row.method = data["method"]
    row.paid_by = employee.id
    row.paid_at = datetime.utcnow()
    row.legacy = False
    doc = _issue_doc(db, row, contract, employee, settings)

    rest = _round(row.amount) - amount
    if rest > 0.01:
        # Внесено меньше плана — остаток отдельной строкой (или остаток возврата)
        db.add(
            ContractClientPayment(
                contract_id=contract.id,
                kind="rest" if row.direction == "in" else "refund",
                direction=row.direction,
                title=f"Остаток: {row.title}",
                basis=f"Плановая сумма {_fmt_money(row.amount)}, внесено {_fmt_money(amount)}",
                amount=_round(rest),
                sort_order=row.sort_order,
                created_by=employee.id,
            )
        )
        row.amount = amount if row.kind not in BASE_KINDS else row.amount
    sign = "Возврат" if row.direction == "out" else "Оплата"
    _log(db, employee, contract.id, "client_payment", f"{sign} «{row.title}»: {_fmt_money(amount)}, {METHODS[row.method]}, документ № {doc.number}")
    db.commit()
    if row.kind in BASE_KINDS:
        mirror_to_contract(db, contract)
    return doc


def issue_doc_for_legacy(db, row, data, employee):
    """Выписать документ для оплаты, отмеченной до появления документов (данные уточняются при выдаче)."""
    if row.status != "paid" or row.doc_id:
        raise HTTPException(400, "Документ уже выдан или платёж не оплачен")
    amount, time_value = _validate_paid({**data, "amount": data.get("amount") or row.paid_amount or row.amount, "date": data.get("date") or row.paid_date})
    row.paid_amount = amount
    row.paid_date = data.get("date") or row.paid_date
    row.paid_time = time_value
    row.method = data["method"]
    row.paid_by = employee.id
    row.legacy = False
    contract = get_contract_or_404(db, row.contract_id)
    doc = _issue_doc(db, row, contract, employee, get_settings(db))
    _log(db, employee, contract.id, "client_payment", f"Выписан документ № {doc.number} к оплате «{row.title}»")
    db.commit()
    if row.kind in BASE_KINDS:
        mirror_to_contract(db, contract)
    return doc


def cancel_paid(db, row, employee):
    """Снять проведённую оплату/возврат: документ аннулируется (номер не переиспользуется)."""
    if row.status != "paid":
        raise HTTPException(400, "Платёж не проведён")
    contract = get_contract_or_404(db, row.contract_id)
    if row.doc_id:
        doc = db.query(ClientPaymentDoc).filter(ClientPaymentDoc.id == row.doc_id).first()
        if doc:
            doc.annulled_at = datetime.utcnow()
            doc.annulled_by = employee.id
    # Автоматически созданный остаток к этому платежу убираем, если он ещё не оплачен
    rest_title = f"Остаток: {row.title}"
    for rest in (
        db.query(ContractClientPayment).filter(ContractClientPayment.contract_id == contract.id, ContractClientPayment.title == rest_title, ContractClientPayment.status.in_(OPEN_STATUSES)).all()
    ):
        if row.kind not in BASE_KINDS:
            row.amount = _round(row.amount) + _round(rest.amount)
        db.delete(rest)
    _log(db, employee, contract.id, "client_payment_cancel", f"Снята оплата «{row.title}» ({_fmt_money(row.paid_amount)})")
    row.status = "planned"
    row.doc_id = None
    row.paid_amount = None
    row.paid_date = None
    row.paid_time = None
    row.method = None
    row.paid_by = None
    row.paid_at = None
    row.legacy = False
    db.commit()
    if row.kind in BASE_KINDS:
        mirror_to_contract(db, contract)


def delete_open(db, row, employee):
    """Удалить неоплаченный дополнительный платёж / возврат / долг (с откатом стоимости договора для доп. платежа)."""
    if row.kind in BASE_KINDS:
        raise HTTPException(400, "Плановые платежи договора не удаляются — используйте «Уменьшение стоимости»")
    if row.status not in OPEN_STATUSES:
        raise HTTPException(400, "Проведённый платёж сначала нужно снять")
    contract = get_contract_or_404(db, row.contract_id)
    if row.kind == "extra":
        contract.total_amount = _round(contract.total_amount) - _round(row.amount)
    _log(db, employee, contract.id, "client_payment_delete", f"Удалён платёж «{row.title}» ({_fmt_money(row.amount)})")
    db.delete(row)
    db.commit()


# ── Доп. соглашение: увеличение / уменьшение стоимости ───────────────────────


def _apply_area(db, contract, new_area):
    """Новая площадь по доп. соглашению → договор + пересчёт оплат исполнителям (как при правке площади)."""
    if new_area in (None, "") or abs(float(new_area) - float(contract.area or 0)) < 0.001:
        return None
    if float(new_area) <= 0:
        raise HTTPException(400, "Площадь должна быть больше нуля")
    old = contract.area
    contract.area = float(new_area)
    db.commit()
    from routers.payments_router import _recalculate_payments_for_contract

    recalculated = _recalculate_payments_for_contract(db, contract.id)
    return {"old": old, "new": contract.area, "recalculated": recalculated}


def _area_text(area_change):
    if not area_change:
        return ""
    return f"; площадь {area_change['old'] or 0:g} → {area_change['new']:g} м², пересчитано оплат исполнителям: {area_change['recalculated']}"


def add_extra(db, contract, data, employee):
    amount = _round(data.get("amount"))
    if amount <= 0:
        raise HTTPException(400, "Укажите сумму доплаты")
    basis = (data.get("basis") or "").strip()
    if not basis:
        raise HTTPException(400, "Укажите основание (номер и дата доп. соглашения)")
    ensure_rows(db, contract)
    reason = "увеличение площади" if data.get("reason") == "area" else "дополнительные услуги"
    area_change = _apply_area(db, contract, data.get("new_area")) if data.get("reason") == "area" else None
    contract.total_amount = _round(contract.total_amount) + amount
    row = ContractClientPayment(
        contract_id=contract.id,
        kind="extra",
        direction="in",
        title=f"Доплата по доп. соглашению ({reason})",
        basis=basis,
        amount=amount,
        sort_order=_next_order(db, contract.id),
        created_by=employee.id,
    )
    db.add(row)
    _log(db, employee, contract.id, "client_payment_extra", f"Доп. соглашение ({reason}): +{_fmt_money(amount)}, {basis}{_area_text(area_change)}")
    db.commit()
    return {"payment_id": row.id, "area_change": area_change}


def decrease(db, contract, data, employee):
    """Уменьшение стоимости: сначала уменьшаем неоплаченные платежи (с последнего), остаток — к возврату клиенту."""
    amount = _round(data.get("amount"))
    if amount <= 0:
        raise HTTPException(400, "Укажите сумму уменьшения")
    if amount - _round(contract.total_amount) > 0.01:
        raise HTTPException(400, "Уменьшение больше стоимости договора")
    basis = (data.get("basis") or "").strip()
    if not basis:
        raise HTTPException(400, "Укажите основание (номер и дата доп. соглашения)")
    ensure_rows(db, contract)
    area_change = _apply_area(db, contract, data.get("new_area"))
    left = amount
    open_rows = [r for r in _rows(db, contract.id) if r.direction == "in" and r.status in OPEN_STATUSES and r.kind != "termination_debt"]
    for row in sorted(open_rows, key=lambda r: (r.sort_order, r.id), reverse=True):
        if left <= 0.01:
            break
        cut = min(left, _round(row.amount))
        row.amount = _round(row.amount) - cut
        if row.amount <= 0.01:
            row.amount = 0
            row.status = "cancelled"
        left = _round(left - cut)
    refund = None
    if left > 0.01:
        refund = ContractClientPayment(
            contract_id=contract.id,
            kind="refund",
            direction="out",
            title="Возврат: уменьшение стоимости по доп. соглашению",
            basis=basis,
            amount=left,
            sort_order=_next_order(db, contract.id),
            created_by=employee.id,
        )
        db.add(refund)
    contract.total_amount = _round(contract.total_amount) - amount
    tail = f", к возврату клиенту {_fmt_money(left)}" if refund else ""
    _log(db, employee, contract.id, "client_payment_decrease", f"Доп. соглашение: −{_fmt_money(amount)}, {basis}{tail}{_area_text(area_change)}")
    db.commit()
    mirror_to_contract(db, contract)
    return {"refund": _round(left) if refund else 0, "area_change": area_change}


# ── Расторжение: расчёт с клиентом ────────────────────────────────────────────


def terminate(db, contract, data, employee):
    """Удерживаем стоимость выполненных работ; остальное — к возврату, либо долг клиента, если оплачено меньше."""
    retained = _round(data.get("retained"))
    if retained < 0:
        raise HTTPException(400, "Стоимость выполненных работ не может быть отрицательной")
    reason = (data.get("reason") or "").strip()
    if not reason:
        raise HTTPException(400, "Укажите основание расторжения")
    ensure_rows(db, contract)
    rows = _rows(db, contract.id)
    if any(r.kind in ("termination_debt",) or (r.kind == "refund" and "расторжени" in (r.title or "")) for r in rows if r.status in OPEN_STATUSES):
        raise HTTPException(400, "Расчёт при расторжении уже сделан — удалите его строку, чтобы пересчитать")
    for row in rows:
        if row.direction == "in" and row.status in OPEN_STATUSES:
            row.status = "cancelled"
    state = summary(db, contract)
    pending_refund = state["to_refund"]
    balance = _round(state["net_paid"] - pending_refund - retained)
    basis = f"{reason}. Стоимость выполненных работ: {_fmt_money(retained)}, оплачено клиентом: {_fmt_money(state['net_paid'])}"
    order = _next_order(db, contract.id)
    if balance > 0.01:
        db.add(
            ContractClientPayment(
                contract_id=contract.id, kind="refund", direction="out", title="Возврат при расторжении договора", basis=basis, amount=balance, sort_order=order, created_by=employee.id
            )
        )
    elif balance < -0.01:
        db.add(
            ContractClientPayment(
                contract_id=contract.id, kind="termination_debt", direction="in", title="Доплата при расторжении договора", basis=basis, amount=-balance, sort_order=order, created_by=employee.id
            )
        )
    if not contract.termination_reason:
        contract.termination_reason = reason
    _log(
        db,
        employee,
        contract.id,
        "client_payment_terminate",
        f"Расчёт при расторжении: {basis}; итог {'к возврату ' + _fmt_money(balance) if balance > 0.01 else ('долг клиента ' + _fmt_money(-balance) if balance < -0.01 else 'без расчётов')}",
    )
    db.commit()
    # Старые поля договора не трогаем: плановые суммы остаются для истории, оплаченные даты не менялись
    return {"refund": balance if balance > 0.01 else 0, "debt": -balance if balance < -0.01 else 0}
