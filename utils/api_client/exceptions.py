"""
Классы исключений API клиента
"""


# =========================
# КЛАССЫ ИСКЛЮЧЕНИЙ API
# =========================

class APIError(Exception):
    """Базовая ошибка API"""
    pass


class APITimeoutError(APIError):
    """Ошибка таймаута запроса"""
    pass


class APIConnectionError(APIError):
    """Ошибка соединения с сервером"""
    pass


class APIAuthError(APIError):
    """Ошибка аутентификации"""
    pass


class APIResponseError(APIError):
    """Ошибка ответа сервера"""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code
