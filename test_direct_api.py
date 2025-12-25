import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Login
login_response = requests.post(
    'https://147.45.154.193/api/auth/login',
    data={'username': 'admin', 'password': 'admin123'},
    verify=False
)

print(f'Login status: {login_response.status_code}')
login_data = login_response.json()
print(f'Token: {login_data["access_token"][:60]}...')

# Try to create employee
token = login_data["access_token"]
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {token}'
}

employee_data = {
    'full_name': 'Test User API',
    'phone': '+7 999 888-77-66',
    'email': 'testapi@test.com',
    'position': 'Test Position',
    'department': 'Test Dept',
    'login': 'testapi999',
    'password': 'testpass999'
}

create_response = requests.post(
    'https://147.45.154.193/api/employees',
    headers=headers,
    json=employee_data,
    verify=False
)

print(f'\nCreate employee status: {create_response.status_code}')
print(f'Response: {create_response.text}')
