import requests

BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/auth/login"
AGENTS_URL = f"{BASE_URL}/api/v1/agents"
TIMEOUT = 30


def test_agents_patch_color():
    # Authenticate and get Bearer token
    login_data = {"username": "admin", "password": "admin123"}
    try:
        login_resp = requests.post(LOGIN_URL, data=login_data, timeout=TIMEOUT)
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token")
        assert token, "No access_token in login response"
    except Exception as e:
        raise AssertionError(f"Login request error: {e}")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # Get agents
        resp_agents = requests.get(AGENTS_URL, headers=headers, timeout=TIMEOUT)
        assert resp_agents.status_code == 200, f"GET /api/v1/agents failed: {resp_agents.text}"

        agents = resp_agents.json()
        # Filter agents with position="Агент"
        agents_list = [agent for agent in agents if agent.get("position") == "Агент"]

        if not agents_list:
            print("No agents with position 'Агент' found; skipping PATCH test.")
            return

        # Pick the first agent's name
        agent_name = agents_list[0].get("name") or agents_list[0].get("full_name") or None
        if not agent_name:
            # As fallback, check keys for probable name key
            for key in ["name", "full_name"]:
                if key in agents_list[0]:
                    agent_name = agents_list[0][key]
                    break
        assert agent_name, "Agent name not found in agent data"

        patch_url = f"{AGENTS_URL}/{agent_name}/color"
        patch_payload = {"color": "#FF5733"}

        patch_resp = requests.patch(patch_url, headers={**headers, "Content-Type": "application/json"},
                                    json=patch_payload,
                                    timeout=TIMEOUT)

        assert patch_resp.status_code == 200, f"PATCH /api/v1/agents/{agent_name}/color failed: {patch_resp.text}"
        patch_json = patch_resp.json()
        # Verify color is updated in response, if present
        if "color" in patch_json:
            assert patch_json["color"] == patch_payload["color"], "Color value in response does not match payload"
        else:
            # If no color field, just verify response is non-empty or has expected fields (no specific schema given)
            assert patch_json, "Empty response to PATCH agent color"
    except Exception as e:
        raise AssertionError(f"Test failed: {e}")


test_agents_patch_color()