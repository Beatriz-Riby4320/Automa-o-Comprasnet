import re
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone
from trello_automacao import criar_cartao_trello

fuso_brasilia = timezone(timedelta(hours=-3))

def parse_data_abertura(abertura_str: str) -> datetime:
    s = abertura_str.strip()
    # Regex para data + hora
    m = re.search(r"(\d{2}/\d{2}/\d{4})\D+(\d{2}:\d{2})(?::\d{2})?", s)
    if m:
        data = m.group(1)
        hora = m.group(2)
        try:
            dt = datetime.strptime(f"{data} {hora}", "%d/%m/%Y %H:%M")
            return dt.replace(tzinfo=fuso_brasilia)
        except ValueError:
            pass
    # Só data
    m2 = re.search(r"(\d{2}/\d{2}/\d{4})", s)
    if m2:
        try:
            dt = datetime.strptime(m2.group(1), "%d/%m/%Y")
            dt = dt.replace(hour=12, minute=0)
            return dt.replace(tzinfo=fuso_brasilia)
        except ValueError:
            pass
    return datetime.now(fuso_brasilia)

def extrair_contratacoes():
    contratacoes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Login
        page.goto("https://busca.r-licitacoes.com.br/login", timeout=60000, wait_until="domcontentloaded")
        page.fill('input[name="usuario"]', '44.954.785/0001-07')
        page.fill('input[name="senha"]', 'BEATRIZ@01')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Abre quadro Kanban
        page.get_by_title('Quadro Kanban').get_by_role('link').click()
        page.wait_for_timeout(3000)

        coluna = page.locator('div#coluna[data-id="1"]')
        cards = coluna.locator('div.shadow-sm.mb-2')

        for i in range(cards.count()):
            card = cards.nth(i)
            badges = card.locator("span.badge").all_inner_texts()

            # Abre modal do card atual
            card.locator('button[title="Ver Detalhes"]').click()
            page.wait_for_selector("div.modal.show .modal-content", timeout=20000)
            modal = page.locator("div.modal.show .modal-content")

            # Extrai título
            titulo = modal.locator("div.fs-4.mb-3 b").first.text_content().strip()

            edital_text = modal.locator("div.mb-2").nth(0).inner_text()
            edital = edital_text.split("Nº Edital:")[-1].split("|")[0].strip()
            codigo = edital_text.split("Código:")[-1].strip()

            modo_disputa = modal.locator("div.mb-2").nth(1).inner_text().split(":")[-1].strip()
            preferencial_me = modal.locator("div.mb-2").nth(2).inner_text().split(":")[-1].strip()
            endereco = modal.locator("div.mb-2").nth(3).inner_text().split(":")[-1].strip()

            publicacao = modal.locator("div.col div.mb-2").nth(0).inner_text().split(":")[-1].strip()

            # Extrai abertura com XPath relativo
            abertura_text = modal.locator("xpath=.//div[@class='mb-2'][b[text()='Abertura:']]").inner_text()
            abertura = abertura_text.replace("Abertura:", "").strip()
            data_abertura = parse_data_abertura(abertura)

            disputa = modal.locator("div.col div.mb-2").nth(2).inner_text().split(":")[-1].strip()
            objeto = modal.locator("div.row.mb-2 div.col").inner_text().strip()

            # Debug
            print("Título:", titulo,
                  "| Abertura texto:", abertura_text,
                  "| Data convertida:", data_abertura.isoformat())

            # Itens da compra
            itens = []
            linhas = modal.locator("table#example tbody tr")
            for j in range(linhas.count()):
                cols = linhas.nth(j).locator("td").all_inner_texts()
                if len(cols) >= 4:
                    itens.append({
                        "numero": cols[0].strip(),
                        "descricao": cols[1].strip(),
                        "unidade": cols[2].strip(),
                        "quantidade": cols[3].strip()
                    })

            descricao = (
                f"Nº Edital: {edital}\n"
                f"Código: {codigo}\n"
                f"Modo Disputa: {modo_disputa}\n"
                f"Preferencial ME: {preferencial_me}\n"
                f"Endereço: {endereco}\n"
                f"Publicação: {publicacao}\n"
                f"Abertura: {abertura}\n"
                f"Disputa: {disputa}\n\n"
                f"{objeto}\n\n"
                f"Itens da Compra:\n"
            )
            for item in itens:
                descricao += (
                    f"- Item {item['numero']}: {item['descricao']} "
                    f"({item['unidade']}) — Quantidade: {item['quantidade']}\n"
                )

            link_portal = modal.locator("a.btn.btn-outline-primary").get_attribute("href") or "Link não disponível"

            contratacoes.append({
                "titulo": titulo,
                "descricao": descricao,
                "data_abertura": data_abertura,
                "link_portal": link_portal,
                "badges": badges
            })

            # Fecha modal
            modal.locator('button.btn-close').click()
            page.wait_for_selector("div.modal.show .modal-content", state="hidden", timeout=10000)

    return contratacoes

if __name__ == "__main__":
    contratacoes = extrair_contratacoes()
    for item in contratacoes:
        criar_cartao_trello(
            titulo=item["titulo"],
            descricao=item["descricao"],
            data_abertura=item["data_abertura"],
            link_portal=item["link_portal"],
            badges=item["badges"]
        )
