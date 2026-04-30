import ast
import json
import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class AugmentationResult:
    augmented_comments: list[str]
    augmented_pairs: list[dict]
    integrated_comments: list[str]
    steps: list[str]
    provider: str
    model: str


def get_gms_client():
    api_key = os.getenv("GMS_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("GMS_BASE_URL")

    if not api_key:
        return None

    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)

    return OpenAI(api_key=api_key)


def parse_comment_list(response_text):
    response_text = response_text.strip()
    if response_text.startswith("```"):
        response_text = response_text.removeprefix("```json").removeprefix("```")
        response_text = response_text.removesuffix("```").strip()

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        parsed = ast.literal_eval(response_text)

    if not isinstance(parsed, list):
        return []

    return [str(item).strip() for item in parsed if str(item).strip()]


def augment_comments(comments, stock_name="", max_items=10):
    """GMS LLM API로 정제 댓글을 증강한다."""
    steps = []
    model = os.getenv("GMS_MODEL") or os.getenv("MODEL") or os.getenv("model") or "gpt-5-nano"
    provider = "GMS LLM API"

    if not comments:
        steps.append("정제 댓글이 없어 증강 단계를 건너뛰었습니다.")
        return AugmentationResult([], [], [], steps, provider, model)

    client = get_gms_client()
    if client is None:
        steps.append("GMS_API_KEY가 없어 증강 단계를 건너뛰었습니다.")
        return AugmentationResult([], [], list(comments), steps, provider, model)

    target_comments = comments[:max_items]
    prompt = f"""
아래는 토스증권 {stock_name} 커뮤니티에서 수집 후 정제한 댓글 목록입니다.
각 댓글의 의미와 투자 커뮤니티 문맥은 유지하면서 자연스러운 한국어 댓글로 1개씩 확장해서 다시 표현해줘.
원문에 없는 새로운 투자 판단, 사실, 수치, 가격 전망은 만들지 마.

반드시 JSON 배열만 반환해. 예: ["표현 1", "표현 2"]

댓글 목록:
{json.dumps(target_comments, ensure_ascii=False)}
"""

    steps.append(f"GMS LLM API로 정제 댓글 {len(target_comments)}개 증강을 요청했습니다.")

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
        augmented_comments = parse_comment_list(response_text)
    except Exception as exc:
        steps.append(f"GMS LLM API 증강 실패: {exc}")
        return AugmentationResult([], [], list(comments), steps, provider, model)

    augmented_comments = augmented_comments[: len(target_comments)]
    augmented_pairs = [
        {
            "source": source,
            "augmented": augmented,
        }
        for source, augmented in zip(target_comments, augmented_comments)
    ]
    integrated_comments = list(comments) + augmented_comments

    steps.append(f"증강 댓글 {len(augmented_comments)}개를 생성했습니다.")
    steps.append(f"정제 댓글과 증강 댓글을 합쳐 통합 데이터 {len(integrated_comments)}개를 구성했습니다.")
    return AugmentationResult(
        augmented_comments,
        augmented_pairs,
        integrated_comments,
        steps,
        provider,
        model,
    )
