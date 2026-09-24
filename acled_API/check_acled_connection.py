from pathlib import Path
import os

import requests
from dotenv import load_dotenv


ENV_FILE = Path(__file__).with_name(".env")
TOKEN_URL = "https://acleddata.com/oauth/token"
API_URL = "https://acleddata.com/api/acled/read"


def load_credentials():
    load_dotenv(ENV_FILE)

    username = os.getenv("ACLED_USERNAME")
    password = os.getenv("ACLED_PASSWORD")

    if not username or not password:
        raise RuntimeError(
            "ACLED_USERNAME oder ACLED_PASSWORD fehlt in der .env-Datei."
        )

    return username, password


def get_access_token(username, password):
    response = requests.post(
        TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "username": username,
            "password": password,
            "grant_type": "password",
            "client_id": "acled",
            "scope": "authenticated",
        },
        timeout=30,
    )

    response.raise_for_status()

    token = response.json().get("access_token")

    if not token:
        raise RuntimeError("ACLED hat kein Access Token zurückgegeben.")

    return token


def check_connection(token):
    response = requests.get(
        API_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={
            "_format": "json",
            "country": "Iran|Israel",
            "event_date": "2025-01-01|2025-08-18",
            "event_date_where": "BETWEEN",
            "sub_event_type": (
                "Air/drone strike|"
                "Shelling/artillery/missile attack"
            ),
            "limit": 3,
            "with_total": "true",
            "fields": (
                "event_id_cnty|event_date|country|"
                "event_type|sub_event_type|fatalities"
            ),
        },

        timeout=30,
    )

    response.raise_for_status()
    return response.json()


def main():
    username, password = load_credentials()
    token = get_access_token(username, password)
    result = check_connection(token)

    events = result.get("data", [])
    total_count = result.get(
        "total_count",
        "not provided",
    )

    print("OAuth authentication successful.")
    print(
        f"Events returned on this page: "
        f"{len(events)}"
    )
    print(
        f"Total matching events: "
        f"{total_count}"
    )

    for event in events:
        print(
            event.get("event_date"),
            event.get("country"),
            event.get("event_type"),
            event.get("fatalities"),
        )

if __name__ == "__main__":
    main()