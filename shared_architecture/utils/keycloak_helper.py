import requests
import logging

def get_access_token(auth_url, client_id, client_secret, username, password):
    try:
        data = {
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password
        }
        response = requests.post(auth_url, data=data)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        logging.error(f"Error getting Keycloak token: {e}")
        raise

def refresh_access_token(refresh_url, client_id, client_secret, refresh_token):
    try:
        data = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token
        }
        response = requests.post(refresh_url, data=data)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        logging.error(f"Error refreshing Keycloak token: {e}")
        raise
