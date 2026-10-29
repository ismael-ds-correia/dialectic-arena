import json
import os
import uuid
from dotenv import load_dotenv
import streamlit as st

# Carregar variáveis de ambiente
load_dotenv()

from arena.graph import graph
from main import salvar_registro_debate

# 1. Configuração da Página
st.set_page_config(
    page_title="Dialectic Arena",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilização CSS adicional para uma interface refinada
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.3rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #4B5563;
        font-size: 1.05rem;
        margin-bottom: 1.8rem;
    }
    .badge-pro {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-contra {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .card-veredicto {
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #E5E7EB;
        background-color: #F9FAFB;
        margin-top: 1rem;
        margin-bottom: 1.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 2. Barra Lateral (Sidebar)
with st.sidebar:
    st.image("https://img.icons8.com/color/96/courthouse.png", width=72)
    st.title("Dialectic Arena")
    st.markdown("**Tribunal Autônomo de Inteligência Artificial**")
    st.write(
        """
        Esta plataforma orquestra um debate dialético e rigoroso entre agentes especializados:
        
        - 🛡️ **Agente Pró:** Defende a alegação com dados e busca na web.
        - ⚔️ **Agente Contra:** Refuta e busca evidências contrárias de forma cética.
        - ⚖️ **Juiz Supremo:** Aplica rigor técnico com decisão binária obrigatória (**Procedente** ou **Improcedente**).
        - 🧑‍⚖️ **Human-in-the-Loop:** Você, como Presidente do Tribunal, homologa ou descarta o veredito final.
        """
    )
    st.divider()
    if st.button("🧹 Limpar / Reiniciar Sessão", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 3. Inicialização do Session State
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "debate_history" not in st.session_state:
    st.session_state.debate_history = []
if "parecer_juiz" not in st.session_state:
    st.session_state.parecer_juiz = None
if "debate_concluido" not in st.session_state:
    st.session_state.debate_concluido = False
if "homologado" not in st.session_state:
    st.session_state.homologado = None
if "alegacao_atual" not in st.session_state:
    st.session_state.alegacao_atual = ""
if "caminho_salvo" not in st.session_state:
    st.session_state.caminho_salvo = None
if "dados_salvos" not in st.session_state:
    st.session_state.dados_salvos = None

# Cabeçalho Principal
st.markdown('<div class="main-title">🏛️ Dialectic Arena: Tribunal de Debates</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Debate dialético automatizado via LangGraph com veredito técnico e validação humana.</div>', unsafe_allow_html=True)

# 4. Formulário de Entrada da Alegação
tema_sugerido = "As urnas em 2026 foram fraudadas para eleger o candidato X."
alegacao_input = st.text_area(
    "📝 **Insira a alegação ou fato a ser debatido e julgado:**",
    value=st.session_state.alegacao_atual or tema_sugerido,
    height=80,
    help="Digite a tese central que passará pelas 3 rodadas de sustentação e refutação.",
)

col_btn, col_espaco = st.columns([1, 4])
with col_btn:
    btn_iniciar = st.button("🚀 Iniciar Debate e Julgamento", type="primary", use_container_width=True)

# 5. Execução do Debate
if btn_iniciar:
    if not alegacao_input.strip():
        st.warning("Por favor, insira uma alegação válida antes de iniciar o debate.")
    else:
        # Resetar estados da rodada anterior
        st.session_state.thread_id = f"web_run_{uuid.uuid4().hex[:8]}"
        st.session_state.debate_history = []
        st.session_state.parecer_juiz = None
        st.session_state.debate_concluido = False
        st.session_state.homologado = None
        st.session_state.alegacao_atual = alegacao_input.strip()
        st.session_state.caminho_salvo = None
        st.session_state.dados_salvos = None

        config = {"configurable": {"thread_id": st.session_state.thread_id}}

        estado_inicial = {
            "alegacao": st.session_state.alegacao_atual,
            "historico_debate": [],
            "rodada_atual": 1,
            "parecer_juiz": {},
            "veredicto_final": "",
            "aprovado_humano": False,
            "homologado_por_humano": False,
        }

        # Feedback em tempo real com st.status
        with st.status("🏛️ O Tribunal está em sessão. O debate está em andamento...", expanded=True) as status:
            st.write("🔍 Convocando os agentes de defesa e acusação...")
            try:
                for evento in graph.stream(estado_inicial, config=config):
                    for node_name, node_output in evento.items():
                        if isinstance(node_output, dict):
                            if node_name == "agente_pro":
                                st.write("🛡️ **Agente Pró** formulou seus argumentos de defesa com base nas evidências coletadas.")
                            elif node_name == "agente_contra":
                                st.write("⚔️ **Agente Contra** submeteu a refutação técnica e cética.")
                            elif node_name == "agente_juiz":
                                st.write("⚖️ **Juiz Supremo** concluiu a auditoria dos dados e proferiu a sentença.")

                # Recuperar estado snapshot no ponto de interrupção
                snapshot = graph.get_state(config)
                estado_snap = snapshot.values

                st.session_state.debate_history = estado_snap.get("historico_debate") or estado_snap.get("debate_history", [])
                st.session_state.parecer_juiz = estado_snap.get("parecer_juiz")
                st.session_state.debate_concluido = True

                status.update(label="✅ Debate e julgamento concluídos! Aguardando homologação da Presidência.", state="complete", expanded=False)
            except Exception as e:
                status.update(label=f"❌ Erro durante a execução: {str(e)}", state="error", expanded=True)
                st.error(f"Detalhes do erro: {e}")

# 6. Renderização do Histórico do Debate
if st.session_state.debate_history:
    st.markdown("---")
    st.subheader("📜 Transcrição Oficial das 3 Rodadas do Debate")

    rodada_atual_exibida = 0
    for turno in st.session_state.debate_history:
        autor = turno.get("autor") or turno.get("author", "Desconhecido")
        rodada = turno.get("rodada") or turno.get("round", 1)
        argumento = turno.get("argumento") or turno.get("argument", "")

        if rodada != rodada_atual_exibida:
            rodada_atual_exibida = rodada
            st.markdown(f"#### 🔄 Rodada {rodada}")

        if autor in ["Pró", "Pro"]:
            with st.chat_message("user", avatar="🛡️"):
                st.markdown(f"**Agente Pró (Defesa):**")
                st.write(argumento)
        else:
            with st.chat_message("assistant", avatar="⚔️"):
                st.markdown(f"**Agente Contra (Acusação / Cético):**")
                st.write(argumento)

# 7. Apresentação do Veredito do Juiz & Human-in-the-Loop
if st.session_state.parecer_juiz and st.session_state.debate_concluido:
    parecer = st.session_state.parecer_juiz
    veredicto = parecer.get("veredicto", "N/A")
    justificativa = parecer.get("justificativa", "N/A")
    avaliacao_fontes = parecer.get("avaliacao_fontes", "")

    st.markdown("---")
    st.subheader("⚖️ Parecer do Juiz Técnico Rigoroso")

    if veredicto == "Procedente":
        st.success(f"### Veredicto: PROCEDENTE (A alegação se sustenta tecnicamente)", icon="✅")
    else:
        st.error(f"### Veredicto: IMPROCEDENTE (A alegação carece de sustentação ou foi refutada)", icon="🚫")

    with st.container():
        if avaliacao_fontes:
            st.markdown("##### 🔍 Avaliação das Fontes e Evidências")
            st.info(avaliacao_fontes)

        st.markdown("##### 📜 Fundamentação Técnica e Racional do Julgamento")
        st.write(justificativa)

    # Seção de Decisão do Presidente do Tribunal (Humano)
    st.markdown("---")
    st.subheader("🧑‍⚖️ Presidência do Tribunal (Human-in-the-Loop)")
    st.markdown("Como autoridade máxima da corte, cabe a você homologar formalmente ou descartar esta decisão judicial:")

    col_h1, col_h2, _ = st.columns([1.5, 1.5, 3])

    with col_h1:
        btn_homologar = st.button("✅ Homologar Veredito e Salvar", type="primary", use_container_width=True)
    with col_h2:
        btn_rejeitar = st.button("❌ Rejeitar / Descartar", use_container_width=True)

    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    if btn_homologar:
        try:
            # Atualiza o estado no LangGraph
            graph.update_state(
                config,
                {
                    "homologado_por_humano": True,
                    "aprovado_humano": True,
                    "veredicto_final": f"Veredicto '{veredicto}' homologado pelo Presidente do Tribunal.",
                },
            )
            # Retoma o grafo para concluir
            for _ in graph.stream(None, config=config):
                pass

            # Salva o JSON na pasta dedicada
            estado_completo = graph.get_state(config).values
            caminho_arquivo = salvar_registro_debate(estado_completo)

            st.session_state.homologado = True
            st.session_state.caminho_salvo = caminho_arquivo

            # Ler dados gravados para exibir
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                st.session_state.dados_salvos = json.load(f)

            st.rerun()
        except Exception as e:
            st.error(f"Erro ao homologar o debate: {e}")

    elif btn_rejeitar:
        try:
            graph.update_state(
                config,
                {
                    "homologado_por_humano": False,
                    "aprovado_humano": False,
                    "veredicto_final": "Veredicto rejeitado pelo Presidente do Tribunal.",
                },
            )
            st.session_state.homologado = False
            st.rerun()
        except Exception as e:
            st.error(f"Erro ao rejeitar veredito: {e}")

# 8. Feedback Final Pós-Decisão
if st.session_state.homologado is True:
    st.success("🎉 **Veredito HOMOLOGADO com sucesso!** O debate foi arquivado nos autos oficiais da corte.")
    if st.session_state.caminho_salvo:
        st.info(f"💾 **Arquivo JSON gerado em:** `{os.path.abspath(st.session_state.caminho_salvo)}`")
    if st.session_state.dados_salvos:
        with st.expander("👁️ Visualizar Arquivo JSON Oficial", expanded=True):
            st.json(st.session_state.dados_salvos)

elif st.session_state.homologado is False:
    st.warning("⚠️ **Veredito DESCARTADO pela Presidência do Tribunal.** A ata foi finalizada sem homologação e não gerou registro oficial.")

