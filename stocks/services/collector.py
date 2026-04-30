import os
import time
from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_DIR = Path(__file__).resolve().parents[2]
CHROME_DRIVER_PATH = BASE_DIR / "chromedriver-win64" / "chromedriver.exe"


class StockSearchNotFound(Exception):
    """회사 검색 결과를 확인할 수 없을 때 사용자에게 안내하기 위한 예외."""


@dataclass
class CollectionResult:
    requested_company_name: str
    official_stock_name: str
    stock_code: str
    detail_url: str
    community_url: str
    original_comments: list[str]
    steps: list[str]


def create_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option(
        "excludeSwitches",
        ["enable-automation", "enable-logging"],
    )
    chrome_options.add_argument("--log-level=3")

    if os.getenv("SELENIUM_HEADLESS", "0") == "1":
        chrome_options.add_argument("--headless=new")

    service = Service(
        executable_path=str(CHROME_DRIVER_PATH),
        log_output=os.devnull,
    )
    return webdriver.Chrome(service=service, options=chrome_options)


def extract_stock_code(driver):
    url_parts = driver.current_url.split("/")
    if "stocks" not in url_parts:
        return None

    stock_index = url_parts.index("stocks")
    if stock_index + 1 >= len(url_parts):
        return None

    return url_parts[stock_index + 1]


def find_stock_name(driver, fallback_name):
    selectors = [
        "h1",
        "main h1",
        "#stock-content h1",
        "[data-testid*='stock'] h1",
        "[data-testid*='stock'] strong",
    ]

    for selector in selectors:
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            text = element.text.strip()
            if text and len(text) <= 30:
                return text

    title = driver.title.strip()
    if title:
        return title.split("|")[0].split("-")[0].strip()

    return fallback_name


def search_top_stock(driver, company_name, steps):
    wait = WebDriverWait(driver, 15)
    steps.append("토스증권 메인 페이지에 접속했습니다.")
    driver.get("https://www.tossinvest.com/")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    steps.append(f"입력값 '{company_name}'으로 회사를 검색했습니다.")
    body = driver.find_element(By.TAG_NAME, "body")
    body.send_keys("/")

    try:
        search_input = wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='검색어를 입력해주세요']")
            )
        )
    except TimeoutException as exc:
        steps.append("검색창을 찾지 못해 검색을 진행할 수 없습니다.")
        raise StockSearchNotFound(
            "현재 토스증권 검색창을 찾을 수 없습니다. 잠시 후 다시 시도해 주세요."
        ) from exc

    search_input.clear()
    search_input.send_keys(company_name)
    time.sleep(1)

    steps.append("검색 결과 최상단 회사를 자동 선택했습니다.")
    search_input.send_keys(Keys.ENTER)

    try:
        wait.until(EC.url_contains("/stocks/"))
        wait.until(lambda browser: extract_stock_code(browser) is not None)
    except TimeoutException as exc:
        steps.append("검색 결과에서 선택 가능한 회사를 찾지 못했습니다.")
        raise StockSearchNotFound(
            f"'{company_name}'에 대한 회사 검색 결과를 찾지 못했습니다. 회사명을 더 정확히 입력해 주세요."
        ) from exc

    stock_code = extract_stock_code(driver)
    if stock_code is None:
        steps.append("선택된 회사의 종목 코드를 확인하지 못했습니다.")
        raise StockSearchNotFound(
            f"'{company_name}' 검색 결과의 종목 정보를 확인하지 못했습니다. 다른 회사명으로 다시 시도해 주세요."
        )

    stock_name = find_stock_name(driver, company_name)
    detail_url = f"https://www.tossinvest.com/stocks/{stock_code}/order"
    steps.append(f"상세 페이지에 접근했습니다: {stock_name} ({stock_code})")
    return stock_name, stock_code, detail_url


def move_to_community(driver, stock_code, steps):
    wait = WebDriverWait(driver, 15)
    community_url = f"https://www.tossinvest.com/stocks/{stock_code}/community"

    steps.append("선택된 회사의 커뮤니티 영역으로 이동했습니다.")
    driver.get(community_url)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#stock-content")))
    except Exception:
        steps.append("기본 콘텐츠 영역 대기 시간이 초과되어 댓글 수집을 바로 시도했습니다.")

    time.sleep(2)
    return community_url


def collect_comments(driver, steps, limit=20, max_scroll=10):
    comments = []
    last_height = driver.execute_script("return document.body.scrollHeight")
    comment_selectors = [
        "div > div.tc3tm81 > div > div.tc3tm85 > span > span",
        "article.comment span",
        "#stock-content article span",
    ]

    for scroll_count in range(1, max_scroll + 1):
        spans = []
        for selector in comment_selectors:
            spans = driver.find_elements(By.CSS_SELECTOR, selector)
            if spans:
                break

        before_count = len(comments)
        for span in spans:
            text = span.text.strip()
            if text and text not in comments:
                comments.append(text)

        added_count = len(comments) - before_count
        steps.append(
            f"댓글 수집 진행: 스크롤 {scroll_count}/{max_scroll}, "
            f"신규 {added_count}개, 누적 {len(comments)}개"
        )

        if len(comments) >= limit:
            steps.append(f"목표 댓글 {limit}개를 채워 수집을 종료했습니다.")
            break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            steps.append("더 이상 내려갈 페이지가 없어 수집을 종료했습니다.")
            break
        last_height = new_height

    comments = comments[:limit]
    if comments:
        steps.append(f"댓글 데이터 {len(comments)}개를 수집했습니다.")
    else:
        steps.append("커뮤니티 영역에서 수집 가능한 댓글 데이터가 없습니다.")

    return comments


def collect_stock_comments(company_name, limit=20):
    steps = []
    driver = create_driver()

    try:
        stock_name, stock_code, detail_url = search_top_stock(
            driver,
            company_name,
            steps,
        )
        community_url = move_to_community(driver, stock_code, steps)
        comments = collect_comments(driver, steps, limit=limit)

        return CollectionResult(
            requested_company_name=company_name,
            official_stock_name=stock_name,
            stock_code=stock_code,
            detail_url=detail_url,
            community_url=community_url,
            original_comments=comments,
            steps=steps,
        )
    finally:
        driver.quit()
