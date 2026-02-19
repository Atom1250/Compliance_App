import pytest

from app.regulatory.safe_eval import evaluate_expression


def test_safe_eval_accepts_structured_context_with_whitelist() -> None:
    context = {"company": {"reporting_year": 2026, "listed": True}}
    result = evaluate_expression(
        "company.reporting_year >= 2025 and company.listed == True",
        context=context,
        allowed_symbols={"company"},
    )
    assert result is True


def test_safe_eval_rejects_unknown_symbol() -> None:
    context = {"company": {"reporting_year": 2026}}
    with pytest.raises(ValueError, match="Unknown symbol: issuer"):
        evaluate_expression(
            "issuer.reporting_year >= 2025",
            context=context,
            allowed_symbols={"company"},
        )


def test_safe_eval_rejects_missing_attribute() -> None:
    context = {"company": {"reporting_year": 2026}}
    with pytest.raises(ValueError, match="Unknown attribute: listed"):
        evaluate_expression(
            "company.listed == True",
            context=context,
            allowed_symbols={"company"},
        )
