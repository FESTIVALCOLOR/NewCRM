from utils.api_client import APIClient

client = APIClient('https://147.45.154.193')
result = client.login('admin', 'admin123')
print(f'Token: {result["access_token"][:50]}...')
print(f'Headers: {client.headers}')

# Попробуем создать сотрудника
test_employee = {
    'full_name': 'Test User',
    'phone': '+7 999 999-99-99',
    'email': 'test@test.com',
    'position': 'Test',
    'department': 'Test',
    'login': 'testuser123',
    'password': 'testpass123'
}

try:
    result = client.create_employee(test_employee)
    print('Employee created:', result['id'])
except Exception as e:
    print(f'Error: {e}')
