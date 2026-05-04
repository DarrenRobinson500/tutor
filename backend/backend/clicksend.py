import requests
from django.conf import settings

CLICKSEND_BASE = "https://rest.clicksend.com/v3/sms/send"

def clicksend_send_sms(to_number: str, body: str) -> str:

    payload = {
        "messages": [
            {
                "source": "python",
                "body": body,
                "to": to_number,
                "from": settings.CLICKSEND_FROM_NUMBER,  # shared number
            }
        ]
    }

    resp = requests.post(
        CLICKSEND_BASE,
        json=payload,
        auth=(settings.CLICKSEND_USERNAME, settings.CLICKSEND_API_KEY)
    )

    data = resp.json()

    if resp.status_code != 200 or data.get("http_code") != 200:
        raise Exception(f"ClickSend error: {data}")

    # ClickSend returns an array of messages; each has a message_id
    return data["data"]["messages"][0]["message_id"]