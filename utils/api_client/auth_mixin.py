from typing import Optional, List, Dict, Any


class AuthMixin:

    def login(self, username: str, password: str) -> Dict[str, Any]:
        """
        Вход в систему

        Args:
            username: Логин
            password: Пароль

        Returns:
            dict с токеном и информацией о пользователе

        Raises:
            APIAuthError: При ошибке аутентификации
            APIConnectionError: При ошибке соединения
        """
        response = self._request(
            'POST',
            f"{self.base_url}/api/v1/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        data = self._handle_response(response)
        # Сохраняем оба токена
        self.set_token(data["access_token"], data.get("refresh_token"))
        self.employee_id = data["employee_id"]
        return data

    def refresh_access_token(self) -> bool:
        """
        Обновить access_token с помощью refresh_token

        Returns:
            True если токен успешно обновлен, False если нужен повторный логин
        """
        if not self.refresh_token or self._is_refreshing:
            return False

        self._is_refreshing = True
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token},
                mark_offline=False  # Не помечаем offline при ошибке refresh
            )

            if response.status_code == 200:
                data = response.json()
                # Сохраняем новый refresh_token если сервер его вернул (ротация токенов)
                new_refresh = data.get("refresh_token", self.refresh_token)
                self.set_token(data["access_token"], new_refresh)
                self.employee_id = data.get("employee_id", self.employee_id)
                return True
            else:
                return False
        except Exception:
            return False
        finally:
            self._is_refreshing = False

    def logout(self) -> bool:
        """
        Выход из системы

        Returns:
            True если успешно
        """
        try:
            response = self._request(
                'POST',
                f"{self.base_url}/api/v1/auth/logout",
                retry=False  # Не повторять при выходе
            )
            return response.status_code == 200
        except Exception as e:
            print(f"[API] Ошибка выхода: {e}")
            return False
        finally:
            self.clear_token()

    def get_current_user(self) -> Dict[str, Any]:
        """
        Получить информацию о текущем пользователе

        Returns:
            dict с данными пользователя
        """
        response = self._request('GET', f"{self.base_url}/api/v1/auth/me")
        return self._handle_response(response)
