import requests

# Check Bitget balance
bitget_balance = requests.get('http://localhost:8000/api/v1/bitget/balance').json()
print('Bitget balance response:')
print(bitget_balance) 