import pytest
from app.services.matching import matching_service
from app.services.payment import payment_service

def test_check_mutual_match():
    # Mutual match with same chat language and matching age category
    seeker = {
        "id": 1,
        "nickname": "Alice",
        "gender": "female",
        "age": 20,
        "age_category": "adult",
        "find_gender": "male",
        "find_age_category": "adult",
        "age_from": 18,
        "age_to": 30,
        "topics": ["tech"],
        "chat_language": "en",
        "is_premium": False,
        "vip_only": False,
    }

    candidate = {
        "id": 2,
        "nickname": "Bob",
        "gender": "male",
        "age": 25,
        "age_category": "adult",
        "find_gender": "female",
        "find_age_category": "adult",
        "age_from": 18,
        "age_to": 30,
        "topics": ["tech"],
        "chat_language": "en",
        "is_premium": False,
        "vip_only": False,
    }

    # Matches
    assert matching_service._check_mutual_match(seeker, candidate) is True

    # Language mismatch
    candidate_diff_lang = dict(candidate, chat_language="ru")
    assert matching_service._check_mutual_match(seeker, candidate_diff_lang) is False

    # Age category mismatch
    candidate_diff_cat = dict(candidate, age_category="teen")
    assert matching_service._check_mutual_match(seeker, candidate_diff_cat) is False

def test_get_invoice_params():
    params = payment_service.get_invoice_params("premium_week")
    assert params is not None
    assert params["currency"] == "XTR"
