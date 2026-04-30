from selenium import webdriver
from selenium.webdriver.edge.service import Service

# 크롬 드라이버 실행 (가장 기본형)
# driver = webdriver.Chrome()

#엣지
driver_path = "edgedriver_win64/msedgedriver.exe"
service = Service(executable_path="edgedriver_win64/msedgedriver.exe")
driver = webdriver.Edge(service=service)

#원하는 페이지로 이동
driver.get("https://www.google.com")
