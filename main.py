import sys
import uuid
from dotenv import load_dotenv

# Garantir codificação UTF-8 no terminal Windows para evitar travamentos ou UnicodeEncodeError
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Carregar variáveis de ambiente (.env)
load_dotenv()

from arena.graph import graph

def exibir_separador(caractere: str = "=", tamanho: int = 70) -> None:
    print(caractere * tamanho)

def formatar_argumento(turno: dict) -> None:
    autor = turno.get("autor") or turno.get("author", "Desconhecido")
    rodada = turno.get("rodada") or turno.get("round", "?")
    argumento = turno.get("argumento") or turno.get("argument", "")

    prefixo = "[PRO]" if autor in ["Pró", "Pro"] else "[CONTRA]"
    exibir_separador("-")
    print(f"\n{prefixo} Rodada {rodada} - {autor.upper()}:\n")
    print(argumento.strip())
    print()

def exibir_votos_juri(votos: list) -> None:
    exibir_separador("=")
    print("\n  PARECER DO COLEGIADO DE JUIZES  \n")
    exibir_separador("=")
    for item in votos:
        juiz = item.get("juiz") or item.get("judge", "Juiz")
        voto = item.get("voto") or item.get("vote", "N/A")
        justificativa = item.get("justificativa") or item.get("rationale", "")

        print(f"\n• {juiz}")
        print(f"  Voto: {voto}")
        print(f"  Justificativa: {justificativa}\n")
    exibir_separador("-")

def main() -> None:
    exibir_separador("=")
    print("           DIALECTIC ARENA - TRIBUNAL DE DEBATES")
    exibir_separador("=")

    # 1. Entrada do Usuário
    tema_padrao = "A inteligência artificial trará mais benefícios do que riscos para a humanidade."
    entrada = input(f"\nInforme a alegação para o debate [Pressione Enter para padrão]:\n> ").strip()
    alegacao = entrada if entrada else tema_padrao

    print(f"\n[+] Tema Definido: \"{alegacao}\"\n")

    # 2. Inicialização do Estado
    thread_id = f"debate_{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    estado_inicial = {
        "alegacao": alegacao,
        "historico_debate": [],
        "rodada_atual": 1,
        "votos_juri": [],
        "veredicto_final": "",
        "aprovado_humano": False,
        "homologado_por_humano": False,
    }

    print("[*] Iniciando o debate com os agentes...\n")

    # 3. Execução da Fase de Debate em Streaming
    for evento in graph.stream(estado_inicial, config=config):
        for node_name, node_output in evento.items():
            if isinstance(node_output, dict) and node_name in ["agente_pro", "agente_contra"]:
                historico = node_output.get("historico_debate", [])
                if historico:
                    formatar_argumento(historico[-1])

    # 4. Intervenção Humana (Human-in-the-Loop)
    snapshot = graph.get_state(config)
    estado_atual = snapshot.values

    votos = estado_atual.get("votos_juri", [])
    if votos:
        exibir_votos_juri(votos)

    print("\n--- DECISAO DA PRESIDENCIA DO TRIBUNAL ---")
    decisao = input("Voce, como Presidente do Tribunal, homologa esse veredito? (s/n): ").strip().lower()

    # 5. Finalização
    if decisao in ["s", "sim", "y", "yes"]:
        graph.update_state(
            config,
            {
                "homologado_por_humano": True,
                "aprovado_humano": True,
                "veredicto_final": "Homologado pelo Presidente do Tribunal.",
            },
        )
        # Retoma o grafo para concluir a execução
        for _ in graph.stream(None, config=config):
            pass

        exibir_separador("=")
        print("\n[OK] Veredito devidamente HOMOLOGADO pelo Presidente do Tribunal.")
        print("[*] Debate encerrado com sucesso.\n")
        exibir_separador("=")
    else:
        graph.update_state(
            config,
            {
                "homologado_por_humano": False,
                "aprovado_humano": False,
                "veredicto_final": "Rejeitado pelo Presidente do Tribunal.",
            },
        )
        exibir_separador("=")
        print("\n[!] O veredito foi DESCARTADO/REJEITADO pelo Presidente do Tribunal.")
        print("[*] Execucao finalizada sem homologacao.\n")
        exibir_separador("=")

if __name__ == "__main__":
    main()
