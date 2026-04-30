# 셀레니움(자동으로 웹 브라우저를 제어하는 도구) 공식 문서 URL
# https://www.selenium.dev/documentation/webdriver/waits/

# 시간을 다루기 위한 라이브러리
import time

from selenium import webdriver
# 크롬 브라우저의 위치/경로를 설정하기 위한 기능
from selenium.webdriver.chrome.service import Service
# 웹페이지의 버튼, 텍스트, 제목 등 특정 요소를 찾기 위한 방법들
from selenium.webdriver.common.by import By
# 웹페이지가 제대로 로딩되었는지 확인하는 여러 조건들
from selenium.webdriver.support import expected_conditions as EC
# 특정 조건이 완료될 때까지 기다리는 기능
from selenium.webdriver.support.ui import WebDriverWait

#설치된 크롬 자동화 도구(chromedriver)의 경로를 저장
service = Service("../chromedriver-win64/chromedriver.exe")

def open_toss_main():
    
    driver = webdriver.Chrome(service=service)
    
    driver.get("https://www.tossinvest.com/")

    # time.sleep(3)

    # 페이지가 제대로 열렸는지 더 정확하게 확인하기
    # 최대 10초 기다리면서, 웹페이지의 본문(body) 부분이 나타났는지 계속 확인
    # - 만약 1초 안에 나타나면 바로 다음으로 진행
    # - 만약 10초까지 기다렸는데도 안 나타나면 오류 발생
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    # WebDriverWait(driver, 10)	driver를 최대 10초 동안 대기시키겠다는 설정
    # until 조건이 True가 될 때까지 반복해서 확인
    # EC.presence_of_element_located (해당 요소가 DOM(HTML 구조) 상에 존재할 때까지라는 조건)
    # (By.TAG_NAME, "body") 찾고자 하는 대상입니다. 여기서는 <body> 태그를 지칭
    
    print("TossInvest 메인 페이지 접속 완료")

    #브라우저 닫기
    driver.quit()

open_toss_main()
