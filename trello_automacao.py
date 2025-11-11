import os, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
TOKEN = os.getenv("TRELLO_TOKEN")
LIST_ID = os.getenv("LIST_ID")
LABEL_COMPRASNET = os.getenv("LABEL_COMPRASNET")
LABEL_DE = os.getenv("LABEL_DE")

def criar_cartao_trello(titulo, descricao, data_abertura, link_portal):
    url = "https://api.trello.com/1/cards"
    params = {
        "key": API_KEY,
        "token": TOKEN,
        "idList": LIST_ID,
        "name": titulo,
        "desc": descricao,
        "idLabels": ",".join([LABEL_COMPRASNET, LABEL_DE]),
        "due": data_abertura.isoformat(),
        "dueReminder": 1440
    }
    res = requests.post(url, params=params)
    card = res.json()

    # Adiciona comentário com link do portal
    comment_url = f"https://api.trello.com/1/cards/{card['id']}/actions/comments"
    requests.post(comment_url, params={"key": API_KEY, "token": TOKEN, "text": link_portal})

    return card
