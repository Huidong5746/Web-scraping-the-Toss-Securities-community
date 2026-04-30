import time
import json
import ast
import os
import sqlite3
from pathlib import Path
from datetime import datetime

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

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")

# 크롬 드라이버 경로
service = Service(str(ROOT_DIR / "chromedriver-win64" / "chromedriver.exe"))
DB_PATH = BASE_DIR / "toss_comments.db"


def init_database():
    """수집 실행 결과를 저장할 SQLite 테이블을 준비한다."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS toss_comment_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requested_company_name TEXT NOT NULL,
                official_stock_name TEXT NOT NULL,
                original_comments TEXT NOT NULL,
                cleaned_comments TEXT NOT NULL,
                augmented_comments TEXT NOT NULL,
                iqr_info TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def save_collection_result(
    requested_company_name,
    official_stock_name,
    original_comments,
    cleaned_comments,
    augmented_comments,
    iqr_info,
):
    """수집, 전처리, 증강 결과를 DB에 한 번의 실행 단위로 저장한다."""
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO toss_comment_runs (
                requested_company_name,
                official_stock_name,
                original_comments,
                cleaned_comments,
                augmented_comments,
                iqr_info,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                requested_company_name,
                official_stock_name,
                json.dumps(original_comments, ensure_ascii=False),
                json.dumps(cleaned_comments, ensure_ascii=False),
                json.dumps(augmented_comments, ensure_ascii=False),
                json.dumps(iqr_info, ensure_ascii=False),
                created_at,
            ),
        )
        return cursor.lastrowid, created_at


def extract_official_stock_name(driver, fallback_name):
    """토스증권 화면에서 실제 매칭된 종목명을 최대한 안정적으로 추출한다."""
    selectors = [
        "h1",
        "[data-testid*='stock'] h1",
        "[data-testid*='stock'] strong",
        "#stock-content h1",
        "main h1",
        "main strong",
    ]

    for selector in selectors:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        for element in elements:
            text = element.text.strip()
            if text and len(text) <= 30:
                return text

    title = driver.title.strip()
    if title:
        return title.split("|")[0].split("-")[0].strip()

    return fallback_name


def fetch_visible_comments(company_name, limit=20, max_scroll=10):
    driver = webdriver.Chrome(service=service)

    try:
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
        official_stock_name = extract_official_stock_name(driver, company_name)

        community_url = f"https://www.tossinvest.com/stocks/{stock_code}/community"
        driver.get(community_url)
        time.sleep(1)

        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#stock-content"))
            )
        except Exception:
            pass
        time.sleep(2)
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

        return official_stock_name, comments[:limit]
    finally:
        driver.quit()

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

    if not comments:
        print("[부적절 필터] 입력 댓글 없음, 스킵")
        return []

    comments = list(comments)

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

def clean_with_pandas(comments):
    """결측치, 특수문자, 반복문자, 숫자, 영어, IQR 기반 이상치 제거"""
    if not comments:
        print("[전처리] 입력 댓글 없음, 스킵")
        return [], {
            "method": "IQR",
            "used": False,
            "reason": "input comments empty",
            "input_count": 0,
            "q1": None,
            "q3": None,
            "iqr": None,
            "lower": None,
            "upper": None,
            "removed_count": 0,
        }

    print(f"시작 (입력", len(comments), "개)")
    df = pd.DataFrame(comments, columns=["comment"])

    #결측치 제거 (None, 공백 등)
    df = df.dropna(subset=["comment"])
    df["comment"] = df["comment"].astype(str).str.strip()
    df = df[df["comment"] != ""]

    #특수문자 제거 (한글/영문/숫자만 유지)
    df["clean"] = df["comment"].apply(lambda x: re.sub(r"[^가-힣a-zA-Z0-9\s]", "", x))
    df["clean"] = df["clean"].str.replace(r"\s+", " ", regex=True).str.strip()

    #불필요한 패턴 제거
    # - 댓글 길이를 기준으로, 정상 범위(숫자-상관)만 남김
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

    #길이 기반 이상치 제거 (IQR)
    #댓글 길이를 기준으로, 정상 범위(숫자-상관)만 남김
    df["length"] = df["clean"].str.len()

    before_iqr_count = len(df)
    iqr_info = {
        "method": "IQR",
        "used": False,
        "reason": None,
        "input_count": before_iqr_count,
        "q1": None,
        "q3": None,
        "iqr": None,
        "lower": None,
        "upper": None,
        "removed_count": 0,
    }

    if len(df) >= 5:
        q1 = df["length"].quantile(0.25)
        q3 = df["length"].quantile(0.75)
        iqr = q3 - q1
        lower = max(5, q1 - 1.5 * iqr)
        upper = q3 + 1.5 * iqr
        cond_iqr = (df["length"] < lower) | (df["length"] > upper)
        iqr_info.update(
            {
                "used": True,
                "q1": float(q1),
                "q3": float(q3),
                "iqr": float(iqr),
                "lower": float(lower),
                "upper": float(upper),
                "removed_count": int(cond_iqr.sum()),
            }
        )
        df = df[~cond_iqr]
    else:
        # 너무 적을때, 3자 미만 제거
        iqr_info.update(
            {
                "reason": "fewer than 5 comments after pattern filtering",
                "lower": 3,
                "removed_count": int((df["length"] < 3).sum()),
            }
        )
        df = df[df["length"] >= 3]

    comments_cleaned = df["clean"].tolist()
    
    # print(len(comments_cleaned))

    return comments_cleaned, iqr_info

# 데이터 증강 (GMS,OpenAI)
def augment_comments(cleaned_result):
    """전처리된 문장에서 일부 샘플 추출 후 GPT로 증강"""

    if not cleaned_result:
        print("[증강] 증강할 데이터 없음, 스킵")
        return []

    print("[증강] LLM 호출로 문장 증강 중... (입력", len(cleaned_result), "개)")

    prompt = f"""
    {cleaned_result}

    위 리스트의 각각의 문장을, 의미는 유지하면서 다르게 표현해줘.
    - 출력 형식: 대괄호 [ 로 시작해서 대괄호 ] 로 끝나는 리스트
    """

    response = run_llm(prompt)
    response_text = str(response).strip()

    # LLM 호출 실패 메시지는 파싱하지 않고 증강 스킵
    if response_text.startswith("[오류 발생]"):
        print("[증강] LLM 오류로 증강 스킵:", response_text)
        return []

    try:
        augmented = ast.literal_eval(response_text)
        if not isinstance(augmented, list):
            augmented = []
    except (ValueError, SyntaxError):
        print("[증강] 응답 파싱 실패로 증강 스킵:", response_text)
        augmented = []

    return augmented


def print_title(title):
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)


def print_comments(title, comments):
    print_title(title)
    if not comments:
        print("출력할 댓글이 없습니다.")
        return

    for i, comment in enumerate(comments, 1):
        print(f"{i}. {comment}")


def main():
    print_title("토스증권 댓글 데이터 수집기")
    company_name = input("회사 이름을 입력하세요: ").strip()

    if not company_name:
        print("[안내] 회사 이름이 입력되지 않아 데이터 수집을 종료합니다.")
        return

    init_database()

    print(f"[시작] '{company_name}' 댓글 데이터를 수집합니다.")
    official_stock_name, comments = fetch_visible_comments(company_name, limit=20)
    print(f"[매칭] 실제 종목명: {official_stock_name}")
    print_comments("수집된 댓글", comments)

    filtered_comments = filter_inappropriate(comments)
    cleaned_comments, iqr_info = clean_with_pandas(filtered_comments)
    augmented_comments = augment_comments(cleaned_comments)

    saved_id, created_at = save_collection_result(
        requested_company_name=company_name,
        official_stock_name=official_stock_name,
        original_comments=comments,
        cleaned_comments=cleaned_comments,
        augmented_comments=augmented_comments,
        iqr_info=iqr_info,
    )

    print_comments("전처리 댓글", cleaned_comments)
    print_comments("증강된 댓글", augmented_comments)
    print_title("DB 저장 완료")
    print(f"저장 위치: {DB_PATH}")
    print(f"저장 ID: {saved_id}")
    print(f"생성 일시: {created_at}")


if __name__ == "__main__":
    main()
