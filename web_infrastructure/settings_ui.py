import streamlit as st
import time
from config.config import settings, LLMProvider

def render_settings_overlay(backend):
    """Rendert das Einstellungs-Overlay."""
    if not st.session_state.show_settings:
        return

    st.markdown("## Einstellungen")
    
    # Tabs fuer verschiedene Einstellungsbereiche
    tab_api, tab1, tab2, tab3 = st.tabs(["API & Modelle", "Generierung", "Emotionen", "Datenbank"])
    
    with tab_api:
        st.subheader("API & Modell Konfiguration")
        
        # 1. Provider Auswahl (jetzt mit 3 Optionen)
        provider_options = [
            "Groq Cloud (Schnell & Stark)",
            "Cerebras Cloud (Ultra-High-Speed)",
            "Ollama Lokal (Privat & Offline)"
        ]
        
        # Aktuellen Index ermitteln
        if settings.llm_provider == LLMProvider.GROQ:
            current_provider_index = 0
        elif settings.llm_provider == LLMProvider.CEREBRAS:
            current_provider_index = 1
        else:
            current_provider_index = 2
            
        selected_provider = st.selectbox(
            "KI-Anbieter (Backend)", 
            provider_options,
            index=current_provider_index
        )
        
        is_groq = "Groq" in selected_provider
        is_cerebras = "Cerebras" in selected_provider
        
        st.divider()
        
        if is_groq:
            st.markdown("### ☁️ Groq Cloud Konfiguration")
            st.caption("Benötigt einen API Key. Kostenlos verfügbar unter [console.groq.com](https://console.groq.com)")
            
            # API Key Input
            new_api_key = st.text_input(
                "Groq API Key", 
                value=settings.groq_api_key if settings.groq_api_key else "",
                type="password",
                help="Der Key wird in config/addSecrets.py gespeichert und bleibt nach einem Neustart erhalten."
            )
            
            # Model Selection
            groq_models = {
                "llama-3.3-70b-versatile": "Llama 3.3 70B (Versatile - Empfohlen)",
                "llama-3.1-8b-instant": "Llama 3.1 8B (Instant - Schnell)",
                "moonshotai/kimi-k2-instruct-0905": "Kimi k2 Instruct (0905)",
                "moonshotai/kimi-k2-instruct": "Kimi k2 Instruct (Latest)",
                "openai/gpt-oss-120b": "OpenAI GPT-OSS 120B",
                "openai/gpt-oss-20b": "OpenAI GPT-OSS 20B",
                "groq/compound": "Groq Compound (Agentic)",
                "custom": "Eigenes Modell eingeben..."
            }
            
            # Determine current selection (preserve custom values)
            current_groq_val = settings.groq_model
            start_index = 0
            if current_groq_val in groq_models:
                start_index = list(groq_models.keys()).index(current_groq_val)
            else:
                start_index = list(groq_models.keys()).index("custom")
            
            selected_groq_key = st.selectbox(
                "Groq Modell",
                list(groq_models.keys()),
                index=start_index,
                format_func=lambda x: str(groq_models.get(x, x))
            )
            
            if selected_groq_key == "custom":
                new_model = st.text_input(
                    "Manuelle Modell-ID",
                    value=current_groq_val if current_groq_val not in groq_models else "",
                    help="Gib hier die exakte Model-ID ein (z.B. gemma2-9b-it)"
                )
            else:
                new_model = selected_groq_key

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Groq Einstellungen Speichern", type="primary", use_container_width=True, key="save_settings_groq"):
                    settings.update_from_ui(provider="groq", api_key=new_api_key, model=new_model)
                    backend.reinit_brain_if_needed()  # Hot-swap Brain
                    st.success("✅ Einstellungen für Groq gespeichert!")
                    time.sleep(0.5)
                    st.rerun()
            with col2:
                if st.button("Schließen", use_container_width=True, key="close_settings_groq"):
                    st.session_state.show_settings = False
                    st.rerun()
                    
        elif is_cerebras:
            st.markdown("### ⚡ Cerebras Cloud Konfiguration")
            st.caption("Ultra-schnelle Inferenz (2000+ Token/s). API Key von [cloud.cerebras.ai](https://cloud.cerebras.ai)")
            
            # API Key Status anzeigen
            if settings.cerebras_api_key:
                st.success("✓ Cerebras API Key ist gesetzt")
            else:
                st.warning("⚠️ Kein Cerebras API Key konfiguriert")
            
            # API Key Input
            new_cerebras_key = st.text_input(
                "Cerebras API Key", 
                value=settings.cerebras_api_key if settings.cerebras_api_key else "",
                type="password",
                help="Hole dir einen Key von cloud.cerebras.ai"
            )
            
            # Model Auswahl
            cerebras_models = {
                # Production
                "llama-3.3-70b": "Llama 3.3 70B (Standard - Empfohlen)",
                "llama3.1-8b": "Llama 3.1 8B (Speed: ~2200 t/s)",
                "qwen-3-32b": "Qwen 3 32B (Speed: ~2600 t/s)",
                "gpt-oss-120b": "OpenAI GPT-OSS 120B (Speed: ~3000 t/s)",
                
                # Preview
                "qwen-3-235b-a22b-instruct-2507": "Qwen 3 235B (Preview - Massive)",
                "zai-glm-4.7": "Z.ai GLM 4.7 355B (Preview - Largest)",
                
                # Custom
                "custom": "Eigenes Modell eingeben..."
            }
            
            # Determine current selection
            current_cer_val = settings.cerebras_model
            cer_start_index = 0
            if current_cer_val in cerebras_models:
                cer_start_index = list(cerebras_models.keys()).index(current_cer_val)
            else:
                cer_start_index = list(cerebras_models.keys()).index("custom")
            
            selected_cerebras_key = st.selectbox(
                "Cerebras Modell",
                list(cerebras_models.keys()),
                index=cer_start_index,
                format_func=lambda x: str(cerebras_models.get(x, x))
            )
            
            if selected_cerebras_key == "custom":
                new_cerebras_model = st.text_input(
                    "Manuelle Modell-ID",
                    value=current_cer_val if current_cer_val not in cerebras_models else "",
                    help="Gib hier die exakte Model-ID ein"
                )
            else:
                new_cerebras_model = selected_cerebras_key

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Cerebras Einstellungen Speichern", type="primary", use_container_width=True, key="save_settings_cerebras"):
                    settings.update_from_ui(provider="cerebras", api_key=new_cerebras_key, model=new_cerebras_model)
                    backend.reinit_brain_if_needed()  # Hot-swap Brain
                    st.success("✅ Einstellungen für Cerebras gespeichert!")
                    time.sleep(0.5)
                    st.rerun()
            with col2:
                if st.button("Schließen", use_container_width=True, key="close_settings_cerebras"):
                    st.session_state.show_settings = False
                    st.rerun()
                    
        else:
            st.markdown("### 🏠 Ollama Lokal Konfiguration")
            st.caption("Benötigt eine laufende Ollama-Instanz auf deinem PC.")
            
            # Simple Mode Toggle
            simple_mode = st.toggle("Ich weiß nicht, welche Modelle ich nutzen soll", value=False)
            
            if simple_mode:
                st.info("💡 Keine Sorge! Wir setzen die bewährten Standards für dich.")
                st.markdown("""
                **Empfohlene Standards:**
                - Chat Modell: `llama3:8b` (Ausgewogen)
                - Host: `http://localhost:11434`
                """)
                
                if st.button("Standard-Werte setzen & Speichern", type="primary", use_container_width=True, key="save_settings_ollama_std"):
                    settings.update_from_ui(provider="ollama", model="llama3:8b")
                    # Wir setzen hier direkt die config attribute für host da update_from_ui das (noch) nicht kann
                    settings.ollama_host = "http://localhost:11434"
                    settings.emotion_analysis_model = "qwen2.5:1.5b"
                    backend.reinit_brain_if_needed()  # Hot-swap Brain
                    st.success("✅ Standard-Werte gesetzt! Bitte stelle sicher, dass du `ollama run llama3:8b` im Terminal ausgeführt hast.")
                    time.sleep(1.5)
                    st.rerun()
            else:
                new_host = st.text_input("Ollama URL", value=settings.ollama_host)
                new_ollama_model = st.text_input("Chat Modell", value=settings.ollama_model)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Ollama Einstellungen Speichern", type="primary", use_container_width=True, key="save_settings_ollama"):
                        settings.update_from_ui(provider="ollama", model=new_ollama_model)
                        settings.ollama_host = new_host
                        backend.reinit_brain_if_needed()  # Hot-swap Brain
                        st.success("✅ Einstellungen für Ollama gespeichert!")
                        time.sleep(0.5)
                        st.rerun()
                with col2:
                    if st.button("Schließen", use_container_width=True, key="close_settings_ollama"):
                        st.session_state.show_settings = False
                        st.rerun()


    with tab1:
        st.subheader("Generierungs-Einstellungen")
        new_temp = st.slider("Temperatur", 0.0, 1.0, float(settings.temperature), 0.1,
                            help="Hoehere Werte = kreativere Antworten")
        new_tokens = st.number_input("Max Tokens", 100, 8000, int(settings.max_tokens), 100,
                                    help="Maximale Laenge der Antworten")
        new_cot = st.toggle("Chain of Thought (Gedankenprozess)", bool(settings.chain_of_thought),
                           help="Zeigt CHAPPiEs Denkprozess")
        
        st.subheader("Gedaechtnis")
        new_k = st.slider("Memory Top-K", 1, 10, int(settings.memory_top_k),
                         help="Anzahl der Erinnerungen die abgerufen werden")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Speichern", use_container_width=True, type="primary", key="save_settings_gen"):
                settings.update_from_ui(temperature=new_temp, max_tokens=new_tokens,
                                       chain_of_thought=new_cot, memory_top_k=new_k)
                st.success("Einstellungen gespeichert!")
                time.sleep(0.5)
                st.rerun()
        with col2:
            if st.button("Schliessen", use_container_width=True, key="close_settings_gen"):
                st.session_state.show_settings = False
                st.rerun()
    
    with tab2:
        st.subheader("Emotionen bearbeiten")
        st.info("Hier kannst du CHAPPiEs emotionalen Zustand manuell anpassen.")

        emo = st.session_state.get("current_emotions") or {
            "joy": 50, "trust": 50, "energy": 80, "curiosity": 60,
            "frustration": 0, "motivation": 80
        }
        
        new_joy = st.slider("Freude", 0, 100, int(emo.get("joy", 50)), 
                           help="Gluecklichkeits-Level")
        new_trust = st.slider("Vertrauen", 0, 100, int(emo.get("trust", 50)),
                             help="Vertrauens-Level zum User")
        new_energy = st.slider("Energie", 0, 100, int(emo.get("energy", 80)),
                              help="Energie-Level (sinkt bei viel Arbeit)")
        new_curiosity = st.slider("Neugier", 0, 100, int(emo.get("curiosity", 60)),
                                 help="Wie neugierig CHAPPiE ist")
        new_motivation = st.slider("Motivation", 0, 100, int(emo.get("motivation", 80)),
                                  help="Motivations-Level")
        new_frustration = st.slider("Frustration", 0, 100, int(emo.get("frustration", 0)),
                                   help="Frustrations-Level (niedrig ist besser)")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Emotionen speichern", use_container_width=True, type="primary", key="save_settings_emo"):
                new_emotions = {
                    "joy": new_joy,
                    "trust": new_trust,
                    "energy": new_energy,
                    "curiosity": new_curiosity,
                    "frustration": new_frustration,
                    "motivation": new_motivation
                }
                if new_emotions and isinstance(new_emotions, dict):
                    st.session_state.current_emotions = new_emotions
                # Auch im Backend aktualisieren
                backend.emotions.state.happiness = new_joy
                backend.emotions.state.trust = new_trust
                backend.emotions.state.energy = new_energy
                backend.emotions.state.curiosity = new_curiosity
                backend.emotions.state.frustration = new_frustration
                backend.emotions.state.motivation = new_motivation
                backend.emotions._save_state()  # Persistieren
                st.success("Emotionen aktualisiert!")
                time.sleep(0.5)
                st.rerun()
        with col2:
            if st.button("Zuruecksetzen", use_container_width=True, key="reset_settings_emo"):
                default_emotions = {
                    "joy": 50, "trust": 50, "energy": 80, "curiosity": 60,
                    "frustration": 0, "motivation": 80
                }
                if default_emotions and isinstance(default_emotions, dict):
                    st.session_state.current_emotions = default_emotions
                backend.emotions.reset()
                st.success("Emotionen zurueckgesetzt!")
                time.sleep(0.5)
                st.rerun()
        with col3:
            if st.button("Schließen", use_container_width=True, key="close_settings_emo"):
                st.session_state.show_settings = False
                st.rerun()
    
    with tab3:
        st.subheader("Datenbank-Verwaltung")
        
        memory_count = backend.memory.get_memory_count()
        st.metric("Gespeicherte Erinnerungen", memory_count)
        
        st.warning("Achtung: Das Loeschen der ChromaDB ist nicht rueckgaengig zu machen!")
        
        # Sicherheits-Checkbox
        confirm_delete = st.checkbox("Ich verstehe, dass alle Erinnerungen unwiderruflich geloescht werden")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("ChromaDB loeschen", use_container_width=True,
                        type="primary" if confirm_delete else "secondary",
                        disabled=not confirm_delete, key="delete_chromadb"):
                if confirm_delete:
                    deleted_count = backend.memory.clear_memory()
                    st.success(f"{deleted_count} Erinnerungen geloescht!")
                    time.sleep(1)
                    st.rerun()
        with col2:
            if st.button("Schließen", use_container_width=True, key="close_settings_db"):
                st.session_state.show_settings = False
                st.rerun()
    
    st.markdown("---")