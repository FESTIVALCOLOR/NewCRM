from utils.api_client import APIClient
import jwt

client = APIClient('https://147.45.154.193')
result = client.login('admin', 'admin123')
token = result['access_token']

print(f'Token: {token[:80]}...')

# Декодируем токен (без проверки подписи)
decoded = jwt.decode(token, options={"verify_signature": False})
print(f'Decoded: {decoded}')

# Проверим заголовки
print(f'Headers after login: {client.headers}')
