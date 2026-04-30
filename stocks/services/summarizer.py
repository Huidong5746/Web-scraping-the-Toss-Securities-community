import json
import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class SummaryResult:
    summary: str
    keywords: list[str]
    insights: list[str]
    warnings: list[str]
    steps: list[str]
    available: bool


def get_summary_client():
    api_key = os.getenv("GMS_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("GMS_BASE_URL")

    if not api_key:
        return None

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)

    return OpenAI(api_key=api_key)


def fallback_summary(comments, reason):
    keywords = []
    for comment in comments:
        for token in str(comment).split():
            token = token.strip()
            if len(token) >= 2 and token not in keywords:
                keywords.append(token)
            if len(keywords) >= 5:
                break
        if len(keywords) >= 5:
            break

    return SummaryResult(
        summary=reason,
        keywords=keywords,
        insights=[
            "LLM 요약을 사용할 수 없어 수집된 전체 댓글 목록을 직접 확인해야 합니다.",
            "댓글 수가 적거나 API 설정이 없으면 자동 인사이트의 신뢰도가 낮습니다.",
        ],
        warnings=[
            "커뮤니티 댓글은 투자 판단의 근거가 아니라 참고용 비정형 데이터입니다.",
        ],
        steps=[reason],
        available=False,
    )


def summarize_comments(comments, stock_name=""):
    steps = []

    if not comments:
        return SummaryResult(
            summary="요약할 전체 댓글 데이터가 없습니다.",
            keywords=[],
            insights=[
                "커뮤니티 댓글이 수집되지 않았습니다.",
                "회사명을 더 구체적으로 입력하거나 잠시 후 다시 시도해 주세요.",
            ],
            warnings=[
                "데이터가 없으므로 분위기나 의미 있는 정보를 판단할 수 없습니다.",
            ],
            steps=["수집된 전체 댓글이 없어 요약 단계를 건너뛰었습니다."],
            available=False,
        )

    client = get_summary_client()
    if client is None:
        return fallback_summary(
            comments,
            "GMS_API_KEY가 없어 LLM 요약을 건너뛰었습니다.",
        )

    model = os.getenv("GMS_MODEL") or os.getenv("MODEL") or os.getenv("model") or "gpt-5-nano"
    prompt = f"""
아래는 토스증권 {stock_name} 커뮤니티에서 수집한 전체 원본 댓글입니다.
전체 댓글 데이터에서 주요 내용을 요약해줘.

반드시 아래 JSON 객체 형식만 반환해.
{{
  "summary": "전체 분위기 한두 문장",
  "keywords": ["키워드1", "키워드2", "키워드3"],
  "insights": ["인사이트1", "인사이트2", "인사이트3"],
  "warnings": ["주의사항1"]
}}

주의:
- 댓글에 없는 사실, 수치, 가격 전망을 만들지 마.
- 투자 조언처럼 단정하지 마.
- 데이터가 부족하면 부족하다고 말해.

댓글:
{json.dumps(comments, ensure_ascii=False)}
"""

    steps.append(f"GMS LLM API로 전체 댓글 {len(comments)}개 요약을 요청했습니다.")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
        response_text = response.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = response_text.removeprefix("```json").removeprefix("```")
            response_text = response_text.removesuffix("```").strip()
        payload = json.loads(response_text)
    except Exception as exc:
        return fallback_summary(
            comments,
            f"LLM 요약 생성 중 오류가 발생했습니다: {exc}",
        )

    steps.append("요약, 키워드, 인사이트, 주의사항을 생성했습니다.")
    return SummaryResult(
        summary=str(payload.get("summary", "")).strip(),
        keywords=[str(item).strip() for item in payload.get("keywords", []) if str(item).strip()],
        insights=[str(item).strip() for item in payload.get("insights", []) if str(item).strip()],
        warnings=[str(item).strip() for item in payload.get("warnings", []) if str(item).strip()],
        steps=steps,
        available=True,
    )
