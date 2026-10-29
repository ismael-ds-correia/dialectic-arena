import json
import os
import re
import sys
import unicodedata
import uuid
from datetime import datetime
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


def sanitizar_nome_diretorio(texto: str, tamanho_maximo: int = 50) -> str:
    """Sanitiza o texto removendo acentos, caracteres especiais e substituindo espaços por hífens."""
    # Normalizar caracteres unicode (remover acentuação)
    texto_normalizado = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("ASCII")
    # Manter apenas letras, números e espaços
    texto_limpo = re.sub(r"[^a-zA-Z0-9\s-]", "", texto_normalizado).strip().lower()
    # Substituir espaços em branco por hífens
    slug = re.sub(r"[\s]+", "-", texto_limpo)
    # Limitar o tamanho máximo sem quebrar no meio de hífens finais
    return slug[:tamanho_maximo].rstrip("-") or "debate"


def salvar_registro_debate(state: dict) -> str:
    """Salva o histórico e o parecer do debate em formato JSON dentro de debates/<slug-alegacao>/."""
    alegacao = state.get("alegacao") or state.get("claim", "")
    pasta_slug = sanitizar_nome_diretorio(alegacao)
    diretorio_destino = os.path.join("debates", pasta_slug)
    os.makedirs(diretorio_destino, exist_ok=True)

    caminho_arquivo = os.path.join(diretorio_destino, "debate_result.json")

    dados_salvar = {
        "alegacao": alegacao,
        "timestamp": datetime.now().isoformat(),
        "historico_debate": state.get("historico_debate") or state.get("debate_history", []),
        "parecer_juiz": state.get("parecer_juiz", {}),
        "homologado_por_humano": state.get("homologado_por_humano", True),
    }

    with open(caminho_arquivo, "w", encoding="utf-8") as f:
        json.dump(dados_salvar, f, indent=4, ensure_ascii=False)

    return caminho_arquivo


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
        estado_final_atualizado = {
            "homologado_por_humano": True,
            "aprovado_humano": True,
            "veredicto_final": f"Veredicto '{veredicto_nome}' homologado pelo Presidente do Tribunal.",
        }
        graph.update_state(config, estado_final_atualizado)
        # Retoma o grafo para concluir a execução
        for _ in graph.stream(None, config=config):
            pass

        # Obter estado consolidado para salvar em JSON
        estado_completo = graph.get_state(config).values
        caminho_salvo = salvar_registro_debate(estado_completo)

        exibir_separador("=")
        print(f"\n[OK] Veredito '{veredicto_nome}' devidamente HOMOLOGADO pelo Presidente do Tribunal.")
        print(f"[💾] Registro completo do debate salvo com sucesso em:")
        print(f"     -> {os.path.abspath(caminho_salvo)}")
        print("\n[*] Debate encerrado com sucesso.\n")
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
