from urllib.parse import quote, urlparse, parse_qs
import requests as rq
from credentials import API_KEY, SECRET_KEY, RURL


def generate_auth_url():
    auth_url = f'https://api-v2.upstox.com/login/authorization/dialog?response_type=code&client_id={API_KEY}&redirect_uri={quote(RURL, safe="")}'
    return auth_url


def process_auth_code(auth_url):
    parsed_url = urlparse(auth_url)
    auth_code = parse_qs(parsed_url.query).get('code', [None])[0]

    if auth_code:
        retrieve_access_token(auth_code)
    else:
        print("Authentication code not found in URL.")


def retrieve_access_token(auth_code):
    url = 'https://api-v2.upstox.com/login/authorization/token'
    headers = {
        'accept': 'application/json',
        'Api-Version': '2.0',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {
        'code': auth_code,
        'client_id': API_KEY,
        'client_secret': SECRET_KEY,
        'redirect_uri': RURL,
        'grant_type': 'authorization_code'
    }
    response = rq.post(url, headers=headers, data=data)
    if response.status_code == 200:
        json_response = response.json()
        access_token = json_response['access_token']
        print("Access token fetched successfully.")
        open_value = get_open_value(access_token)
        if open_value is not None:
            print(f"Bank Nifty Current Price: {open_value}")
        save_access_token(access_token)
    else:
        print("Failed to fetch access token.")


def get_open_value(access_token):
    url = "https://api.upstox.com/v2/market-quote/quotes"
    headers = {
        'accept': 'application/json',
        'Api-Version': '2.0',
        'Authorization': f'Bearer {access_token}'
    }
    payload = {'symbol': "NSE_INDEX|Nifty Bank"}
    response = rq.get(url, headers=headers, params=payload)
    if response.status_code == 200:
        response_data = response.json()
        open_value = response_data['data']['NSE_INDEX:Nifty Bank']['ohlc']['open']
        return open_value
    else:
        return None

def save_access_token(access_token):
    with open("access_token.txt", "w") as file:
        file.write(access_token)


if __name__ == "__main__":
    auth_url = generate_auth_url()
    print("Generated authentication URL:", auth_url)
    auth_code = input("Paste the authentication URL obtained after manual login: ")
    process_auth_code(auth_code)
