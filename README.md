# Toss Securities Community Comment Scraper

토스증권 커뮤니티에서 종목별 댓글을 수집하고, 수집한 텍스트를 전처리한 뒤 LLM 기반 증강 및 요약 결과를 Django 웹 화면에서 확인하는 프로젝트입니다.

## 프로젝트 책임자
- 김희동

## 주요 기능

- 회사명 또는 종목명을 입력해 토스증권에서 관련 종목을 검색합니다.
- Selenium과 ChromeDriver를 사용해 해당 종목의 커뮤니티 페이지 댓글을 수집합니다.
- 수집 댓글에서 중복, 짧은 문장, 의미 없는 패턴, 과도하게 긴 문장 등을 제거합니다.
- OpenAI 또는 GMS 호환 LLM API를 사용해 부적절 댓글 필터링, 댓글 증강, 전체 분위기 요약을 수행합니다.
- 원본 댓글, 전처리 댓글, 증강 댓글, 통합 데이터셋, 처리 단계 로그를 Django 페이지에서 보여줍니다.
- `05_toss_practice` 폴더에는 단계별 스크래핑/전처리/저장 연습용 스크립트가 포함되어 있습니다.

## 프로젝트 구조

```text
.
├── manage.py
├── requirements.txt
├── config/                     # Django 프로젝트 설정
├── stocks/                     # Django 앱
│   ├── forms.py                # 종목 검색 입력 폼
│   ├── views.py                # 검색 요청 처리 및 결과 렌더링
│   ├── templates/stocks/       # 결과 화면 템플릿
│   └── services/
│       ├── collector.py        # 토스증권 검색 및 댓글 수집
│       ├── preprocessor.py     # 댓글 정제 및 부적절 댓글 필터링
│       ├── augmenter.py        # LLM 기반 댓글 증강
│       ├── summarizer.py       # LLM 기반 댓글 요약
│       └── pipeline.py         # 전체 처리 파이프라인
├── 05_toss_practice/           # 실습용 단독 스크립트와 SQLite 저장 예제
├── chromedriver-win64/         # Selenium ChromeDriver
└── edgedriver_win64/           # EdgeDriver
```

## 실행 환경

- Python 3.11 이상 권장
- Google Chrome
- `chromedriver-win64/chromedriver.exe`
- Windows PowerShell 기준으로 작성

## 설치 방법

가상환경을 만들고 의존성을 설치합니다.

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

## 환경 변수

프로젝트 루트에 `.env` 파일을 만들고 필요한 값을 설정합니다.

```env
DJANGO_SECRET_KEY=dev-only-secret-key
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=*

OPENAI_API_KEY=your_openai_api_key
MODEL=gpt-5-nano

GMS_API_KEY=your_gms_or_openai_compatible_key
GMS_BASE_URL=https://your-gms-compatible-endpoint
GMS_MODEL=gpt-5-nano

SELENIUM_HEADLESS=0
```

LLM API 키가 없으면 일부 LLM 단계는 건너뛰거나 fallback 결과를 반환합니다. 댓글 수집 자체는 Selenium과 ChromeDriver가 정상 동작하면 실행할 수 있습니다.

## Django 웹 앱 실행

```powershell
python manage.py runserver
```

브라우저에서 아래 주소로 접속합니다.

```text
http://127.0.0.1:8000/
```

화면에서 회사명을 입력하면 다음 순서로 처리됩니다.

1. 토스증권 메인 페이지 접속
2. 입력한 회사명으로 종목 검색
3. 검색 결과의 상위 종목 선택
4. 종목 커뮤니티 페이지 이동
5. 댓글 최대 20개 수집
6. 부적절 댓글 필터링 및 규칙 기반 전처리
7. LLM 기반 댓글 증강
8. LLM 기반 요약, 키워드, 인사이트, 주의사항 생성
9. 결과 화면 출력

## 실습 스크립트

루트의 `010_static_page.py`, `021_dynamic_page.py` 등은 정적/동적 페이지 크롤링을 연습하기 위한 파일입니다.

`05_toss_practice` 폴더의 스크립트는 토스증권 댓글 수집 과정을 단계적으로 발전시킨 예제입니다. 특히 `080_toss_practice.py`는 댓글 수집, 전처리, LLM 증강, SQLite 저장까지 포함합니다.

```powershell
python .\05_toss_practice\080_toss_practice.py
```

실습 스크립트 실행 결과는 `05_toss_practice/toss_comments.db`에 저장됩니다.

## 데이터 처리 흐름

```text
사용자 입력
  ↓
collector.collect_stock_comments()
  ↓
preprocessor.preprocess_comments()
  ↓
augmenter.augment_comments()
  ↓
summarizer.summarize_comments()
  ↓
pipeline.run_stock_comment_pipeline()
  ↓
Django template 렌더링
```

## 주의사항

- 토스증권 웹 페이지 구조가 바뀌면 CSS selector 또는 검색 로직 수정이 필요할 수 있습니다.
- Selenium 자동화는 브라우저, 드라이버, 네트워크 상태에 영향을 받습니다.
- 커뮤니티 댓글은 투자 판단의 근거가 아니라 참고용 비정형 데이터입니다.
- LLM 요약과 증강 결과는 사실 검증된 투자 정보가 아니므로 그대로 신뢰하면 안 됩니다.
- `.env`, `db.sqlite3`, 로그 파일, 가상환경은 `.gitignore`에 의해 Git 추적에서 제외됩니다.

## 문제 해결

- 브라우저가 실행되지 않으면 Chrome 버전과 `chromedriver.exe` 버전이 호환되는지 확인합니다.
- 서버는 뜨지만 수집이 실패하면 토스증권 검색창 placeholder 또는 댓글 영역 selector가 변경되었을 수 있습니다.
- 한글이 깨져 보이면 파일 인코딩이 UTF-8인지 확인합니다.
- LLM 단계가 동작하지 않으면 `.env`의 API 키, 모델명, `GMS_BASE_URL` 값을 확인합니다.
