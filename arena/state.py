import operator
from typing import Annotated, Any, Dict, List, Literal, TypedDict

class DebateTurn(TypedDict, total=False):
    autor: Literal["Pró", "Contra", "Pro", "Con"]
    rodada: int
    argumento: str
    author: Literal["Pro", "Con", "Pró", "Contra"]
    round: int
    argument: str

class JudgeVote(TypedDict, total=False):
    juiz: str
    voto: str
    justificativa: str
    judge: str
    vote: str
    rationale: str

class ArenaState(TypedDict, total=False):
    claim: str
    debate_history: Annotated[List[Dict[str, Any]], operator.add]
    current_round: int
    jury_votes: List[Dict[str, Any]]
    final_verdict: str
    human_approved: bool
