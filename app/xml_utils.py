# votesys/app/xml_utils.py

import os
from lxml import etree
from filelock import FileLock
from typing import List
from .models import Poll

# Sabit yollar
BASE_DIR    = os.path.dirname(__file__)
SCHEMA_PATH = os.path.join(BASE_DIR, "poll.xsd")
DATA_DIR    = os.path.join(BASE_DIR, "data")
LOCK_PATH   = os.path.join(BASE_DIR, "data.lock")

# XSD şemasını yükleyip bir kez derleyelim
with open(SCHEMA_PATH, "rb") as f:
    schema_doc = etree.XML(f.read())
XML_SCHEMA = etree.XMLSchema(schema_doc)

def validate_xml(xml_bytes: bytes) -> None:
    """
    Gelen XML içeriğini XSD'ye göre doğrular.
    Geçersizse etree.XMLSchemaError fırlatır.
    """
    doc = etree.fromstring(xml_bytes)
    XML_SCHEMA.assertValid(doc)

def _poll_filepath(poll_id: int) -> str:
    """ poll_{id}.xml dosyasının tam yolunu döndürür """
    return os.path.join(DATA_DIR, f"poll_{poll_id}.xml")

def read_poll(poll_id: int) -> Poll:
    """
    Belirli bir anketi XML dosyasından okur,
    önce kilitlenir (FileLock), sonra XSD doğrulaması yapılır,
    en sonra Poll modeline parse edilir.
    """
    path = _poll_filepath(poll_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Anket bulunamadı: {path}")

    with FileLock(LOCK_PATH):
        xml_bytes = open(path, "rb").read()

    validate_xml(xml_bytes)
    return Poll.from_xml(xml_bytes)

def write_poll(poll: Poll) -> None:
    """
    Poll objesini manuel olarak XSD'ye uygun XML'e dönüştürür,
    doğrular, kilitlenip yazar.
    """
    # 1. Kök elementi ve attribute
    root = etree.Element("poll", id=str(poll.id))

    # 2. <question>
    q = etree.SubElement(root, "question")
    q.text = poll.question

    # 3. <options> wrapper
    opts_wr = etree.SubElement(root, "options")
    for opt in poll.options:
        opt_el = etree.SubElement(opts_wr, "option", id=str(opt.id))
        # <text>
        text_el = etree.SubElement(opt_el, "text")
        text_el.text = opt.text
        # <votes>
        votes_el = etree.SubElement(opt_el, "votes")
        votes_el.text = str(opt.votes)

    # 4. Byte dizisine çevir
    xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8")

    # 5. Son kez XSD ile doğrula
    validate_xml(xml_bytes)

    # 6. FileLock ile kilitleyip diske yaz
    with FileLock(LOCK_PATH):
        with open(_poll_filepath(poll.id), "wb") as f:
            f.write(xml_bytes)

def list_poll_ids() -> List[int]:
    """
    data/ klasöründeki poll_*.xml dosyalarını tarayıp
    ID listesi döner. Örn: [1, 2, 5]
    """
    ids: List[int] = []
    for fname in os.listdir(DATA_DIR):
        if fname.startswith("poll_") and fname.endswith(".xml"):
            try:
                idx = int(fname[len("poll_"):-4])
                ids.append(idx)
            except ValueError:
                continue
    return sorted(ids)
