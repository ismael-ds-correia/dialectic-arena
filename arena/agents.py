import json
from typing import Any, Dict, List, Literal
from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from arena.state import ArenaState
from arena.tools import web_search_tool

# Instâncias do modelo Groq
# 1. LLM para os debatedores (Pró e Contra)
llm = ChatGroq(model_name="openai/gpt-oss-20b", temperature=0.7, max_retries=5)

# 2. LLM isolado estritamente para o Juiz (processamento de texto puro em modo JSON, sem tools)
juiz_llm_engine = ChatGroq(
    model_name="openai/gpt-oss-20b",
    temperature=0.2,
    max_retries=5,
    model_kwargs={"response_format": {"type": "json_object"}},
)

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
    "1. Avalie a confiabilidade e veracidade das evidências e fontes citadas pelo Agente Pró e pelo Agente Contra.\n"
    "2. É PROIBIDO declarar o resultado como 'Inconclusivo' ou 'Empate'. Você DEVE escolher apenas entre 'Procedente' (a alegação se sustenta com fatos) ou 'Improcedente' (a alegação foi refutada ou carece de evidências sólidas).\n"
    "3. Se ambos os lados forem fracos, declare 'Improcedente' devido ao ônus da prova caber a quem alega.\n"
    "4. Retorne sua decisão OBRIGATORIAMENTE em formato JSON válido contendo exatamente as seguintes chaves:\n"
    "   - 'veredicto': apenas 'Procedente' ou 'Improcedente'\n"
    "   - 'justificativa': texto da fundamentação jurídica e lógica da decisão\n"
    "   - 'avaliacao_fontes': texto avaliando criticamente as fontes e dados citados\n"
    "Responda apenas com o JSON puro."
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

    debate_formatado = []
    for turno in historico:
        autor = turno.get("autor") or turno.get("author")
        rodada = turno.get("rodada") or turno.get("round")
        argumento = turno.get("argumento") or turno.get("argument")
        debate_formatado.append(f"[Rodada {rodada} - {autor}]: {argumento}")
    historico_formatado = "\n\n".join(debate_formatado) if debate_formatado else "Início do debate (sem falas anteriores)."

    prompt_usuario = f"""
Alegação sob debate: "{alegacao}"

--- REGRAS INEGOCIÁVEIS DE PAPEL ---
1. Você é o ADVOGADO DE DEFESA da afirmação: "{alegacao}".
2. Seu único objetivo é DEFENDER que esta afirmação é verdadeira, plausível ou fundamentada.
3. É ESTRITAMENTE PROIBIDO mudar de lado, dar razão ao opositor ou concluir que a alegação é falsa.
4. Se os resultados das buscas trouxerem checagens de fatos ou notas oficiais desmentindo a tese, NÃO CONCORDE COM ELAS. Em vez disso, use-as para apontar brechas, questionar narrativas oficiais, apontar falta de transparência ou sugerir que as checagens são incompletas.
------------------------------------

Evidências de busca encontradas: {evidencias_str}
Histórico do debate até agora: {historico_formatado}

Elabore seu argumento/réplica de defesa agora:
"""

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
    evidencias_str = str(evidencias)

    prompt_usuario = f"""
Alegação sob debate: "{alegacao}"

--- REGRAS INEGOCIÁVEIS DE PAPEL ---
1. Você é o PROMOTOR DE ACUSAÇÃO/REFUTAÇÃO da afirmação: "{alegacao}".
2. Seu único objetivo é PROVAR que esta afirmação é falsa, improcedente ou carece de evidências.
3. É ESTRITAMENTE PROIBIDO concordar com o Agente Pró ou aceitar a alegação como verdadeira.
4. Use dados da busca, checagens de fatos e lógica rigorosa para desconstruir os argumentos do Pró.
------------------------------------

Evidências de busca encontradas: {evidencias_str}
Último argumento do Pró: {ultimo_argumento_pro}

Elabore seu contra-argumento/tréplica agora:
"""

    mensagens = [
        SystemMessage(content=AGENTE_CONTRA_SYSTEM),
        HumanMessage(content=prompt_usuario),
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
        "Aplique as regras inegociáveis e emita seu parecer definitivo em formato JSON puro "
        "com as chaves 'veredicto', 'justificativa' e 'avaliacao_fontes'."
    )

    mensagens = [
        SystemMessage(content=AGENTE_JUIZ_SYSTEM),
        HumanMessage(content=prompt_juiz),
    ]

    try:
        # Chamada pura ao modelo em modo json_object, sem tools ou function calling
        resposta = juiz_llm_engine.invoke(mensagens)
        conteudo = str(resposta.content).strip()

        # Limpar eventuais crases de markdown
        if "```json" in conteudo:
            conteudo = conteudo.split("```json")[-1].split("```")[0].strip()
        elif "```" in conteudo:
            conteudo = conteudo.split("```")[-1].split("```")[0].strip()

        parecer_raw = json.loads(conteudo)

        veredicto_bruto = str(parecer_raw.get("veredicto", "Improcedente")).strip()
        veredicto = "Procedente" if "procedente" in veredicto_bruto.lower() and "improcedente" not in veredicto_bruto.lower() else "Improcedente"

        parecer = {
            "veredicto": veredicto,
            "justificativa": str(parecer_raw.get("justificativa", "Fundamentação emitida com base nas evidências apresentadas.")),
            "avaliacao_fontes": str(parecer_raw.get("avaliacao_fontes", "Fontes e consistência dos argumentos auditadas pelo juiz.")),
        }
    except Exception as e:
        print(f"[!] Erro no processamento do juiz: {e}", flush=True)
        parecer = {
            "veredicto": "Improcedente",
            "justificativa": f"Julgamento automatizado finalizado com ressalva: {e}. Pelo ônus da prova, considerou-se improcedente.",
            "avaliacao_fontes": "Não foi possível validar de forma cabal as fontes fornecidas.",
        }

    return {"parecer_juiz": parecer}
