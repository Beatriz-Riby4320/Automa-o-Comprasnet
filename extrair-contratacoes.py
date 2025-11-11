from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone
from trello_automacao import criar_cartao_trello

fuso_brasilia = timezone(timedelta(hours=-3))

def extrair_contratacoes():
    contratacoes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Login
        page.goto('https://busca.r-licitacoes.com.br/login')
        page.fill('input[name="usuario"]', '44.954.785/0001-07')
        page.fill('input[name="senha"]', 'BEATRIZ@01')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Abre quadro Kanban
        page.get_by_title('Quadro Kanban').get_by_role('link').click()
        page.wait_for_timeout(3000)

        # Coluna OPORTUNIDADE
        coluna = page.locator('div#coluna[data-id="1"]')
        cards = coluna.locator('div.shadow-sm.mb-2')

        for i in range(cards.count()):
            card = cards.nth(i)
            badges = card.locator("span.badge").all_inner_texts()

            if "COMPRASNET" in badges and "DISPENSA" in badges:
                # Clica em Ver Detalhes
                card.locator('button[title="Ver Detalhes"]').click()
                page.wait_for_selector("div.modal-content", timeout=10000)

                # Extrai campos do modal
                titulo = page.locator("div.modal-content h5").inner_text()
                edital = page.locator("text=N° Edital").locator("xpath=..").inner_text().split(":")[-1].strip()
                codigo_uasg = page.locator("text=Código UASG").locator("xpath=..").inner_text().split(":")[-1].strip()
                modo_disputa = page.locator("text=Modo Disputa").locator("xpath=..").inner_text().split(":")[-1].strip()
                registro_precos = page.locator("text=Registro de Preços").locator("xpath=..").inner_text().split(":")[-1].strip()
                publicacao = page.locator("text=Publicação").locator("xpath=..").inner_text().split(":")[-1].strip()
                abertura = page.locator("text=Abertura").locator("xpath=..").inner_text().split(":")[-1].strip()
                entrega = page.locator("text=Entrega").locator("xpath=..").inner_text().split(":")[-1].strip()
                objeto = page.locator("div.modal-content p").inner_text()

                # Extrai itens da compra
                itens = []
                linhas = page.locator("div.modal-content table tbody tr")
                for j in range(linhas.count()):
                    cols = linhas.nth(j).locator("td").all_inner_texts()
                    if len(cols) >= 4:
                        itens.append({
                            "numero": cols[0].strip(),
                            "descricao": cols[1].strip(),
                            "unidade": cols[2].strip(),
                            "quantidade": cols[3].strip()
                        })

                # Monta descrição
                descricao = (
                    f"Nº Edital: {edital}\n"
                    f"Código UASG: {codigo_uasg}\n"
                    f"Modo Disputa: {modo_disputa}\n"
                    f"Registro de Preços: {registro_precos}\n"
                    f"Publicação: {publicacao}\n"
                    f"Abertura: {abertura}\n"
                    f"Entrega: {entrega}\n\n"
                    f"{objeto}\n\n"
                    f"Itens da Compra:\n"
                )
                for item in itens:
                    descricao += (
                        f"- Item {item['numero']}: {item['descricao']} "
                        f"({item['unidade']}) — Quantidade: {item['quantidade']}\n"
                    )

                # Converte data de abertura
                try:
                    data_abertura = datetime.strptime(abertura, "%d/%m/%Y %H:%M").replace(tzinfo=fuso_brasilia)
                except:
                    data_abertura = datetime.now(fuso_brasilia)

                # Extrai link do botão Portal
                link_portal = page.locator('button[title="Portal"]').get_attribute("onclick")
                if link_portal:
                    codigo = link_portal.split("(")[-1].split(")")[0]
                    link_final = f"https://cnetmobile.estaleiro.serpro.gov.br/comprasnet-web/public/compras/acompanhamento-compra?compra={codigo}"
                else:
                    link_final = "Link não disponível"

                contratacoes.append({
                    "titulo": titulo,
                    "descricao": descricao,
                    "data_abertura": data_abertura,
                    "link_portal": link_final
                })

                # Fecha modal
                page.locator('button[title="Fechar"]').click()
                page.wait_for_timeout(1000)

    return contratacoes


if __name__ == "__main__":
    contratacoes = extrair_contratacoes()
    for item in contratacoes:
        criar_cartao_trello(
            titulo=item["titulo"],
            descricao=item["descricao"],
            data_abertura=item["data_abertura"],
            link_portal=item["link_portal"]
        )
