import operator
from typing import Annotated, Any, Dict, List, Literal, TypedDict


class DebateTurn(TypedDict, total=False):
    # Campos em Português
    autor: Literal["Pró", "Contra", "Pro", "Con"]
    rodada: int
    argumento: str

    # Campos em Inglês
    author: Literal["Pro", "Con", "Pró", "Contra"]
    round: int
    argument: str


class JudgeVote(TypedDict, total=False):
    # Campos em Português
    juiz: str
    voto: str
    justificativa: str

    # Campos em Inglês
    judge: str
    vote: str
    rationale: str


class ArenaState(TypedDict, total=False):
    # Campos em Português
    alegacao: str
    historico_debate: Annotated[List[Dict[str, Any]], operator.add]
    rodada_atual: int
    votos_juri: List[Dict[str, Any]]
    veredicto_final: str
    homologado_por_humano: bool
    aprovado_humano: bool

    # Campos em Inglês (compatibilidade)
    claim: str
    debate_history: Annotated[List[Dict[str, Any]], operator.add]
    current_round: int
    jury_votes: List[Dict[str, Any]]
    final_verdict: str
    human_approved: bool
