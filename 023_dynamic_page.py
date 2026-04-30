# 페이지 소스(HTML) 획득 및 뷰티풀수프 연결

from selenium import webdriver
from bs4 import BeautifulSoup


#셀레니움을 제어하는 옵션
chrome_options = webdriver.ChromeOptions()
chrome_options.add_experimental_option("detach", True) # 페이지를 다 읽어도 브라우저를 유지함 (quit보단 후순위)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) #Chrome이 자동화된 테스트 소프트웨어에 의해 제어되고 있습니다 -> x
chrome_options.add_argument("disable-blink-features=AutomationControlled") # 셀레니움 같은 자동화 도구에 의해 제어되고 있는지


driver = webdriver.Chrome(options=chrome_options)

driver.get("https://www.google.com/search?q=파이썬")

html_doc = driver.page_source
# print(html_doc)

soup = BeautifulSoup(html_doc, "html.parser")

#HTML 일부 출력
# print(soup.prettify()[:1000])

#파일 저장

#with : 컨텍스트 매니저 -> 파일 열고 작업이 끝난 뒤 자동으로 닫아줌
#open(파일명, 쓰기모드-> 없으면 새로 만들기 있으면 기존 내용 다지우고 새로 쓰기, 인코딩) file -> 객체내에서 열린 파일을 file 변수로 설정
with open("02_result.txt", "w", encoding="utf-8") as file: 
    file.write(soup.prettify())