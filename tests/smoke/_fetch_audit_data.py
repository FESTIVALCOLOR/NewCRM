"""Скрипт для скачивания всех данных с CRM сервера для аудита."""
import requests
import json
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = "https://crm.festivalcolor.ru"

# Рабочие креденшлы (admin/admin123 -- seed на сервере)
AUTH_ATTEMPTS = [
    {"username": "admin", "password": "admin123"},
]


def try_login(username, password):
    """Попытка авторизации."""
    r = requests.post(
        f"{BASE}/api/auth/login",
        data={"username": username, "password": password},
        verify=False,
        timeout=15,
    )
    return r


def main():
    token = None

    for creds in AUTH_ATTEMPTS:
        print(f"Попытка: {creds['username']} / {'*' * len(creds['password'])}...")
        r = try_login(creds["username"], creds["password"])
        print(f"  -> {r.status_code}: {r.text[:150]}")
        if r.status_code == 200:
            data = r.json()
            token = data.get("access_token") or data.get("token")
            print(f"  -> Успех! Token: {token[:30]}...")
            break

    if not token:
        print("\nВСЕ попытки авторизации провалились!")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Endpoint-ы для скачивания
    endpoints = {
        "clients": "/api/clients/",
        "contracts": "/api/contracts/",
        "payments": "/api/payments/",
        "crm_cards_individual": "/api/crm/cards?project_type=Индивидуальный",
        "crm_cards_typical": "/api/crm/cards?project_type=Типовой",
        "crm_archive_individual": "/api/crm/cards?archived=True&project_type=Индивидуальный",
        "crm_archive_typical": "/api/crm/cards?archived=True&project_type=Типовой",
        "supervision_active": "/api/supervision/cards",
        "supervision_archive": "/api/supervision/cards?archived=true",
        "rates": "/api/rates/",
        "employees": "/api/employees/",
        "dashboard": "/api/v1/dashboard/summary",
        "dashboard_stats": "/api/statistics/dashboard",
        "agents": "/api/agents/",
        "cities": "/api/cities/",
    }

    result = {}
    print("\n" + "=" * 65)
    print(f"{'Endpoint':<35} {'Статус':>7} {'Записей':>10}")
    print("=" * 65)

    for key, path in endpoints.items():
        try:
            resp = requests.get(
                f"{BASE}{path}",
                headers=headers,
                verify=False,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            result[key] = data

            # Подсчёт записей
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict):
                for k in ("items", "cards", "data"):
                    if k in data and isinstance(data[k], list):
                        count = len(data[k])
                        break
                else:
                    count = "dict"
            else:
                count = "?"

            print(f"{key:<35} {resp.status_code:>7} {str(count):>10}")
        except Exception as e:
            sc = ""
            if hasattr(e, "response") and e.response is not None:
                sc = e.response.status_code
                # Сохраним тело ответа для диагностики
                try:
                    result[key] = {"error": str(e), "status_code": sc, "body": e.response.text[:500]}
                except Exception:
                    result[key] = {"error": str(e), "status_code": sc}
            else:
                result[key] = {"error": str(e)}
            print(f"{key:<35} {'ERR':>7} {str(sc) + ' ' + str(e)[:50]}")

    # Сохранение
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_audit_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    size = os.path.getsize(out_path)
    print(f"\n{'=' * 65}")
    print(f"Сохранено: {out_path}")
    print(f"Размер: {size:,} байт")


if __name__ == "__main__":
    main()
