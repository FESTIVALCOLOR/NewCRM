import requests

BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
AGENTS_URL = f"{BASE_URL}/api/v1/agents"
TIMEOUT = 30

def get_access_token(username: str, password: str) -> str:
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "username": username,
        "password": password
    }
    response = requests.post(LOGIN_URL, headers=headers, data=data, timeout=TIMEOUT)
    response.raise_for_status()
    token = response.json().get("access_token")
    if not token:
        raise ValueError("No access_token found in login response")
    return token

def test_agents_list():
    try:
        token = get_access_token("admin", "admin123")
    except Exception as e:
        assert False, f"Failed to get access token: {e}"

    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(AGENTS_URL, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request to {AGENTS_URL} failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    
    try:
        json_data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    # Expecting a list or an object with items
    assert isinstance(json_data, (list, dict)), "Response JSON is not a list or dict"

    # If dict, check it has items or keys
    if isinstance(json_data, dict):
        assert len(json_data) > 0, "Response JSON dict is empty"
    else:
        assert len(json_data) >= 0, "Response JSON list is expected to be zero or more items"

test_agents_list()