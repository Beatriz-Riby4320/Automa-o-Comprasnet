import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
TOKEN = os.getenv("TRELLO_TOKEN")
LIST_ID = os.getenv("LIST_ID")

LABELS_MAP = {
    "COMPRASNET": os.getenv("LABEL_COMPRASNET"),
    "DISPENSA": os.getenv("LABEL_DE"),
    "PREGÃO": os.getenv("LABEL_PE"),
}

def _to_trello_utc(dt):
    if isinstance(dt, datetime) and dt.tzinfo is not None:
        utc = dt.astimezone(timezone.utc)
        return utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return None

def criar_cartao_trello(titulo, descricao, data_abertura, link_portal, badges=None):
    labels_ids = []
    if badges:
        for badge in badges:
            badge_upper = badge.strip().upper()
            if badge_upper in LABELS_MAP and LABELS_MAP[badge_upper]:
                labels_ids.append(LABELS_MAP[badge_upper])

    params = {
        "key": API_KEY,
        "token": TOKEN,
        "idList": LIST_ID,
        "name": titulo,
        "desc": f"{descricao}\n\nPortal: {link_portal}",
        "idLabels": ",".join(labels_ids) if labels_ids else None,
        "due": _to_trello_utc(data_abertura),
        "dueReminder": 1440
    }

    params = {k: v for k, v in params.items() if v is not None}

    print("Enviando para Trello:", params)

    url = "https://api.trello.com/1/cards"
    res = requests.post(url, data=params)

    print("Resposta Trello:", res.status_code, res.text)

    if res.status_code == 200:
        print(f"Cartão criado: {titulo}")
    else:
        print(f"Erro ao criar cartão: {res.text}")
