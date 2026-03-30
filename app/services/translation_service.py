import requests

from app.core.config import settings

_PAPAGO_URL = "https://openapi.naver.com/v1/papago/n2mt"


def translate_ja_to_en(text: str) -> str:
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    data = {"source": "ja", "target": "en", "text": text}
    response = requests.post(_PAPAGO_URL, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["message"]["result"]["translatedText"]
