# votesys/app/xml_utils.py

import os
from typing import List, Optional
from lxml import etree
from filelock import FileLock
from .models import Poll, Option

BASE_DIR    = os.path.dirname(__file__)
SCHEMA_PATH = os.path.join(BASE_DIR, "poll.xsd")
DATA_DIR    = os.path.join(BASE_DIR, "data")
LOCK_PATH   = os.path.join(BASE_DIR, "data.lock")

os.makedirs(DATA_DIR, exist_ok=True)

with open(SCHEMA_PATH, "rb") as f:
    schema_doc = etree.XML(f.read())
XML_SCHEMA = etree.XMLSchema(schema_doc)


def validate_xml(xml_bytes: bytes) -> None:
    doc = etree.fromstring(xml_bytes)
    XML_SCHEMA.assertValid(doc)


def _poll_filepath(poll_id: int) -> str:
    return os.path.join(DATA_DIR, f"poll_{poll_id}.xml")


def list_poll_ids() -> List[int]:
    ids: List[int] = []
    for fname in os.listdir(DATA_DIR):
        if fname.startswith("poll_") and fname.endswith(".xml"):
            try:
                ids.append(int(fname[5:-4]))
            except ValueError:
                pass
    return sorted(ids)


def write_poll(poll: Poll) -> None:
    """
    Poll -> XML dosyası. owner attribute da eklenir.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    # Kök element: id ve owner
    attrs = {"id": str(poll.id)}
    if poll.owner:
        attrs["owner"] = poll.owner
    root = etree.Element("poll", **attrs)

    # question
    etree.SubElement(root, "question").text = poll.question

    # options
    opts_wrap = etree.SubElement(root, "options")
    for opt in poll.options:
        o = etree.SubElement(opts_wrap, "option", id=str(opt.id))
        etree.SubElement(o, "text").text  = opt.text
        etree.SubElement(o, "votes").text = str(opt.votes)

    xml_bytes = etree.tostring(root, xml_declaration=True, encoding="UTF-8")
    validate_xml(xml_bytes)

    with FileLock(LOCK_PATH):
        with open(_poll_filepath(poll.id), "wb") as f:
            f.write(xml_bytes)


def read_poll(poll_id: int) -> Poll:
    """
    XML dosyasını oku. Önce pydantic-xml, patlarsa manuel parse.
    owner attribute alınır.
    """
    path = _poll_filepath(poll_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Anket bulunamadı: {path}")

    with FileLock(LOCK_PATH):
        xml_bytes = open(path, "rb").read()

    try:
        validate_xml(xml_bytes)
    except Exception as ve:
        print(f"[xml_utils] XSD uyarı: {ve}")

    # pydantic-xml ile dene
    try:
        return Poll.from_xml(xml_bytes)
    except Exception as pe:
        print(f"[xml_utils] pydantic_xml hata: {pe}, manuel parse...")

    # Manuel parse
    root = etree.fromstring(xml_bytes)
    owner = root.get("owner")

    question = root.findtext("question", "").strip()

    opts: List[Option] = []
    for oe in root.findall("./options/option"):
        opts.append(
            Option(
                id=int(oe.get("id")),
                text=oe.findtext("text", "").strip(),
                votes=int(oe.findtext("votes", "0")),
            )
        )

    return Poll(id=poll_id, owner=owner, question=question, options=opts)
