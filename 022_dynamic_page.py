#자동 종료 방지와 옵션 설정
from selenium import webdriver


#셀레니움을 제어하는 옵션
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True) # 페이지를 다 읽어도 브라우저를 유지함 (quit보단 후순위)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) #Chrome이 자동화된 테스트 소프트웨어에 의해 제어되고 있습니다 -> x
chrome_options.add_argument("disable-blink-features=AutomationControlled") # 셀레니움 같은 자동화 도구에 의해 제어되고 있는지

driver = webdriver.Chrome(options=chrome_options)

driver.get("https://www.google.com")
