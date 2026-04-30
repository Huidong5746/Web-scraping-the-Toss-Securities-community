from dataclasses import asdict
from datetime import datetime

from django.utils import timezone

from .augmenter import augment_comments
from .collector import collect_stock_comments
from .preprocessor import preprocess_comments
from .summarizer import summarize_comments


def build_unified_dataset(original_comments, cleaned_comments, augmented_pairs):
    unified_dataset = []

    for index, comment in enumerate(original_comments, 1):
        unified_dataset.append(
            {
                "stage": "original",
                "stage_label": "원본",
                "source_index": index,
                "text": comment,
            }
        )

    for index, comment in enumerate(cleaned_comments, 1):
        unified_dataset.append(
            {
                "stage": "preprocessed",
                "stage_label": "전처리",
                "source_index": index,
                "text": comment,
            }
        )

    for index, item in enumerate(augmented_pairs, 1):
        unified_dataset.append(
            {
                "stage": "augmented",
                "stage_label": "증강",
                "source_index": index,
                "source_text": item["source"],
                "text": item["augmented"],
            }
        )

    return unified_dataset


def run_stock_comment_pipeline(company_name):
    started_at = timezone.localtime(timezone.now())
    collection = collect_stock_comments(company_name)
    preprocess = preprocess_comments(collection.original_comments)
    augmentation = augment_comments(
        preprocess.cleaned_comments,
        stock_name=collection.official_stock_name,
    )
    summary = summarize_comments(
        collection.original_comments,
        stock_name=collection.official_stock_name,
    )
    unified_dataset = build_unified_dataset(
        collection.original_comments,
        preprocess.cleaned_comments,
        augmentation.augmented_pairs,
    )

    return {
        "requested_at": started_at,
        "completed_at": timezone.localtime(timezone.now()),
        "requested_company_name": collection.requested_company_name,
        "official_stock_name": collection.official_stock_name,
        "stock_code": collection.stock_code,
        "detail_url": collection.detail_url,
        "community_url": collection.community_url,
        "original_comments": collection.original_comments,
        "cleaned_comments": preprocess.cleaned_comments,
        "augmented_comments": augmentation.augmented_comments,
        "augmented_pairs": augmentation.augmented_pairs,
        "integrated_comments": augmentation.integrated_comments,
        "unified_dataset": unified_dataset,
        "inappropriate_comments": preprocess.inappropriate_comments,
        "removed_comments": preprocess.removed_comments,
        "preprocess_settings": preprocess.settings,
        "collection_steps": collection.steps,
        "preprocess_steps": preprocess.steps,
        "augmentation_steps": augmentation.steps,
        "augmentation_provider": augmentation.provider,
        "augmentation_model": augmentation.model,
        "summary": summary.summary,
        "summary_keywords": summary.keywords,
        "summary_insights": summary.insights,
        "summary_warnings": summary.warnings,
        "summary_steps": summary.steps,
        "summary_available": summary.available,
        "notices": build_notices(collection.original_comments, preprocess.cleaned_comments),
        "augmentation_ready_data": {
            "stock_name": collection.official_stock_name,
            "comments": preprocess.cleaned_comments,
            "augmented_comments": augmentation.augmented_comments,
            "integrated_comments": augmentation.integrated_comments,
            "unified_dataset": unified_dataset,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
        "raw": {
            "collection": asdict(collection),
            "preprocess": asdict(preprocess),
            "augmentation": asdict(augmentation),
            "summary": asdict(summary),
        },
    }


def build_notices(original_comments, cleaned_comments):
    notices = []

    if not original_comments:
        notices.append(
            "커뮤니티 댓글이 수집되지 않았습니다. 회사명이 정확한지 확인하거나 잠시 후 다시 시도해 주세요."
        )
    elif not cleaned_comments:
        notices.append(
            "수집 댓글은 있었지만 전처리 후 남은 데이터가 없습니다. 짧은 댓글, 중복, 무의미한 패턴이 많을 수 있습니다."
        )

    if len(cleaned_comments) < 3:
        notices.append(
            "정제 댓글 수가 적어 요약과 인사이트는 제한적으로 해석해야 합니다."
        )

    return notices
