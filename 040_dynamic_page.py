import json
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_DIR = Path(__file__).resolve().parent
CHROME_DRIVER_PATH = BASE_DIR / "chromedriver-win64" / "chromedriver.exe"
RESULT_PATH = BASE_DIR / "04_result.txt"

load_dotenv(BASE_DIR / ".env")


def stream(message):
    """크롤링 진행 상황을 바로 확인할 수 있도록 출력한다."""
    print(message, flush=True)


def print_section(title):
    stream("\n" + "=" * 50)
    stream(title)
    stream("=" * 50)


def print_comment_list(title, comments, limit=10):
    print_section(title)
    if not comments:
        stream("출력할 댓글이 없습니다.")
        return

    for index, comment in enumerate(comments[:limit], 1):
        stream(f"{index}. {comment}")

    if len(comments) > limit:
        stream(f"... 외 {len(comments) - limit}개")


def get_driver_chrome():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option(
        "excludeSwitches",
        ["enable-automation", "enable-logging"],
    )
    chrome_options.add_argument("--log-level=3")

    service = Service(
        executable_path=str(CHROME_DRIVER_PATH),
        log_output=os.devnull,
    )
    return webdriver.Chrome(service=service, options=chrome_options)


def find_stock_name(driver, fallback_name):
    """선택된 종목 페이지에서 실제 매칭된 회사명을 찾는다."""
    selectors = [
        "h1",
        "main h1",
        "#stock-content h1",
        "[data-testid*='stock'] h1",
        "[data-testid*='stock'] strong",
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


def extract_stock_code(driver):
    current_url = driver.current_url
    url_parts = current_url.split("/")

    if "stocks" not in url_parts:
        return None

    stock_index = url_parts.index("stocks")
    if stock_index + 1 >= len(url_parts):
        return None

    return url_parts[stock_index + 1]


def search_and_select_top_company(driver, company_name):
    """토스증권에서 회사명을 검색하고 최상단 결과의 상세 페이지에 접근한다."""
    wait = WebDriverWait(driver, 15)

    stream("[1/5] 토스증권 접속 중...")
    driver.get("https://www.tossinvest.com/")
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    stream(f"[2/5] '{company_name}' 검색어 입력 중...")
    body = driver.find_element(By.TAG_NAME, "body")
    body.send_keys("/")

    search_input = wait.until(
        EC.presence_of_element_located(
            (By.XPATH, "//input[@placeholder='검색어를 입력해주세요']")
        )
    )
    search_input.clear()
    search_input.send_keys(company_name)
    time.sleep(1)

    stream("[3/5] 검색 결과 최상단 회사 선택 중...")
    search_input.send_keys(Keys.ENTER)

    wait.until(EC.url_contains("/stocks/"))
    wait.until(lambda browser: extract_stock_code(browser) is not None)

    stock_name = find_stock_name(driver, company_name)
    stock_code = extract_stock_code(driver)
    detail_url = f"https://www.tossinvest.com/stocks/{stock_code}/order"

    stream(f"[상세 페이지 접근 완료] {company_name} -> {stock_name} ({stock_code})")
    return stock_name, stock_code, detail_url


def move_to_community_area(driver, stock_code):
    """선택된 회사의 상세 페이지에서 커뮤니티 영역으로 이동한다."""
    wait = WebDriverWait(driver, 15)
    community_url = f"https://www.tossinvest.com/stocks/{stock_code}/community"

    stream("[4/5] 선택된 회사의 커뮤니티 영역으로 이동 중...")
    driver.get(community_url)

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#stock-content")))
    except Exception:
        stream("[안내] 기본 콘텐츠 영역을 찾지 못했지만 수집을 계속 시도합니다.")

    time.sleep(2)
    stream("[커뮤니티 이동 완료] 댓글 영역 확인 중...")


def collect_community_comments(driver, limit=20, max_scroll=10):
    """커뮤니티 영역에 게시된 댓글 텍스트 데이터를 수집한다."""
    stream("[5/5] 댓글 수집 시작...")

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
        stream(
            f"[수집 진행] 스크롤 {scroll_count}/{max_scroll}, "
            f"신규 {added_count}개, 누적 {len(comments)}개"
        )

        if len(comments) >= limit:
            stream(f"[수집 완료] 목표 댓글 {limit}개를 채웠습니다.")
            break

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            stream("[수집 완료] 더 이상 내려갈 페이지가 없습니다.")
            break
        last_height = new_height

    return comments[:limit]


def run_llm(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL") or os.getenv("model") or "gpt-5-nano"

    if not api_key:
        stream("[LLM 필터] OPENAI_API_KEY가 없어 부적절 댓글 필터를 건너뜁니다.")
        return None

    llm = init_chat_model(model, model_provider="openai", api_key=api_key)
    response = llm.invoke(
        [
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )
    return response.content


def filter_inappropriate_comments(comments):
    """LLM API를 호출하여 부적절한 댓글을 제거한다."""
    if not comments:
        return [], []

    numbered_comments = "\n".join(
        f"{index}. {comment}" for index, comment in enumerate(comments)
    )
    prompt = f"""
다음 댓글 목록에서 부적절한 댓글(욕설, 혐오, 비방, 선정성, 과도한 비난 등)의 번호(0부터 시작)만 JSON 배열로 알려줘.
응답은 반드시 JSON 배열만 반환해. 예: [0, 2, 5] 또는 []

댓글 목록:
{numbered_comments}
"""

    stream("[전처리] LLM API로 부적절 댓글 판별 중...")
    response_text = run_llm(prompt)
    if response_text is None:
        return list(comments), []

    try:
        remove_indexes = json.loads(response_text.strip())
        remove_indexes = {
            int(index)
            for index in remove_indexes
            if isinstance(index, (int, float)) and 0 <= int(index) < len(comments)
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        stream(f"[LLM 필터] 응답 파싱 실패, 원본 유지: {response_text}")
        return list(comments), []

    removed_comments = [comment for index, comment in enumerate(comments) if index in remove_indexes]
    filtered_comments = [
        comment for index, comment in enumerate(comments) if index not in remove_indexes
    ]

    stream(f"[LLM 필터] 제거 {len(removed_comments)}개, 유지 {len(filtered_comments)}개")
    return filtered_comments, removed_comments


def normalize_comment(comment):
    cleaned = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", comment)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_meaningless_comment(comment):
    compact = re.sub(r"\s+", "", comment)

    if not compact:
        return True
    if re.fullmatch(r"\d+", compact):
        return True
    if re.fullmatch(r"[ㅋㅎㅠㅜ]+", compact):
        return True
    if re.fullmatch(r"(.)\1{2,}", compact):
        return True
    if compact.lower() in {"none", "null", "nan"}:
        return True

    return False


def preprocess_comments(comments, min_length=3, max_length=120):
    """댓글 전처리 결과를 이후 증강/통합 단계에서 활용하기 쉬운 구조로 반환한다."""
    print_section("댓글 전처리 시작")
    stream(f"[전처리] 원본 댓글 {len(comments)}개")

    llm_filtered_comments, inappropriate_comments = filter_inappropriate_comments(comments)
    cleaned_comments = []
    removed_comments = []
    seen = set()

    for comment in llm_filtered_comments:
        original = "" if comment is None else str(comment).strip()
        cleaned = normalize_comment(original)

        reason = None
        if not original:
            reason = "결측치 또는 공백"
        elif len(cleaned) < min_length:
            reason = "길이가 너무 짧음"
        elif len(cleaned) > max_length:
            reason = "길이가 너무 김"
        elif is_meaningless_comment(cleaned):
            reason = "의미 없는 패턴"
        elif cleaned in seen:
            reason = "중복 댓글"

        if reason:
            removed_comments.append(
                {
                    "reason": reason,
                    "original": original,
                    "cleaned": cleaned,
                }
            )
            continue

        seen.add(cleaned)
        cleaned_comments.append(cleaned)

    result = {
        "original_comments": list(comments),
        "llm_filtered_comments": llm_filtered_comments,
        "cleaned_comments": cleaned_comments,
        "removed_comments": removed_comments,
        "inappropriate_comments": inappropriate_comments,
        "settings": {
            "min_length": min_length,
            "max_length": max_length,
        },
    }

    stream(f"[전처리] 부적절 댓글 제거: {len(inappropriate_comments)}개")
    stream(f"[전처리] 규칙 기반 제거: {len(removed_comments)}개")
    stream(f"[전처리] 최종 정제 댓글: {len(cleaned_comments)}개")
    return result


def display_preprocess_result(preprocess_result):
    print_comment_list("원본 댓글", preprocess_result["original_comments"])
    print_comment_list("LLM 제거 댓글", preprocess_result["inappropriate_comments"])
    print_comment_list("정제 댓글", preprocess_result["cleaned_comments"])

    print_section("규칙 기반 제거 내역")
    removed_comments = preprocess_result["removed_comments"]
    if not removed_comments:
        stream("규칙 기반으로 제거된 댓글이 없습니다.")
        return

    for index, item in enumerate(removed_comments[:10], 1):
        stream(f"{index}. [{item['reason']}] {item['original']}")

    if len(removed_comments) > 10:
        stream(f"... 외 {len(removed_comments) - 10}개")


def save_result(keyword, stock_name, stock_code, comments, preprocess_result):
    with open(RESULT_PATH, "w", encoding="utf-8") as result_file:
        result_file.write(f"입력 회사명: {keyword}\n")
        result_file.write(f"선택된 회사명: {stock_name}\n")
        result_file.write(f"종목 코드: {stock_code}\n")
        result_file.write(f"수집 댓글 수: {len(comments)}\n\n")

        result_file.write("[원본 댓글]\n")
        for index, comment in enumerate(comments, 1):
            result_file.write(f"{index}. {comment}\n")

        result_file.write("\n[정제 댓글]\n")
        for index, comment in enumerate(preprocess_result["cleaned_comments"], 1):
            result_file.write(f"{index}. {comment}\n")

        result_file.write("\n[LLM 제거 댓글]\n")
        for index, comment in enumerate(preprocess_result["inappropriate_comments"], 1):
            result_file.write(f"{index}. {comment}\n")

        result_file.write("\n[전처리 메타데이터]\n")
        result_file.write(
            json.dumps(
                {
                    "removed_comments": preprocess_result["removed_comments"],
                    "settings": preprocess_result["settings"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    stream(f"[저장 완료] {RESULT_PATH} 저장 완료")


def crawl_toss_comments(company_name):
    driver = get_driver_chrome()

    try:
        stock_name, stock_code, detail_url = search_and_select_top_company(
            driver,
            company_name,
        )
        stream(f"[상세 페이지 URL] {detail_url}")
        move_to_community_area(driver, stock_code)
        comments = collect_community_comments(driver)
        preprocess_result = preprocess_comments(comments)
        display_preprocess_result(preprocess_result)
        save_result(company_name, stock_name, stock_code, comments, preprocess_result)
    finally:
        driver.quit()
        stream("[종료] 브라우저를 닫았습니다.")


def main():
    company_name = input("검색할 회사명을 입력하세요: ").strip()

    if not company_name:
        stream("[안내] 회사명이 입력되지 않아 크롤링을 종료합니다.")
        return

    crawl_toss_comments(company_name)


if __name__ == "__main__":
    main()
