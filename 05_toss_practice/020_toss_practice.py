import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


service = Service("../chromedriver-win64/chromedriver.exe")


def search_company(company_name):
    driver = webdriver.Chrome(service=service)

    driver.get("https://www.tossinvest.com/")
    time.sleep(1) 

    # body 태그를 선택하여 '/' 입력 → 검색창 열림
    body = driver.find_element(By.TAG_NAME, "body")
    body.send_keys("/")
    time.sleep(1)

    # 검색 입력창 요소를 찾고, 회사명을 입력 후 Enter 입력
    # XPATH //태그명[@속성명='속성값']
    # //div[@id='login-box'] (ID가 login-box인 div)
    # //*[text()='확인'] (태그 상관없이 '확인'이라는 글자가 적힌 모든 것)
    search_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='검색어를 입력해주세요']")))
    search_input.send_keys(company_name)
    search_input.send_keys(Keys.ENTER)
    time.sleep(3)

    print(f"'{company_name}' 검색 완료")
    driver.quit()



search_company("삼성전자")
