from collections import namedtuple
from typing import Any

scalar_types: Any
integer_types: Any
basestring = str

_Term = namedtuple('Term', 'tag data args span')

class Term(_Term):
    def __new__(cls, tag: Any, data: Any, args: Any, span: Any): ...
    def __iter__(self) -> Any: ...
    def __eq__(self, other: Any) -> Any: ...
    def __hash__(self) -> Any: ...
    def withSpan(self, span: Any): ...
    def build(self, builder: Any): ...
    def __cmp__(self, other: Any): ...
    def __int__(self): ...
    def __float__(self): ...
    def withoutArgs(self): ...
    def asFunctor(self): ...

class Tag:
    name: Any = ...
    def __init__(self, name: Any) -> None: ...
    def __eq__(self, other: Any) -> Any: ...
    def __ne__(self, other: Any) -> Any: ...
    def __hash__(self) -> Any: ...

def coerceToTerm(val: Any): ...

class TermMaker:
    def __getattr__(self, name: Any): ...

termMaker: Any