# XML tabanlı anket verisini işlemek için gerekli tipler ve yardımcı sınıflar
from typing import List, Optional
from pydantic_xml import BaseXmlModel, attr, element

# ————————— Anket Seçeneği Modeli —————————
# Bu model <option> elemanını temsil eder.
# Seçenek metni ve o ana kadar aldığı oy sayısını tutar.
class Option(BaseXmlModel, tag="option"):
    """
    <option id="...">
      <text>...</text>
      <votes>...</votes>
    </option>
    """
    # Seçeneğin benzersiz kimliği (XML attribute)
    id: int    = attr(name="id")
    # Seçenek açıklaması (XML elementi)
    text: str  = element(name="text")
    # O ana kadar verilen oy sayısı (XML elementi)
    votes: int = element(name="votes")

# ————————— Anket (Poll) Modeli —————————
# Bu model <poll> elemanını temsil eder.
# Soruyu, sahibi ve seçenek listesini XML üzerinde tanımlar.
class Poll(BaseXmlModel, tag="poll"):
    """
    <poll id="..." owner="...">
      <question>...</question>
      <options>
        <option>...</option>
        ...
      </options>
    </poll>
    """
    # Anketin benzersiz kimliği (XML attribute)
    id: int                 = attr(name="id")
    # Anketi oluşturan kullanıcı adı (XML attribute)
    owner: Optional[str]    = attr(name="owner", default=None)
    # Anket sorusu metni (XML elementi)
    question: str           = element(name="question")
    # Anket seçeneklerinin listesi (birden çok <option>)
    options: List[Option]   = element(tag="option", wrapped="options")
