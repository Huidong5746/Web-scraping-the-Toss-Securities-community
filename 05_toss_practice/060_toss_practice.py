import time
import json
import ast
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from langchain.chat_models import init_chat_model

from dotenv import load_dotenv
load_dotenv("../.env")

# 이전 폴더의 크롬 드라이버 경로
service = Service("../chromedriver-win64/chromedriver.exe")


def fetch_visible_comments(company_name, limit=20, max_scroll=10):
    driver = webdriver.Chrome(service=service)

    driver.get("https://www.tossinvest.com/")
    time.sleep(1)

    body = driver.find_element(By.TAG_NAME, "body")
    body.send_keys("/")
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
    stock_code = current_url.split("/")[
        current_url.split("/").index("stocks") + 1
    ]

    community_url = f"https://www.tossinvest.com/stocks/{stock_code}/community"
    driver.get(community_url)
    time.sleep(1)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#stock-content"))
        )
    except Exception:
        pass
    time.sleep(2)  # SPA 렌더링 여유
    print("[크롤링] 페이지 로드 완료, 댓글 수집 중...")

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

def run_llm(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    MODEL = os.getenv("MODEL")
    llm = init_chat_model(MODEL, model_provider="openai",api_key=api_key)
    result = llm.invoke(
        [
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )
    return result.content

#부적절 댓글 필터
def filter_inappropriate(comments):
    """욕설·혐오·비방·선정성 등 부적절 댓글을 LLM으로 판별해 제거"""

    # before = len(comments)
    print(f"LLM으로 부적절 댓글 판별 중... (입력", len(comments), "개)")
    numbered = "\n".join(f"{i}. {c}" for i, c in enumerate(comments))

    prompt = f"""
    다음 댓글 목록에서 부적절한 댓글(욕설, 혐오, 비방, 선정성, 과도한 비난 등)의 번호만 반환해줘.
    응답은 반드시 이 형식만: [0, 2, 5] 또는 []
    다른 설명이나 마크다운 없이 배열만 반환.

    댓글 목록:
    {numbered}
    """

    response = run_llm(prompt).strip()
    print(response)
    to_remove = json.loads(response)

    # 제거할 인덱스 (유효한 것만)
    # isinstance(x, (int, float)): 숫자체크
    # 0 <= int(x) < len(comments) 유효범위체크
    # 정수변환 및 중복제거
    to_remove_idx = sorted(set(int(x) for x in to_remove if isinstance(x, (int, float)) and 0 <= int(x) < len(comments)))
    
    # 걸러진 내용 출력
    if to_remove_idx:
        for i in to_remove_idx:
            print("  -", comments[i])


    # 역순으로 제거 (인덱스 밀림 방지)
    for i in reversed(to_remove_idx):
        comments.pop(i)

    print("[부적절 필터] 남은 댓글", len(comments), "개")

filter_inappropriate(comments)


