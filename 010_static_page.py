#파이썬에서 HTML 데이터를 분석할때 사용하는 패키지 BeautifulSoup(핵심 클래스)
#https://beautiful-soup-4.readthedocs.io/en/latest/
# from bs4 import BeautifulSoup
#https://requests.readthedocs.io/en/latest/
# import requests
#표준 라이브러리(Standard Library) 필요할때 사용하기 vs Built-in Functions
# from pprint import pprint

def crawling_basic():
    """
    웹 크롤링의 기본 예제를 수행하는 함수입니다.

    이 함수는 다음과 같은 작업을 수행합니다.
      1. http://quotes.toscrape.com/tag/love/ HTTP GET 요청을 보내 객체를 받습니다.
      2. 객체에서 문자열 값을 BeautifulSoup를 사용하여 파싱합니다.
      3. 파싱된 결과에서 다양한 방법(find, find_all, select_one, select)을 사용해
         특정 HTML 요소들을 검색하고 그 내용을 출력합니다.

    주의: 웹사이트의 구조가 변경될 경우, 선택자(selector) 및 태그명이 달라질 수 있으므로,
           코드의 일부 결과가 달라질 수 있습니다.
    """

    html_doc = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document</title>
    </head>
    <body>
        <p>hello ssafy!</p>
    </body>
    </html>
    """

    print(html_doc)

    # BeautifulSoup 객체 생성 (파싱 시작)
    # 'html.parser'는 파이썬 기본 엔진을 쓰겠다는 뜻
    # soup = BeautifulSoup(html_doc, 'html.parser')

    # print(soup)
    # print(soup.prettify())
    # print(soup.title)

    # response = requests.get("http://quotes.toscrape.com/tag/love/")

    #__repr__
    #ex) <urllib3.response.HTTPResponse object at 0x000001AD4D365150> -> <Response [200]>
    # print(response)
    # print(response.__dict__)
    # pprint(response.__dict__)

    # html_doc = response.text

    # print(html_doc)

    # soup = BeautifulSoup(html_doc, 'html.parser')


    #첫 번째 <a> 태그를 찾기
    #find() 함수는 지정한 '태그'의 첫 번째 요소만 반환
    # main = soup.find('a')
    # print(f'첫 번째 a 태그의 텍스트: {main.text}')
    # main = soup.find(class_='header-box')
    # main = soup.find('div', class_='header-box')
    # print(main)

    #페이지 내에 존재하는 모든 <a> 태그를 검색
    #find_all() 함수는 해당 태그를 모두 리스트 형태로 반환
    # a_tags = soup.find_all('a')
    # print(f'전체 a 태그 리스트: {a_tags}')

    # for a_tag in a_tags:
    #     print(a_tag.get('href'))

    #CSS 선택자를 사용하여 클래스 이름이 'text'인 요소 중 첫 번째 요소를 검색
    #select_one() 함수는 선택자와 일치하는 첫 번째 요소를 반환
    # word = soup.select_one('.text')
    # print(f'CSS 선택자(.text)를 사용해 찾은 첫 번째 요소의 텍스트: {word.text}')

    #CSS 선택자를 사용하여 클래스 이름이 'text'인 모든 요소를 검색
    #select() 함수는 선택자와 일치하는 모든 요소를 리스트로 반환
    # words = soup.select('.text')
    # for w in words:
    #     print(f'요소 텍스트: {w.text}')


    #x번째 원소찾기

    # second_a = soup.find_all('a')[1]
    # second_a = soup.select('a')[1]
    # second_a = soup.find('a').find_next('a')
    # print(second_a)


    #find로 select차이?

    # result = soup.find('div', class_='quote').find('span', class_='text').get_text()
    # print(result)
    # result = soup.select_one('div.quote span.text').get_text()
    # print(result)



# crawling_basic() 함수를 실행
crawling_basic()