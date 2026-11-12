# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.pii_redaction import redact_pii


def test_redacts_email():
    assert redact_pii("email me at jane.doe@example.com please") == "email me at [email] please"


def test_redacts_phone_formats():
    assert redact_pii("call 555-123-4567") == "call [phone]"
    assert redact_pii("call (555) 123-4567") == "call [phone]"
    assert redact_pii("call +1 555 123 4567") == "call [phone]"


def test_redacts_card_formats():
    assert redact_pii("my card is L30-AB12-CD34") == "my card is [card]"
    assert redact_pii("card LSC123456") == "card [card]"
    assert redact_pii("temp TMP-WXYZ-1234") == "temp [card]"
    assert redact_pii("number AB1CD-45678") == "number [card]"  # 5 alnum + hyphen + 5 digits shape
    assert redact_pii("lowercase card l30-ab12-cd34") == "lowercase card [card]"
    assert redact_pii("prod card 12345-67890") == "prod card [card]"  # all-digit, guards email->card->phone order


def test_leaves_ordinary_text_untouched():
    assert redact_pii("how do I renew my books") == "how do I renew my books"
    assert redact_pii("I have 3 books due in 2026") == "I have 3 books due in 2026"


def test_handles_empty():
    assert redact_pii("") == ""
