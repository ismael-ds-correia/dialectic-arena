from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from arena.agents import agente_contra, agente_juiz, agente_pro
from arena.state import ArenaState


def deve_continuar_debate(state: ArenaState) -> str:
    """Decide se o debate continua para a próxima rodada ou vai para o juiz."""
    rodada = state.get("rodada_atual") or state.get("current_round", 1)
    if rodada <= 3:
        return "agente_pro"
    return "agente_juiz"


# 1. Criação do Builder
builder = StateGraph(ArenaState)

# 2. Adição dos Nós
builder.add_node("agente_pro", agente_pro)
builder.add_node("agente_contra", agente_contra)
builder.add_node("agente_juiz", agente_juiz)

# 3. Arestas de Início e Sequência
builder.add_edge(START, "agente_pro")
builder.add_edge("agente_pro", "agente_contra")

# 4. Aresta Condicional
builder.add_conditional_edges(
    "agente_contra",
    deve_continuar_debate,
    {
        "agente_pro": "agente_pro",
        "agente_juiz": "agente_juiz",
    },
)

# 5. Encerramento
builder.add_edge("agente_juiz", END)

# 6. Checkpointer e Interrupção (Human-in-the-Loop)
memory = MemorySaver()
graph = builder.compile(
    checkpointer=memory,
    interrupt_after=["agente_juiz"],
)


def salvar_visualizacao_grafo(caminho_arquivo: str = "graph.png") -> None:
    """Salva a imagem do fluxo do grafo em formato PNG."""
    try:
        imagem_bytes = graph.get_graph().draw_mermaid_png()
        with open(caminho_arquivo, "wb") as f:
            f.write(imagem_bytes)
    except Exception as e:
        print(f"Não foi possível salvar o gráfico em imagem: {e}")


if __name__ == "__main__":
    salvar_visualizacao_grafo()
