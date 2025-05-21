# votesys/app/models.py

from typing import List, Optional
from pydantic_xml import BaseXmlModel, attr, element

class Option(BaseXmlModel, tag="option"):
    """
    <option id="...">
      <text>...</text>
      <votes>...</votes>
    </option>
    """
    id: int    = attr(name="id")
    text: str  = element(name="text")
    votes: int = element(name="votes")

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
    id: int                 = attr(name="id")
    owner: Optional[str]    = attr(name="owner", default=None)
    question: str           = element(name="question")
    options: List[Option]   = element(tag="option", wrapped="options")
