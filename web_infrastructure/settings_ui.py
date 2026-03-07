import streamlit as st
import time
from config.config import settings, LLMProvider
from web_infrastructure.ui_utils import EMOTION_DEFAULTS, normalize_emotions

PROVIDER_OPTIONS = {
    "auto": "Auto (folgt Haupt-Provider)",
    "vllm": "vLLM (lokal, empfohlen)",
    "groq": "Groq Cloud",
    "cerebras": "Cerebras Cloud",
    "nvidia": "NVIDIA NIM",
    "ollama": "Ollama Lokal"
}

GROQ_MODELS = {
    "llama-3.3-70b-versatile": "Llama 3.3 70B (Versatile)",
    "llama-3.1-8b-instant": "Llama 3.1 8B (Instant)",
    "moonshotai/kimi-k2-instruct-0905": "Kimi k2 Instruct (0905)",
    "moonshotai/kimi-k2-instruct": "Kimi k2 Instruct (Latest)",
    "openai/gpt-oss-120b": "OpenAI GPT-OSS 120B",
    "openai/gpt-oss-20b": "OpenAI GPT-OSS 20B",
    "groq/compound": "Groq Compound (Agentic)",
    "custom": "Eigenes Modell..."
}

CEREBRAS_MODELS = {
    "llama-3.3-70b": "Llama 3.3 70B (Standard)",
    "llama3.1-8b": "Llama 3.1 8B (Speed)",
    "qwen-3-32b": "Qwen 3 32B",
    "gpt-oss-120b": "OpenAI GPT-OSS 120B",
    "qwen-3-235b-a22b-instruct-2507": "Qwen 3 235B (Preview)",
    "zai-glm-4.7": "Z.ai GLM 4.7 355B (Preview)",
    "custom": "Eigenes Modell..."
}

NVIDIA_MODELS = {
    "z-ai/glm5": "GLM 5 - Z.ai",
    "deepseek-ai/deepseek-v3.1-terminus": "DeepSeek V3.1 Terminus",
    "moonshotai/kimi-k2.5": "Kimi K2.5",
    "meta/llama-3.3-70b-instruct": "Llama 3.3 70B",
    "meta/llama-3.1-405b-instruct": "Llama 3.1 405B",
    "nvidia/llama-3.1-nemotron-70b": "Nemotron 70B",
    "deepseek-ai/deepseek-r1": "DeepSeek R1 (Reasoning)",
    "custom": "Eigenes Modell..."
}

VLLM_MODELS = {
    "Qwen/Qwen3.5-32B-Instruct": "Qwen 3.5 32B Instruct",
    "Qwen/Qwen3.5-72B-Instruct": "Qwen 3.5 72B Instruct",
    "Qwen/Qwen3.5-122B-A10B-Instruct-GPTQ-Int4": "Qwen 3.5 122B A10B GPTQ Int4",
    "custom": "Eigenes Modell..."
}

OLLAMA_MODELS = {
    "llama3:8b": "Llama 3 8B",
    "llama3.1:8b": "Llama 3.1 8B",
    "llama3.2:1b": "Llama 3.2 1B (Klein)",
    "llama3.2:3b": "Llama 3.2 3B",
    "qwen2.5:1.5b": "Qwen 2.5 1.5B (Klein)",
    "qwen2.5:7b": "Qwen 2.5 7B",
    "mistral:7b": "Mistral 7B",
    "custom": "Eigenes Modell..."
}

EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2": "all-MiniLM-L6-v2 (Schnell, 384D)",
    "all-mpnet-base-v2": "all-mpnet-base-v2 (Genau, 768D)",
    "multi-qa-MiniLM-L6-cos-v1": "multi-qa-MiniLM (Optimiert für Q&A)",
    "paraphrase-multilingual-MiniLM-L12-v2": "Paraphrase Multilingual",
    "custom": "Eigenes Modell..."
}


def _get_model_for_provider(models_dict, current_value):
    if current_value in models_dict:
        return current_value
    if current_value and current_value not in models_dict:
        return "custom"
    return list(models_dict.keys())[0]


def _render_model_select(label, models_dict, current_value, key_prefix, help_text=None):
    current_key = _get_model_for_provider(models_dict, current_value)
    selected = st.selectbox(
        label,
        list(models_dict.keys()),
        index=list(models_dict.keys()).index(current_key),
        format_func=lambda x: models_dict.get(x, x),
        key=f"{key_prefix}_select",
        help=help_text
    )
    if selected == "custom":
        custom_model = st.text_input(
            "Modell-ID eingeben",
            value=current_value if current_value not in models_dict else "",
            key=f"{key_prefix}_custom",
            help="Gib die exakte Modell-ID ein"
        )
        return custom_model
    return selected


def _render_provider_select(label, current_provider, key, include_auto=True):
    options = list(PROVIDER_OPTIONS.keys()) if include_auto else [k for k in PROVIDER_OPTIONS.keys() if k != "auto"]
    current_val = current_provider.value if current_provider else "auto"
    if current_val not in options:
        current_val = "auto"
    
    selected = st.selectbox(
        label,
        options,
        index=options.index(current_val) if current_val in options else 0,
        format_func=lambda x: PROVIDER_OPTIONS.get(x, x),
        key=key
    )
    return selected


def render_settings_overlay(backend):
    if not st.session_state.show_settings:
        return

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("## Einstellungen")
    with col2:
        if st.button("Schließen", use_container_width=True, key="close_settings_top"):
            st.session_state.show_settings = False
            st.rerun()
            
    st.info("💡 Alle Änderungen werden automatisch gespeichert.")
    
    tab_api, tab1, tab2, tab3 = st.tabs(["API & Modelle", "Generierung", "Emotionen", "Datenbank"])
    
    with tab_api:
        provider_options_display = [
            "vLLM (lokal, empfohlen)",
            "Groq Cloud",
            "Cerebras Cloud",
            "NVIDIA NIM",
            "Ollama Lokal"
        ]
        
        if settings.llm_provider == LLMProvider.VLLM:
            current_provider_index = 0
        elif settings.llm_provider == LLMProvider.GROQ:
            current_provider_index = 1
        elif settings.llm_provider == LLMProvider.CEREBRAS:
            current_provider_index = 2
        elif settings.llm_provider == LLMProvider.NVIDIA:
            current_provider_index = 3
        else:
            current_provider_index = 4
            
        selected_provider_display = st.selectbox(
            "KI-Anbieter (Hauptanbieter)",
            provider_options_display,
            index=current_provider_index,
            key="main_provider_select"
        )
        
        is_vllm = "vLLM" in selected_provider_display
        is_groq = "Groq" in selected_provider_display
        is_cerebras = "Cerebras" in selected_provider_display
        is_nvidia = "NVIDIA" in selected_provider_display
        is_ollama = not (is_vllm or is_groq or is_cerebras or is_nvidia)
        
        st.divider()
        update_data = {}
        
        with st.expander("Chat-Modell (Hauptantwort)", expanded=True):
            if is_groq:
                update_data["groq_api_key"] = st.text_input("Groq API Key", value=settings.groq_api_key or "", type="password", key="groq_api_key_input")
                update_data["groq_model"] = _render_model_select("Modell", GROQ_MODELS, settings.groq_model, "groq_model")
            elif is_vllm:
                update_data["vllm_url"] = st.text_input("vLLM URL", value=settings.vllm_url, key="vllm_url_input")
                update_data["vllm_model"] = _render_model_select("Modell", VLLM_MODELS, settings.vllm_model, "vllm_model")
            elif is_cerebras:
                update_data["cerebras_api_key"] = st.text_input("Cerebras API Key", value=settings.cerebras_api_key or "", type="password", key="cerebras_api_key_input")
                update_data["cerebras_model"] = _render_model_select("Modell", CEREBRAS_MODELS, settings.cerebras_model, "cerebras_model")
            elif is_nvidia:
                update_data["nvidia_api_key"] = st.text_input("NVIDIA API Key", value=settings.nvidia_api_key or "", type="password", key="nvidia_api_key_input")
                update_data["nvidia_model"] = _render_model_select("Modell", NVIDIA_MODELS, settings.nvidia_model, "nvidia_model")
            else:
                update_data["ollama_host"] = st.text_input("Ollama URL", value=settings.ollama_host, key="ollama_host_input")
                update_data["ollama_model"] = _render_model_select("Modell", OLLAMA_MODELS, settings.ollama_model, "ollama_model")
        
        with st.expander("Intent-Analyse (Step 1 - Verstehen)"):
            update_data["intent_provider"] = _render_provider_select("Provider", settings.intent_provider, "intent_provider_select", include_auto=True)
            col1, col2 = st.columns(2)
            with col1:
                update_data["intent_processor_model_vllm"] = _render_model_select("Modell für vLLM", VLLM_MODELS, settings.intent_processor_model_vllm, "intent_vllm")
                update_data["intent_processor_model_groq"] = _render_model_select("Modell für Groq", GROQ_MODELS, settings.intent_processor_model_groq, "intent_groq")
                update_data["intent_processor_model_nvidia"] = _render_model_select("Modell für NVIDIA", NVIDIA_MODELS, settings.intent_processor_model_nvidia, "intent_nvidia")
            with col2:
                update_data["intent_processor_model_cerebras"] = _render_model_select("Modell für Cerebras", CEREBRAS_MODELS, settings.intent_processor_model_cerebras, "intent_cerebras")
                update_data["intent_processor_model_ollama"] = _render_model_select("Modell für Ollama", OLLAMA_MODELS, settings.intent_processor_model_ollama, "intent_ollama")
        
        with st.expander("Query Extraction (Memory-Suche)"):
            update_data["query_extraction_provider"] = _render_provider_select("Provider", settings.query_extraction_provider, "query_provider_select", include_auto=True)
            col1, col2 = st.columns(2)
            with col1:
                update_data["query_extraction_vllm_model"] = _render_model_select("Modell für vLLM", VLLM_MODELS, settings.query_extraction_vllm_model, "query_vllm")
                update_data["query_extraction_groq_model"] = _render_model_select("Modell für Groq", GROQ_MODELS, settings.query_extraction_groq_model, "query_groq")
                update_data["query_extraction_nvidia_model"] = _render_model_select("Modell für NVIDIA", NVIDIA_MODELS, settings.query_extraction_nvidia_model, "query_nvidia")
            with col2:
                update_data["query_extraction_cerebras_model"] = _render_model_select("Modell für Cerebras", CEREBRAS_MODELS, settings.query_extraction_cerebras_model, "query_cerebras")
                update_data["query_extraction_ollama_model"] = _render_model_select("Modell für Ollama", OLLAMA_MODELS, settings.query_extraction_ollama_model, "query_ollama")
        
        with st.expander("Emotion-Analyse"):
            update_data["emotion_analysis_host"] = st.text_input("Ollama Host", value=settings.emotion_analysis_host, key="emotion_host_input")
            update_data["emotion_analysis_model"] = _render_model_select("Modell", OLLAMA_MODELS, settings.emotion_analysis_model, "emotion_model")
        
        with st.expander("Embedding (Vektordatenbank)"):
            update_data["embedding_model"] = _render_model_select("Modell", EMBEDDING_MODELS, settings.embedding_model, "embedding_model")
        
        with st.expander("Training-Modelle"):
            use_global = st.checkbox("Globale Modelle verwenden", value=settings.training_use_global_settings, key="training_use_global")
            update_data["training_use_global_settings"] = use_global
            if not use_global:
                st.markdown("**Chappie Training-Modell**")
                col1, col2 = st.columns(2)
                with col1:
                    update_data["training_chappie_provider"] = _render_provider_select("Provider", settings.training_chappie_provider, "training_chappie_provider", include_auto=True)
                with col2:
                    update_data["training_chappie_model"] = st.text_input("Modell-ID", value=settings.training_chappie_model or "", key="training_chappie_model_input")
                
                st.markdown("**Trainer Modell**")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    update_data["training_trainer_provider"] = _render_provider_select("Provider", settings.training_trainer_provider, "training_trainer_provider", include_auto=True)
                with col_t2:
                    update_data["training_trainer_model"] = st.text_input("Modell-ID", value=settings.training_trainer_model or "", key="training_trainer_model_input")

        provider_value = "vllm" if is_vllm else ("ollama" if is_ollama else ("groq" if is_groq else ("cerebras" if is_cerebras else "nvidia")))
        update_data["llm_provider"] = provider_value
        
        # AUTO-SAVE LOGIC API TAB
        current_api_hash = hash(str(update_data))
        if "last_api_settings_hash" not in st.session_state:
            st.session_state.last_api_settings_hash = current_api_hash
            
        if current_api_hash != st.session_state.last_api_settings_hash:
            settings.update_from_ui(**update_data)
            backend.reinit_brain_if_needed()
            st.session_state.last_api_settings_hash = current_api_hash
            st.toast("Modell-Einstellungen automatisch gespeichert 💾")

    
    with tab1:
        st.subheader("Generierung")
        new_temp = st.slider("Temperatur", 0.0, 1.0, float(settings.temperature), 0.1)
        new_tokens = st.number_input("Max Tokens", 100, 8000, int(settings.max_tokens), 100)
        new_cot = st.toggle("Chain of Thought", bool(settings.chain_of_thought))
        new_k = st.slider("Memory Top-K", 1, 10, int(settings.memory_top_k))
        
        # AUTO-SAVE LOGIC GEN TAB
        gen_data = {"temperature": new_temp, "max_tokens": new_tokens, "chain_of_thought": new_cot, "memory_top_k": new_k}
        current_gen_hash = hash(str(gen_data))
        if "last_gen_settings_hash" not in st.session_state:
            st.session_state.last_gen_settings_hash = current_gen_hash
            
        if current_gen_hash != st.session_state.last_gen_settings_hash:
            settings.update_from_ui(**gen_data)
            st.session_state.last_gen_settings_hash = current_gen_hash
            st.toast("Generierungs-Einstellungen automatisch gespeichert 💾")

    
    with tab2:
        st.subheader("Emotionen bearbeiten")
        emo = normalize_emotions(st.session_state.get("current_emotions"))
        
        new_happiness = st.slider("Freude", 0, 100, int(emo.get("happiness", EMOTION_DEFAULTS["happiness"])))
        new_trust = st.slider("Vertrauen", 0, 100, int(emo.get("trust", EMOTION_DEFAULTS["trust"])))
        new_energy = st.slider("Energie", 0, 100, int(emo.get("energy", EMOTION_DEFAULTS["energy"])))
        new_curiosity = st.slider("Neugier", 0, 100, int(emo.get("curiosity", EMOTION_DEFAULTS["curiosity"])))
        new_motivation = st.slider("Motivation", 0, 100, int(emo.get("motivation", EMOTION_DEFAULTS["motivation"])))
        new_frustration = st.slider("Frustration", 0, 100, int(emo.get("frustration", EMOTION_DEFAULTS["frustration"])))
        new_sadness = st.slider("Traurigkeit", 0, 100, int(emo.get("sadness", EMOTION_DEFAULTS["sadness"])))
        
        new_emotions = normalize_emotions({
            "happiness": new_happiness,
            "trust": new_trust,
            "energy": new_energy,
            "curiosity": new_curiosity,
            "frustration": new_frustration,
            "motivation": new_motivation,
            "sadness": new_sadness,
        })
        
        # AUTO-SAVE LOGIC EMO TAB
        current_emo_hash = hash(str(new_emotions))
        if "last_emo_settings_hash" not in st.session_state:
            st.session_state.last_emo_settings_hash = current_emo_hash
            
        if current_emo_hash != st.session_state.last_emo_settings_hash:
            st.session_state.current_emotions = new_emotions
            backend.emotions.state.happiness = new_happiness
            backend.emotions.state.trust = new_trust
            backend.emotions.state.energy = new_energy
            backend.emotions.state.curiosity = new_curiosity
            backend.emotions.state.frustration = new_frustration
            backend.emotions.state.motivation = new_motivation
            backend.emotions.state.sadness = new_sadness
            backend.emotions._save_state()
            st.session_state.last_emo_settings_hash = current_emo_hash
            st.toast("Emotionen automatisch aktualisiert 💾")
            
        if st.button("Emotionen auf Standardwerte zurücksetzen", key="reset_settings_emo"):
            default_emotions = dict(EMOTION_DEFAULTS)
            st.session_state.current_emotions = default_emotions
            backend.emotions.reset()
            st.toast("Emotionen zurückgesetzt")
            time.sleep(0.5)
            st.rerun()
    
    with tab3:
        st.subheader("Datenbank-Verwaltung")
        memory_count = backend.memory.get_memory_count()
        st.metric("Gespeicherte Erinnerungen", memory_count)
        
        st.warning("⚠️ Das Löschen der ChromaDB ist unwiderruflich!")
        confirm_delete = st.checkbox("Ich verstehe das und möchte die Datenbank leeren")

        if confirm_delete:
            if st.button("ChromaDB unwiderruflich löschen", type="primary", key="delete_chromadb"):
                deleted_count = backend.memory.clear_memory()
                st.success(f"{deleted_count} Erinnerungen gelöscht!")
                time.sleep(1)
                st.rerun()
