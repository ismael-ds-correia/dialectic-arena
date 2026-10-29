import json
from typing import Any, Dict, List, Literal
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from arena.state import ArenaState
from arena.tools import web_search_tool

# Instância do modelo Groq
# Usando max_retries para contornar limites transitórios de TPM/RPM da Groq
llm = ChatGroq(model_name="openai/gpt-oss-120b", temperature=0.7, max_retries=5)

# Prompts de Sistema
AGENTE_PRO_SYSTEM = (
    "Você é um advogado de defesa em um debate formal. Seu objetivo é defender veementemente a alegação apresentada."
    "Use a ferramenta de busca para encontrar fatos e evidências favoráveis."
    "Analise criticamente as tréplicas do opositor e rebatendo ponto a ponto."
    "Argumente em texto corrido, sem tabelas ou bullets."
    "Seja convincente, estruturado e fundamentado."
    "Use até 400 palavras."
)

AGENTE_CONTRA_SYSTEM = (
    "Você é um promotor de acusação e cético em um debate formal. Seu objetivo é refutar a alegação apresentada."
    "Use a ferramenta de busca para encontrar checagens de fatos, contraprovas e inconsistências lógicas."
    "Analise as falas do Agente Pró e desconstrututurar os argumentos dele. "
    "Argumente em texto corrido, sem tabelas ou bullets."
    "Seja rigoroso e incisivo."
    "Use até 400 palavras."
)

AGENTE_JUIZ_SYSTEM = (
    "Você é um Juiz Supremo e perito analista de dados. Sua função é julgar um debate de forma implacável e estritamente técnica.\n"
    "Regras Inegociáveis de Julgamento:\n"
    "1. Avalie a confiabilidade e veracidade das fontes citadas pelo Agente Pró e pelo Agente Contra.\n"
    "2. É PROIBIDO declarar o resultado como 'Inconclusivo' ou 'Empate'. Você DEVE escolher apenas entre 'Procedente' (a alegação se sustenta com fatos) ou 'Improcedente' (a alegação foi refutada ou carece de evidências sólidas).\n"
    "3. Retorne sua decisão estritamente no formato estruturado contendo as chaves: veredicto ('Procedente' ou 'Improcedente') e justificativa."
)

# Modelo Pydantic para saída estruturada do Juiz Único
class ParecerJuizModel(BaseModel):
    veredicto: Literal["Procedente", "Improcedente"] = Field(
        description="Resultado obrigatório: apenas 'Procedente' ou 'Improcedente'"
    )
    justificativa: str = Field(description="Fundamentação técnica e minuciosa da decisão")

def agente_pro(state: ArenaState) -> dict:
    rodada_atual = state.get("rodada_atual") or state.get("current_round", 1)
    print(f"[*] [Agente Pró] Pesquisando evidências e elaborando defesa (Rodada {rodada_atual})...", flush=True)
    alegacao = state.get("alegacao") or state.get("claim", "")
    historico = state.get("historico_debate") or state.get("debate_history", [])

    ultimo_argumento_contra = None
    for turno in reversed(historico):
        autor = turno.get("autor") or turno.get("author")
        if autor in ["Contra", "Con"]:
            ultimo_argumento_contra = turno.get("argumento") or turno.get("argument")
            break

    # Formular query de busca
    if ultimo_argumento_contra:
        query = f"evidências para defender {alegacao} refutar {ultimo_argumento_contra[:100]}"
    else:
        query = f"fatos e argumentos a favor de {alegacao}"

    res_busca = web_search_tool.invoke(query)
    evidencias_str = str(res_busca)

    prompt_usuario = (
        f"Alegação: {alegacao}\n"
        f"Evidências encontradas: {evidencias_str}\n\n"
        "Apresente seus argumentos de defesa com base nessas evidências."
    )
    if ultimo_argumento_contra:
        prompt_usuario = f"Contestação anterior: {ultimo_argumento_contra}\n" + prompt_usuario

    mensagens = [
        SystemMessage(content=AGENTE_PRO_SYSTEM),
        HumanMessage(content=prompt_usuario),
    ]

    resposta = llm.invoke(mensagens)

    return {
        "historico_debate": [
            {
                "autor": "Pró",
                "rodada": rodada_atual,
                "argumento": resposta.content,
            }
        ]
    }

def agente_contra(state: ArenaState) -> dict:
    rodada_atual = state.get("rodada_atual") or state.get("current_round", 1)
    print(f"[*] [Agente Contra] Pesquisando contraprovas e refutando (Rodada {rodada_atual})...", flush=True)
    alegacao = state.get("alegacao") or state.get("claim", "")
    historico = state.get("historico_debate") or state.get("debate_history", [])

    ultimo_argumento_pro = ""
    for turno in reversed(historico):
        autor = turno.get("autor") or turno.get("author")
        if autor in ["Pró", "Pro"]:
            ultimo_argumento_pro = turno.get("argumento") or turno.get("argument", "")
            break

    query = f"checagem de fatos contraprovas críticas '{alegacao}' '{ultimo_argumento_pro[:120]}'"
    evidencias = web_search_tool.invoke(query)

    prompt_contexto = (
        f"Alegação em debate: {alegacao}\n\n"
        f"Último argumento do Agente Pró:\n{ultimo_argumento_pro}\n\n"
        f"Evidências e contraprovas pesquisadas:\n{evidencias}\n\n"
        "Construa sua refutação com base nas evidências e lógica rigorosa."
    )

    mensagens = [
        SystemMessage(content=AGENTE_CONTRA_SYSTEM),
        HumanMessage(content=prompt_contexto),
    ]

    resposta = llm.invoke(mensagens)

    return {
        "historico_debate": [
            {
                "autor": "Contra",
                "rodada": rodada_atual,
                "argumento": resposta.content,
            }
        ],
        "rodada_atual": rodada_atual + 1,
    }

def agente_juiz(state: ArenaState) -> dict:
    print("[*] [Juiz Técnico] Avaliando confiabilidade dos dados e julgando o debate...", flush=True)
    alegacao = state.get("alegacao") or state.get("claim", "")
    historico = state.get("historico_debate") or state.get("debate_history", [])

    debate_formatado = []
    for turno in historico:
        autor = turno.get("autor") or turno.get("author")
        rodada = turno.get("rodada") or turno.get("round")
        argumento = turno.get("argumento") or turno.get("argument")
        debate_formatado.append(f"[Rodada {rodada} - {autor}]:\n{argumento}")

    historico_texto = "\n\n".join(debate_formatado)

    prompt_juiz = (
        f"Alegação em Julgamento: {alegacao}\n\n"
        f"Histórico Completo do Debate:\n{historico_texto}\n\n"
        "Aplique as regras inegociáveis e emita seu parecer definitivo (Procedente ou Improcedente)."
    )

    mensagens = [
        SystemMessage(content=AGENTE_JUIZ_SYSTEM),
        HumanMessage(content=prompt_juiz),
    ]

    juiz_llm = llm.with_structured_output(ParecerJuizModel)
    try:
        resultado = juiz_llm.invoke(mensagens)
        parecer = resultado.model_dump()
    except Exception:
        # Fallback de segurança garantindo o formato estrito
        parecer = {
            "veredicto": "Improcedente",
            "justificativa": "Falha na extração estruturada do parecer; pelo ônus da prova, considerou-se improcedente."
        }

    return {"parecer_juiz": parecer}
