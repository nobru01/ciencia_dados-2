from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from fake_useragent import UserAgent


def _apply_proxy_env(proxy_url: Optional[str]) -> None:
    if not proxy_url:
        return
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ.setdefault("NO_PROXY", "localhost,127.0.0.1")


def _chrome_options(user_agent: str, proxy_url: Optional[str] = None) -> ChromeOptions:
    chrome_options = ChromeOptions()
    chrome_options.add_argument(f"--user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--headless=new")
    if proxy_url:
        chrome_options.add_argument(f"--proxy-server={proxy_url}")
    return chrome_options


def _build_chrome(user_agent: str, proxy_url: Optional[str] = None) -> webdriver.Chrome:
    # 1) Tenta com Selenium Manager (padrão do Selenium 4.6+)
    _apply_proxy_env(proxy_url)
    options = _chrome_options(user_agent, proxy_url)
    try:
        return webdriver.Chrome(options=options)
    except Exception as exc:
        print("[WARN] Selenium Manager falhou ao resolver o driver automaticamente.")
        print(f"[WARN] Erro: {exc}")

    # 2) Fallback: tenta um chromedriver local por variável de ambiente ou pasta drivers/
    local_driver = os.environ.get("CHROMEDRIVER")
    if not local_driver:
        local_driver = str(Path("drivers") / ("chromedriver.exe" if os.name == "nt" else "chromedriver"))

    if Path(local_driver).exists():
        print(f"[INFO] Usando chromedriver local: {local_driver}")
        from selenium.webdriver.chrome.service import Service as ChromeService

        service = ChromeService(executable_path=local_driver)
        return webdriver.Chrome(service=service, options=options)

    raise RuntimeError(
        "Não foi possível obter o ChromeDriver automaticamente e nenhum driver local foi encontrado. "
        "Baixe o arquivo compatível com seu Chrome 140 e salve em 'drivers/chromedriver.exe' "
        "ou defina a variável de ambiente CHROMEDRIVER apontando para o executável."
    )


def _random_user_agent() -> str:
    try:
        ua = UserAgent()
        return ua.random
    except Exception:
        fallback_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
        ]
        return random.choice(fallback_list)


def scrape_first_page(url: str = "https://quotes.toscrape.com/", proxy_url: Optional[str] = None) -> List[Dict[str, str]]:
    user_agent = _random_user_agent()
    print(f"[INFO] Iniciando navegador com user-agent: {user_agent}")
    if proxy_url:
        print(f"[INFO] Usando proxy: {proxy_url}")
    driver = _build_chrome(user_agent, proxy_url)
    wait = WebDriverWait(driver, 15)

    data: List[Dict[str, str]] = []
    try:
        print(f"[INFO] Acessando URL: {url}")
        driver.get(url)

        # Espera pela lista de citações
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='quote']")))
        quotes = driver.find_elements(By.XPATH, "//div[@class='quote']")
        print(f"[INFO] Quantidade de citações encontradas: {len(quotes)}")

        for idx, q in enumerate(quotes, start=1):
            try:
                quote_text = q.find_element(By.XPATH, ".//span[@class='text']").text
                author = q.find_element(By.XPATH, ".//small[@class='author']").text
                tag_elements = q.find_elements(By.XPATH, ".//div[@class='tags']/a[@class='tag']")
                tags = [t.text for t in tag_elements]
                item = {"quote": quote_text, "author": author, "tags": tags}
                data.append(item)
                print(f"[OK] Coletada citação #{idx} de '{author}' com {len(tags)} tag(s)")
            except NoSuchElementException:
                print(f"[WARN] Falha ao coletar elementos da citação #{idx}")

    except TimeoutException:
        print("[ERRO] Tempo de espera excedido ao carregar os elementos da página.")
    finally:
        driver.quit()
        print("[INFO] Navegador encerrado.")

    return data


def save_to_txt(items: List[Dict[str, str]], path: str = "resposta.txt") -> None:
    with open(path, "w", encoding="utf-8") as f:
        for obj in items:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"[INFO] Arquivo salvo em: {path}")


def scrape_all_pages(start_url: str = "https://quotes.toscrape.com/", proxy_url: Optional[str] = None) -> List[Dict[str, str]]:
    user_agent = _random_user_agent()
    if proxy_url:
        print(f"[INFO] Usando proxy: {proxy_url}")
    print(f"[INFO] Iniciando navegador com user-agent: {user_agent}")
    driver = _build_chrome(user_agent, proxy_url)
    wait = WebDriverWait(driver, 15)

    all_items: List[Dict[str, str]] = []
    current_url = start_url

    try:
        while True:
            print(f"[INFO] Acessando URL: {current_url}")
            driver.get(current_url)

            wait.until(EC.presence_of_all_elements_located((By.XPATH, "//div[@class='quote']")))
            quotes = driver.find_elements(By.XPATH, "//div[@class='quote']")
            print(f"[INFO] Quantidade de citações encontradas nesta página: {len(quotes)}")

            for idx, q in enumerate(quotes, start=1):
                try:
                    quote_text = q.find_element(By.XPATH, ".//span[@class='text']").text
                    author = q.find_element(By.XPATH, ".//small[@class='author']").text
                    tag_elements = q.find_elements(By.XPATH, ".//div[@class='tags']/a[@class='tag']")
                    tags = [t.text for t in tag_elements]
                    all_items.append({"quote": quote_text, "author": author, "tags": tags})
                    print(f"[OK] Citação de '{author}' coletada")
                except NoSuchElementException:
                    print("[WARN] Falha ao coletar uma citação desta página")

            # Tenta ir para a próxima página
            try:
                next_link = driver.find_element(By.XPATH, "//li[@class='next']/a")
                next_href = next_link.get_attribute("href")
                if not next_href:
                    # alguns sites usam href relativo
                    next_href = next_link.get_attribute("href") or next_link.get_attribute("data-href")
                current_url = next_href if next_href else driver.current_url.rstrip('/') + "/page/2/"
                print(f"[INFO] Avançando para a próxima página: {current_url}")
            except NoSuchElementException:
                print("[INFO] Não há mais páginas. Coleta finalizada.")
                break

    except TimeoutException:
        print("[ERRO] Tempo de espera excedido ao carregar os elementos da página.")
    finally:
        driver.quit()
        print("[INFO] Navegador encerrado.")

    return all_items


if __name__ == "__main__":
    print("[INFO] Iniciando coleta de todas as páginas de quotes.toscrape.com")
    proxy_env = os.environ.get("PROXY_URL") or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    if proxy_env:
        print(f"[INFO] Proxy detectado em ambiente: {proxy_env}")
    results = scrape_all_pages("https://quotes.toscrape.com/", proxy_url=proxy_env)
    print(f"[INFO] Total coletado: {len(results)} itens")
    save_to_txt(results, "resposta.txt")


