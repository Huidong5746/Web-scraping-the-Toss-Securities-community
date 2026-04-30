import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# 이전 폴더의 크롬 드라이버를 읽어옴
service = Service("../chromedriver-win64/chromedriver.exe")


def open_community_page(company_name):
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
    print(f"종목 코드 추출 완료 → {stock_code}")

    #커뮤니티 페이지 접속
    community_url = f"https://www.tossinvest.com/stocks/{stock_code}/community"
    driver.get(community_url)
    time.sleep(1)

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#stock-content")))
        print("콘텐츠 로드 완료")
    except Exception:
        print("10초 대기 초과: 요소를 찾을 수 없지만 계속 진행합니다.")
    time.sleep(20)

    driver.quit()


open_community_page("삼성전자")
