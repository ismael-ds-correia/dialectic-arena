import operator
from typing import Annotated, List, Literal, TypedDict

class DebateTurn(TypedDict):
    author: Literal["Pro", "Con"]
    round: int
    argument: str

class JudgeVote(TypedDict):
    judge: str
    vote: str
    rationale: str

class ArenaState(TypedDict):
    claim: str
    debate_history: Annotated[List[DebateTurn], operator.add]
    current_round: int
    jury_votes: List[JudgeVote]
    final_verdict: str
    human_approved: bool
