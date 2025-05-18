# votesys/app/models.py

from typing import List
from pydantic_xml import BaseXmlModel, attr, element

class Option(BaseXmlModel, tag="option"):
    """
    <option id="...">
      <text>...</text>
      <votes>...</votes>
    </option>
    """
    # XML attribute olarak id
    id: int = attr(name="id")
    # XML child elementi <text>
    text: str = element(name="text")
    # XML child elementi <votes>
    votes: int = element(name="votes")

class Poll(BaseXmlModel, tag="poll"):
    """
    <poll id="...">
      <question>...</question>
      <options>
        <option>...</option>
        ...
      </options>
    </poll>
    """
    # XML attribute olarak anket id’si
    id: int = attr(name="id")
    # XML child elementi <question>
    question: str = element(name="question")
    # <options> içindeki <option> elementlerini liste olarak al
    options: List[Option] = element(tag="option", wrapped="options")
