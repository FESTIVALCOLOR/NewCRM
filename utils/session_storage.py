"""
Хранение сессии для автологина ("Запомнить меня").

Сохраняет refresh_token + метаданные в зашифрованный файл.
При следующем запуске — пробует обновить access_token через /auth/refresh.
"""
import json
import os
import time
import base64
import hashlib
import platform
from typing import Optional, Dict

# Файл сессии рядом с БД
_SESSION_DIR = os.path.join(os.path.expanduser('~'), '.interior_studio')
_SESSION_FILE = os.path.join(_SESSION_DIR, '.session')

# Максимальный возраст сохранённой сессии (дни)
SESSION_MAX_DAYS = 30


def _get_machine_key() -> bytes:
    """Генерация ключа шифрования на основе идентификатора машины."""
    # Используем имя компьютера + имя пользователя как seed
    machine_id = f"{platform.node()}:{os.getlogin()}:interior_studio_crm"
    return hashlib.sha256(machine_id.encode()).digest()


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    """Простое XOR-шифрование (достаточно для локального хранения)."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def save_session(refresh_token: str, employee_id: int, full_name: str = '',
                 login: str = '') -> bool:
    """Сохранить сессию для автологина."""
    try:
        os.makedirs(_SESSION_DIR, exist_ok=True)
        session_data = {
            'refresh_token': refresh_token,
            'employee_id': employee_id,
            'full_name': full_name,
            'login': login,
            'saved_at': time.time(),
        }
        raw = json.dumps(session_data).encode('utf-8')
        encrypted = _xor_encrypt(raw, _get_machine_key())
        encoded = base64.b64encode(encrypted)
        with open(_SESSION_FILE, 'wb') as f:
            f.write(encoded)
        return True
    except Exception as e:
        print(f"[SessionStorage] Ошибка сохранения сессии: {e}")
        return False


def load_session() -> Optional[Dict]:
    """Загрузить сохранённую сессию. Возвращает None если нет или истекла."""
    try:
        if not os.path.exists(_SESSION_FILE):
            return None
        with open(_SESSION_FILE, 'rb') as f:
            encoded = f.read()
        encrypted = base64.b64decode(encoded)
        raw = _xor_encrypt(encrypted, _get_machine_key())
        session_data = json.loads(raw.decode('utf-8'))

        # Проверяем возраст сессии
        saved_at = session_data.get('saved_at', 0)
        age_days = (time.time() - saved_at) / 86400
        if age_days > SESSION_MAX_DAYS:
            clear_session()
            return None

        return session_data
    except Exception as e:
        print(f"[SessionStorage] Ошибка загрузки сессии: {e}")
        clear_session()
        return None


def clear_session():
    """Удалить сохранённую сессию (логаут / истечение)."""
    try:
        if os.path.exists(_SESSION_FILE):
            os.remove(_SESSION_FILE)
    except Exception as e:
        print(f"[SessionStorage] Ошибка удаления сессии: {e}")


def has_saved_session() -> bool:
    """Проверить наличие сохранённой сессии без загрузки."""
    return os.path.exists(_SESSION_FILE)
