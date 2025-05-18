# votesys/tests/test_xml.py

import pytest
from app.xml_utils import validate_xml
from app.models import Poll, Option

def test_validate_invalid_xml():
    bad = b"<poll><broken></poll>"
    with pytest.raises(Exception):
        validate_xml(bad)

def test_model_to_from_xml_cycle(tmp_path):
    # Önce bir Poll objesi oluştur
    poll = Poll(
        id=7,
        question="XML döngü testi?",
        options=[Option(id=1, text="X", votes=2)]
    )
    xml_bytes = poll.to_xml()
    # Validate (XSD ile uyumlu mu?)
    validate_xml(xml_bytes)
    # Tekrar objeye çevir
    restored = Poll.from_xml(xml_bytes)
    assert restored.id == poll.id
    assert restored.question == poll.question
    assert restored.options[0].votes == 2
