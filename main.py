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


def exibir_parecer_juiz(parecer: dict) -> None:
    exibir_separador("=")
    print("           PARECER DO JUIZ TÉCNICO RIGOROSO")
    exibir_separador("=")

    veredicto = parecer.get("veredicto", "N/A")
    justificativa = parecer.get("justificativa", "N/A")

    print(f"\n⚖️  VEREDICTO DO JUIZ: {veredicto.upper()}")
    print("\n📜 FUNDAMENTAÇÃO TÉCNICA:")
    print(justificativa)
    print()
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
        "parecer_juiz": {},
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

    parecer = estado_atual.get("parecer_juiz")
    if parecer:
        exibir_parecer_juiz(parecer)

    print("\n--- DECISÃO DA PRESIDÊNCIA DO TRIBUNAL ---")
    decisao = input("Você, como Presidente do Tribunal, homologa esse veredito? (s/n): ").strip().lower()

    # 5. Finalização
    if decisao in ["s", "sim", "y", "yes"]:
        veredicto_nome = parecer.get("veredicto", "Procedente") if parecer else "Procedente"
        graph.update_state(
            config,
            {
                "homologado_por_humano": True,
                "aprovado_humano": True,
                "veredicto_final": f"Veredicto '{veredicto_nome}' homologado pelo Presidente do Tribunal.",
            },
        )
        # Retoma o grafo para concluir a execução
        for _ in graph.stream(None, config=config):
            pass

        exibir_separador("=")
        print(f"\n[OK] Veredito '{veredicto_nome}' devidamente HOMOLOGADO pelo Presidente do Tribunal.")
        print("[*] Debate encerrado com sucesso.\n")
        exibir_separador("=")
    else:
        graph.update_state(
            config,
            {
                "homologado_por_humano": False,
                "aprovado_humano": False,
                "veredicto_final": "Veredicto rejeitado pelo Presidente do Tribunal.",
            },
        )
        exibir_separador("=")
        print("\n[!] O veredito foi DESCARTADO/REJEITADO pelo Presidente do Tribunal.")
        print("[*] Execução finalizada sem homologação.\n")
        exibir_separador("=")


if __name__ == "__main__":
    main()
