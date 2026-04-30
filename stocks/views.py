from django.shortcuts import render

from .forms import StockSearchForm
from .services.collector import StockSearchNotFound
from .services.pipeline import run_stock_comment_pipeline


def index(request):
    result = None
    error_message = None

    if request.method == "POST":
        form = StockSearchForm(request.POST)
        if form.is_valid():
            company_name = form.cleaned_data["company_name"].strip()
            if company_name:
                try:
                    result = run_stock_comment_pipeline(company_name)
                except StockSearchNotFound as exc:
                    error_message = str(exc)
                except Exception as exc:
                    error_message = f"처리 중 오류가 발생했습니다: {exc}"
    else:
        form = StockSearchForm()

    return render(
        request,
        "stocks/index.html",
        {
            "form": form,
            "result": result,
            "error_message": error_message,
        },
    )
