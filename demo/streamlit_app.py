import streamlit as st
import os
import sys
import json
from typing import Dict, Any


# Caminho para o repo
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.append(repo_root)

from app.core.schema import Schema
from app.core.extractor import ExtractorAgent
from app.utils.session_storage import save_session_data

st.set_page_config(page_title="ChatBoB", page_icon="🤖")


# Carrega schema e agente
schema_path = os.path.join(repo_root, "examples", "schema_example.json")
schema = Schema.load_from_file(schema_path)
agent = ExtractorAgent(schema)

# Estado inicial padrão
DEFAULT_STATE: Dict[str, Any] = {
    "last_user_message": "",
    "last_asked_question": "",
    "schema": schema,
    "extracted": {},
    "missing_fields": [],
    "question_to_ask": None,
    "final_json": None,
    "context_messages": [],
    "status_finished": False,
    "next": None,
    "logs": [],
    "messages": [],  # mensagens exibidas no chat
    "_session_saved": False
}

# Inicializa state + mensagem inicial automática
if "state" not in st.session_state:
    st.session_state.state = DEFAULT_STATE.copy()
    
    initial_msg = {
        "role": "assistant",
        "content": "Olá! Sou o **ChatBoB**, como posso te chamar?"
    }
    
    # 1. Adiciona ao histórico visual do chat
    st.session_state.state["messages"].append(initial_msg)
    
    # 2. Adiciona ao contexto lógico do BOT (para ele saber que já se apresentou)
    st.session_state.state["context_messages"].append(initial_msg)
    


def run_graph_with_input(user_message: str):
    """Envia mensagem para o agente e salva os resultados no state."""
    state = st.session_state.state

    # salva no histórico visual
    state["messages"].append({"role": "user", "content": user_message})

    # salva no contexto interno
    state["last_user_message"] = user_message

    # o agente gera updates
    updates = agent.feed_message(user_message, state)
    if isinstance(updates, dict):
        state.update(updates)

    # se o agente fez alguma pergunta, ela aparece no chat
    if state.get("question_to_ask") and not state.get("status_finished"):
        state["messages"].append({
            "role": "assistant",
            "content": state["question_to_ask"]
        })

    st.session_state.state = state


st.title("🤖 ChatBoB")
st.info("""
### 🧪 Instruções do Experimento (~5 minutos)
Olá! Este chat faz parte da minha pesquisa de TCC. O ChatBoB fará algumas perguntas para coletar informações. 
**Importante:** suas respostas não precisam representar seus gostos reais, mas devem ser respostas realistas para que o estudo funcione.

Para testarmos a inteligência do agente, preciso que em **pelo menos duas perguntas** você tente desafiar as regras do diálogo
        
Exemplos de como você pode testar os limites dele:

- **Se ele pedir "dois ou mais" itens:** Tente passar apenas um.
- **Se ele pedir "até 3" itens:** Tente falar 4 ou mais.
- **Respostas fora do padrão:** Tente dar respostas que não respondam diretamente ao que foi pedido ou diga que não quer responder.
- **Dúvidas:** Se você não entender o que ele quer, pode perguntar diretamente ao ChatBoB.

Às demais perguntas, responda naturalmente. O objetivo é observar como o ChatBoB lida com essas situações.

**Muito obrigado!**
""")

state = st.session_state.state

# -------------------------
#  EXIBE TODAS AS MENSAGENS DO CHAT
# -------------------------
for msg in state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Se o agente finalizou, mostra o JSON final e uma mensagem de conclusão
if state.get("status_finished") and state.get("final_json"):
    # Verifica se já não foi exibida a mensagem final
    if not state.get("_session_saved", False):
        save_session_data(state)
        state["_session_saved"] = True

    last_message = state["messages"][-1] if state["messages"] else {}
    if last_message.get("role") != "assistant" or "extração finalizada" not in last_message.get("content", "").lower():
        final_message = "🎉 **Extração finalizada!** Aqui está o resultado estruturado:\n\n```json\n" + json.dumps(state["final_json"], indent=2, ensure_ascii=False) + "\n```"
        state["messages"].append({
            "role": "assistant", 
            "content": final_message
        })
        st.rerun()

# -------------------------
#  INPUT DO USUÁRIO
# -------------------------
if not state.get("status_finished"):
    user_message = st.chat_input("Digite sua mensagem...")

    if user_message:
        with st.chat_message("user"):
            st.markdown(user_message)

        # indicador visual de processamento
        with st.spinner("ChatBoB está pensando..."):
            run_graph_with_input(user_message)

        # recarrega para exibir mensagem nova
        st.rerun()
else:
    # Mostra mensagem quando finalizado
    st.info("✅ Extração concluída! O agente coletou todas as informações necessárias.")


# -------------------------
#  BLOCO DEBAIXO DO CHAT — STATE + LOGS
# -------------------------

st.markdown("---")

with st.expander("📌 Estado Atual do Agente"):
    st.json({
        "extracted": state.get("extracted"),
        "missing_fields": state.get("missing_fields"),
        "next": state.get("next"),
        "last_asked_question": state.get("last_asked_question"),
        "status_finished": state.get("status_finished"),
    })

with st.expander("📜 Logs do Agente"):
    for log in state.get("logs", []):
        st.write("•", log)
