import json
from typing import Any, Dict, List

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from arena.state import ArenaState
from arena.tools import web_search_tool

# Instância do modelo Groq
llm = ChatGroq(model_name="openai/gpt-oss-120b", temperature=0.7)

# Prompts de Sistema
AGENTE_PRO_SYSTEM = (
    "Você é um advogado de defesa em um debate formal. Seu objetivo é defender veementemente a alegação apresentada."
    "Use a ferramenta de busca para encontrar fatos e evidências favoráveis."
    "Analise criticamente as tréplicas do opositor e rebatendo ponto a ponto."
    "Argumente em texto corrida, sem tabelas ou bullets."
    "Seja convincente, estruturado e fundamentado."
    "Use até 400 palavras."
)

AGENTE_CONTRA_SYSTEM = (
    "Você é um promotor de acusação e cético em um debate formal. Seu objetivo é refutar a alegação apresentada."
    "Use a ferramenta de busca para encontrar checagens de fatos, contraprovas e inconsistências lógicas."
    "Analise as falas do Agente Pró e desconstrututurar os argumentos dele."
    "Argumente em texto corrida, sem tabelas ou bullets."
    "Seja rigoroso e incisivo."
    "Use até 400 palavras."
)

JURI_SYSTEM = (
    "Você atua como um júri composto por 3 perfis distintos para julgar um debate:\n"
    "- Juiz 1 (Pró-Tendência): Tende a aceitar a alegação, exigindo fortes contraprovas para mudar de ideia.\n"
    "- Juiz 2 (Cético / Rigoroso): Exige evidências empíricas e checagem de fatos irrefutáveis.\n"
    "- Juiz 3 (Neutro / Imparcial): Avalia estritamente a coerência lógica e a qualidade dos dados apresentados por ambos os lados.\n"
    "Analise todo o histórico do debate e emita o voto individual de cada juiz no formato estruturado solicitado, "
    "contendo para cada um: juiz, voto ('Procedente', 'Improcedente' ou 'Inconclusivo') e justificativa."
)

# Modelos Pydantic para saída estruturada do Júri
class VotoJuizModel(BaseModel):
    juiz: str = Field(description="Identificação do juiz (ex: Juiz 1 (Pró-Tendência))")
    voto: str = Field(description="'Procedente', 'Improcedente' ou 'Inconclusivo'")
    justificativa: str = Field(description="Justificativa detalhada do voto com base no debate")

class VereditoJuriModel(BaseModel):
    votos: List[VotoJuizModel] = Field(description="Lista com os votos dos 3 juízes")

def agente_pro(state: ArenaState) -> dict:
    alegacao = state.get("alegacao") or state.get("claim", "")
    historico = state.get("historico_debate") or state.get("debate_history", [])
    rodada_atual = state.get("rodada_atual") or state.get("current_round", 1)

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

    # Executa a busca e garante conversão simples para string
    res_busca = web_search_tool.invoke(query)
    evidencias_str = str(res_busca)

    # Monta o prompt de forma limpa e direta
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
        ],
        "rodada_atual": rodada_atual + 1,
    }

def agente_contra(state: ArenaState) -> dict:
    alegacao = state.get("alegacao") or state.get("claim", "")
    historico = state.get("historico_debate") or state.get("debate_history", [])
    rodada_atual = state.get("rodada_atual") or state.get("current_round", 1)

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
        ]
    }


def colegiado_juri(state: ArenaState) -> dict:
    alegacao = state.get("alegacao") or state.get("claim", "")
    historico = state.get("historico_debate") or state.get("debate_history", [])

    debate_formatado = []
    for turno in historico:
        autor = turno.get("autor") or turno.get("author")
        rodada = turno.get("rodada") or turno.get("round")
        argumento = turno.get("argumento") or turno.get("argument")
        debate_formatado.append(f"[Rodada {rodada} - {autor}]:\n{argumento}")

    historico_texto = "\n\n".join(debate_formatado)

    prompt_juri = (
        f"Alegação avaliada: {alegacao}\n\n"
        f"Histórico Completo do Debate:\n{historico_texto}\n\n"
        "Emita os votos dos 3 juízes conforme as instruções."
    )

    mensagens = [
        SystemMessage(content=JURI_SYSTEM),
        HumanMessage(content=prompt_juri),
    ]

    juri_llm = llm.with_structured_output(VereditoJuriModel)
    try:
        resultado = juri_llm.invoke(mensagens)
        votos = [voto.model_dump() for voto in resultado.votos]
    except Exception:
        # Fallback em caso de erro na extração estruturada
        resposta = llm.invoke(mensagens)
        votos = [
            {
                "juiz": "Juiz 1 (Pró-Tendência)",
                "voto": "Inconclusivo",
                "justificativa": str(resposta.content),
            }
        ]

    return {"votos_juri": votos}

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

    mock_state = {
        "alegacao": "O trabalho remoto reduz a produtividade das empresas.",
        "historico_debate": [],
        "rodada_atual": 1,
        "votos_juri": [],
        "veredito_final": "",
        "homologado_por_humano": False
    }

    print("\n" + "="*50)
    print(" 🚀 EXECUTANDO SIMULAÇÃO DO DEBATE (2 RODADAS) ")
    print("="*50)

    NUM_RODADAS = 2

    for r in range(1, NUM_RODADAS + 1):
        print(f"\n--- 🔔 RODADA {r} ---")

        # 1. Agente Pró
        print(f"\n[AGENTE PRÓ] Gerando argumento (Rodada {r})...")
        res_pro = agente_pro(mock_state)
        arg_pro = res_pro["historico_debate"][0]["argumento"]
        print(f"\n👉 Pró: {arg_pro}")
        
        mock_state["historico_debate"].extend(res_pro["historico_debate"])
        mock_state["rodada_atual"] = res_pro["rodada_atual"]

        # 2. Agente Contra
        print(f"\n[AGENTE CONTRA] Gerando contra-argumento (Rodada {r})...")
        res_contra = agente_contra(mock_state)
        arg_contra = res_contra["historico_debate"][0]["argumento"]
        print(f"\n👉 Contra: {arg_contra}")

        mock_state["historico_debate"].extend(res_contra["historico_debate"])

    # 3. Júri Final
    print("\n" + "="*50)
    print("[JÚRI] Avaliando o histórico completo de 2 rodadas...")
    res_juri = colegiado_juri(mock_state)
    
    print("\n⚖️ Votos do Colegiado de Juízes:")
    print(json.dumps(res_juri, indent=4, ensure_ascii=False))
    print("="*50 + "\n")