import json
import os
import re
from dataclasses import dataclass

from langchain.chat_models import init_chat_model


@dataclass
class PreprocessResult:
    original_comments: list[str]
    llm_filtered_comments: list[str]
    cleaned_comments: list[str]
    inappropriate_comments: list[str]
    removed_comments: list[dict]
    settings: dict
    steps: list[str]


def call_llm(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("MODEL") or os.getenv("model") or "gpt-5-nano"

    if not api_key:
        return None

    llm = init_chat_model(model, model_provider="openai", api_key=api_key)
    response = llm.invoke(
        [
            {
                "role": "user",
                "content": prompt,
            },
        ]
    )
    return response.content


def filter_inappropriate_comments(comments, steps):
    if not comments:
        return [], []

    numbered_comments = "\n".join(
        f"{index}. {comment}" for index, comment in enumerate(comments)
    )
    prompt = f"""
다음 댓글 목록에서 부적절한 댓글(욕설, 혐오, 비방, 선정성, 과도한 비난 등)의 번호(0부터 시작)만 JSON 배열로 알려줘.
응답은 반드시 JSON 배열만 반환해. 예: [0, 2, 5] 또는 []

댓글 목록:
{numbered_comments}
"""

    steps.append("LLM API를 호출해 부적절한 댓글 번호를 판별했습니다.")
    response_text = call_llm(prompt)
    if response_text is None:
        steps.append("OPENAI_API_KEY가 없어 LLM 필터를 건너뛰었습니다.")
        return list(comments), []

    try:
        remove_indexes = json.loads(response_text.strip())
        remove_indexes = {
            int(index)
            for index in remove_indexes
            if isinstance(index, (int, float)) and 0 <= int(index) < len(comments)
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        steps.append("LLM 응답이 JSON 배열이 아니어서 부적절 댓글 제거를 건너뛰었습니다.")
        return list(comments), []

    removed_comments = [
        comment for index, comment in enumerate(comments) if index in remove_indexes
    ]
    filtered_comments = [
        comment for index, comment in enumerate(comments) if index not in remove_indexes
    ]
    steps.append(f"LLM 필터 결과 부적절 댓글 {len(removed_comments)}개를 제거했습니다.")
    return filtered_comments, removed_comments


def normalize_comment(comment):
    cleaned = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", comment)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_meaningless_comment(comment):
    compact = re.sub(r"\s+", "", comment)

    if not compact:
        return True
    if re.fullmatch(r"\d+", compact):
        return True
    if re.fullmatch(r"[ㅋㅎㅠㅜ]+", compact):
        return True
    if re.fullmatch(r"(.)\1{2,}", compact):
        return True
    if compact.lower() in {"none", "null", "nan"}:
        return True

    return False


def preprocess_comments(comments, min_length=3, max_length=120):
    steps = [f"원본 댓글 {len(comments)}개를 전처리 대상으로 받았습니다."]
    llm_filtered_comments, inappropriate_comments = filter_inappropriate_comments(
        comments,
        steps,
    )

    cleaned_comments = []
    removed_comments = []
    seen = set()

    for comment in llm_filtered_comments:
        original = "" if comment is None else str(comment).strip()
        cleaned = normalize_comment(original)
        reason = None

        if not original:
            reason = "결측치 또는 공백"
        elif len(cleaned) < min_length:
            reason = "길이가 너무 짧음"
        elif len(cleaned) > max_length:
            reason = "길이가 너무 김"
        elif is_meaningless_comment(cleaned):
            reason = "의미 없는 패턴"
        elif cleaned in seen:
            reason = "중복 댓글"

        if reason:
            removed_comments.append(
                {
                    "reason": reason,
                    "original": original,
                    "cleaned": cleaned,
                }
            )
            continue

        seen.add(cleaned)
        cleaned_comments.append(cleaned)

    steps.append(f"규칙 기반 전처리로 댓글 {len(removed_comments)}개를 제거했습니다.")
    steps.append(f"최종 정제 댓글 {len(cleaned_comments)}개를 생성했습니다.")

    return PreprocessResult(
        original_comments=list(comments),
        llm_filtered_comments=llm_filtered_comments,
        cleaned_comments=cleaned_comments,
        inappropriate_comments=inappropriate_comments,
        removed_comments=removed_comments,
        settings={
            "min_length": min_length,
            "max_length": max_length,
            "rules": [
                "결측치 제거",
                "너무 짧거나 긴 댓글 제거",
                "특수문자 정리",
                "ㅋㅋ, ㅎㅎ, 숫자만 있는 댓글 등 의미 없는 패턴 제거",
                "LLM API 기반 부적절 댓글 제거",
            ],
        },
        steps=steps,
    )
