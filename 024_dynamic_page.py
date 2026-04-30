#함수 화 및 구조화

import time
import os

from bs4 import BeautifulSoup
#selenium -> 웹 브라우저의 자동화를 가능하게 해주는 라이브러리 https://www.selenium.dev/
#webdriver -> 셀레니움의 기본 기능을 불러오기 (크롬 브라우저를 자동으로 열고 제어)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.edge.service import Service as EdgeService



# ===== 드라이버 생성 함수 =====
def get_driver_chrome():
    """
    크롬 드라이버를 초기화하여 WebDriver 객체를 반환합니다.
    - 옵션 및 경로 설정을 한 곳에서 관리
    """
    chromeDriver_path = "chromedriver-win64/chromedriver.exe"

    # 크롬 옵션 세팅
    chrome_options = webdriver.ChromeOptions()

    #navigator.webdriver -> true를 false로
    chrome_options.add_argument("disable-blink-features=AutomationControlled")

    #Chrome이 자동화된 테스트 소프트웨어에 의해 제어되고 있습니다 -> x
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation","enable-logging"])

    #시스템 로그 수준 억제 (3: FATAL 에러만 표시)
    chrome_options.add_argument("--log-level=3")


    service = Service(executable_path=chromeDriver_path,log_output=os.devnull)
    return webdriver.Chrome(service=service, options=chrome_options)

def get_driver_edge():
    # 엣지 전용 옵션
    options = webdriver.EdgeOptions()
    service = EdgeService(executable_path="edgedriver_win64/msedgedriver.exe")
    return webdriver.Edge(service=service, options=options)

# ===== 크롤링 함수 =====
def get_google_data(keyword):
    """
    지정된 키워드를 사용하여 Google 검색 결과 페이지의 HTML을 가져온 뒤,
    BeautifulSoup으로 구조화하여 파일로 저장합니다.
    """
    driver = get_driver_chrome()
    # driver = get_driver_edge()

    driver.get(f"https://www.google.com/search?q={keyword}")
    
    time.sleep(15)


    #페이지 HTML 소스 가져오기
    html_doc = driver.page_source
    # print(html_doc)

    #BeautifulSoup으로 파싱
    soup = BeautifulSoup(html_doc, "html.parser")

    #HTML 일부 출력
    # print(soup.prettify()[:1000])

    #파일 저장
    with open("02_result.txt", "w", encoding="utf-8") as file:
        file.write(soup.prettify())

    driver.quit()
    # print("브라우저 종료")


get_google_data("파이썬")
