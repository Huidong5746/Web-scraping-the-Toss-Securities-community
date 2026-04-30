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

import pandas as pd
import re


from dotenv import load_dotenv
load_dotenv("../.env")

# 이전 폴더의 크롬 드라이버 경로
service = Service("../chromedriver-win64/chromedriver.exe")


def fetch_visible_comments(company_name, limit=20, max_scroll=10):
    driver = webdriver.Chrome(service=service)

    # 1. Toss 메인 접속
    driver.get("https://www.tossinvest.com/")
    time.sleep(1)

    # 2. 회사명 검색
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

    # 3. 종목 코드 추출
    WebDriverWait(driver, 15).until(EC.url_contains("/order"))
    current_url = driver.current_url
    stock_code = current_url.split("/")[
        current_url.split("/").index("stocks") + 1
    ]

    # 4. 커뮤니티 페이지 접속
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

    # 5. 댓글 수집 (스크롤 반복하며 누적)
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
    to_remove_idx = sorted(set(int(x) for x in to_remove if isinstance(x, (int, float)) and 0 <= int(x) < len(comments)))
    
    # 걸러진 내용 출력
    if to_remove_idx:
        for i in to_remove_idx:
            print("  -", comments[i])


    # 역순으로 제거 (인덱스 밀림 방지)
    for i in reversed(to_remove_idx):
        comments.pop(i)

    print("[부적절 필터] 남은 댓글", len(comments), "개")
    return comments

result = filter_inappropriate(comments)

def clean_with_pandas(comments):
    """결측치, 특수문자, 반복문자, 숫자, 영어, IQR 기반 이상치 제거"""
    print(f"시작 (입력", len(comments), "개)")
    df = pd.DataFrame(comments, columns=["comment"])

    # 결측치 제거 (None, 공백 등)
    df = df.dropna(subset=["comment"])
    df["comment"] = df["comment"].astype(str).str.strip()
    df = df[df["comment"] != ""]

    # 특수문자 제거 (한글/영문/숫자만 유지)
    df["clean"] = df["comment"].apply(lambda x: re.sub(r"[^가-힣a-zA-Z0-9\s]", "", x))
    df["clean"] = df["clean"].str.replace(r"\s+", " ", regex=True).str.strip()

    # 불필요한 패턴 제거
    # 댓글 길이를 기준으로, 정상 범위(숫자-상관)만 남김
    cond_numeric = df["clean"].str.match(r"^\d+$")
    cond_repeat = df["clean"].str.match(r"^[ㅋㅎ]+$")
    cond_english = df["clean"].str.match(r"^[A-Za-z\s]+$")
    cond_none_literal = df["clean"].str.lower() == "none"

    cond_any = cond_numeric | cond_repeat | cond_english | cond_none_literal
    removed_pattern = df[cond_any]["clean"].tolist()
    if removed_pattern:
        print("[전처리] 걸러짐 — 패턴(숫자만/ㅋㅎ/영어만/none):", len(removed_pattern), "개")
        for x in removed_pattern:
            print("  -", repr(x))
    df = df[~cond_any]

    # 길이 기반 이상치 제거 (IQR)
    # 댓글 길이를 기준으로, 정상 범위(숫자-상관)만 남김
    df["length"] = df["clean"].str.len()

    if len(df) >= 5:
        q1 = df["length"].quantile(0.25)
        q3 = df["length"].quantile(0.75)
        iqr = q3 - q1
        lower = max(5, q1 - 1.5 * iqr)
        upper = q3 + 1.5 * iqr
        cond_iqr = (df["length"] < lower) | (df["length"] > upper)
        df = df[~cond_iqr]
    else:
        # 너무 적을때, 3자 미만 제거
        df = df[df["length"] >= 3]

    comments_cleaned = df["clean"].tolist()
    
    print(len(comments_cleaned))

    return comments_cleaned

cleaned_result = clean_with_pandas(result)

