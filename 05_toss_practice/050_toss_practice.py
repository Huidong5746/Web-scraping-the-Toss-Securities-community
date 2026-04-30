import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 이전 폴더의 크롬 드라이버 경로
service = Service("../chromedriver-win64/chromedriver.exe")


def fetch_visible_comments(company_name, limit=20, max_scroll=10):
    driver = webdriver.Chrome(service=service)

    driver.get("https://www.tossinvest.com/")
    time.sleep(1)

    body = driver.find_element(By.TAG_NAME, "body")
    body.send_keys("/")  # '/' 입력 → 검색창 열림
    time.sleep(1)

    search_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='검색어를 입력해주세요']")
        )
    )
    search_input.send_keys(company_name)
    search_input.send_keys(Keys.ENTER)
    time.sleep(1)

    WebDriverWait(driver, 15).until(EC.url_contains("/order"))
    current_url = driver.current_url
    stock_code = current_url.split("/")[current_url.split("/").index("stocks") + 1]

    community_url = f"https://www.tossinvest.com/stocks/{stock_code}/community"
    driver.get(community_url)
    time.sleep(1)

    # 페이지 로딩 대기 (해시 클래스는 빌드마다 바뀌므로 #stock-content 사용)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#stock-content"))
        )
    except Exception:
        pass
    time.sleep(2)  # SPA 렌더링 여유
    print("[크롤링] 페이지 로드 완료, 댓글 수집 중...")

    # 댓글 수집 (스크롤 반복하며 누적)
    comments = []
    last_height = driver.execute_script("return document.body.scrollHeight")

    comment_selectors = [
        "div > div.tc3tm81 > div > div.tc3tm85 > span > span",
        "article.comment span",
        "#stock-content article span",
    ]

    for scroll in range(max_scroll):
        spans = []
        for sel in comment_selectors:
            spans = driver.find_elements(By.CSS_SELECTOR, sel)
            if spans:
                break

        # 새 댓글 누적 (중복 제거)
        for span in spans:
            text = span.text.strip()
            if text and text not in comments:
                comments.append(text)

        # 목표 개수 이상 모이면 종료
        if len(comments) >= limit:
            break

        # 스크롤 다운
        driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
        )
        time.sleep(1)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:  # 더 이상 내려갈 게 없으면 종료
            break
        last_height = new_height

    driver.quit()
    return comments[:limit]



comments = fetch_visible_comments("삼성전자", limit=20)

print("\n=== 커뮤니티 댓글 (최대 20개) ===")
if not comments:
    print("댓글을 가져오지 못했습니다.")
for i, c in enumerate(comments, 1):
    print(f"{i:02d}. {c}")
