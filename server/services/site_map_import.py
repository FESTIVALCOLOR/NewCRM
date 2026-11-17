"""
Карта объектов сайта: разбор файла Excel со столбцами «Город» и «Адрес».

Модуль без обращений к БД и сети — его логика проверяется тестами без сервера.
"""

from dataclasses import dataclass, field
import io

from services.site_map_geo import address_key, normalize_city

MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_ROWS = 3000
# Заголовок ищется в первых строках: над таблицей может быть название или пустая строка
HEADER_SEARCH_ROWS = 15
MAX_CITY_LENGTH = 100
MAX_ADDRESS_LENGTH = 500


class ImportFileError(ValueError):
    """Файл нельзя разобрать; текст ошибки показывается человеку в панели управления."""


@dataclass
class ParsedObjects:
    rows: list[tuple[str, str]] = field(default_factory=list)  # (город, адрес) без повторов внутри файла
    skipped: list[str] = field(default_factory=list)  # пояснения по пропущенным строкам
    duplicates: int = 0  # повторы внутри самого файла


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).split())


def _find_columns(rows: list[tuple]) -> tuple[int, int, int]:
    """Номер строки заголовка и номера столбцов города и адреса."""
    for index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        titles = [_cell_text(cell).lower() for cell in row]
        city = next((i for i, title in enumerate(titles) if title.startswith("город")), None)
        address = next((i for i, title in enumerate(titles) if title.startswith("адрес")), None)
        if city is not None and address is not None:
            return index, city, address
    raise ImportFileError("В файле не найдены столбцы «Город» и «Адрес». Назовите так два столбца в первой строке таблицы.")


def parse_objects_xlsx(content: bytes) -> ParsedObjects:
    """Читает первый лист файла .xlsx и возвращает пары «город, адрес»."""
    if len(content) > MAX_FILE_SIZE:
        raise ImportFileError("Файл слишком большой (максимум 5 МБ)")
    try:
        from openpyxl import load_workbook

        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        sheet = workbook.worksheets[0]
        rows = list(sheet.iter_rows(max_row=MAX_ROWS + HEADER_SEARCH_ROWS, values_only=True))
        workbook.close()
    except Exception as exc:
        raise ImportFileError("Не удалось прочитать файл. Нужен файл Excel в формате .xlsx (старый формат .xls сохраните как .xlsx).") from exc

    header_row, city_col, address_col = _find_columns(rows)
    result = ParsedObjects()
    seen: set[str] = set()
    for number, row in enumerate(rows[header_row + 1 :], start=header_row + 2):
        city = normalize_city(_cell_text(row[city_col]) if city_col < len(row) else "")
        address = _cell_text(row[address_col]) if address_col < len(row) else ""
        if not city and not address:
            continue
        if not address:
            result.skipped.append(f"строка {number}: не указан адрес")
            continue
        if not city:
            result.skipped.append(f"строка {number}: не указан город")
            continue
        if len(city) > MAX_CITY_LENGTH or len(address) > MAX_ADDRESS_LENGTH:
            result.skipped.append(f"строка {number}: слишком длинное значение")
            continue
        key = address_key(address, city)
        if key in seen:
            result.duplicates += 1
            continue
        seen.add(key)
        result.rows.append((city, address))
    return result


def build_template_xlsx() -> bytes:
    """Образец файла для загрузки: заголовки и две строки-примера."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Объекты"
    sheet.append(["Город", "Адрес"])
    sheet.append(["Москва", "ул. Тверская, 12"])
    sheet.append(["Санкт-Петербург", "Каменноостровский проспект, 26"])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
    sheet.column_dimensions["A"].width = 24
    sheet.column_dimensions["B"].width = 60
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
