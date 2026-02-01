import streamlit as st

from web_infrastructure.components import render_memory_item
from memory.memory_engine import MemoryEngine

def render_memories_overlay(backend):
    """Rendert das Overlay für alle Erinnerungen mit Pagination für unbegrenzte Skalierung."""
    if not st.session_state.show_memories:
        return

    # Live Memory Engine für aktuelle Daten (nicht gecacht!)
    live_memory = backend.memory

    st.markdown("## Alle Erinnerungen")
    
    # === KURZZEITGEDAECHTNIS (Short-Term Memory V2) ===
    with st.container(border=True):
        st.markdown("### Kurzzeitgedächtnis (24h)")
        
        if hasattr(backend, 'short_term_memory_v2'):
            stm_count = backend.short_term_memory_v2.get_count()
            
            if stm_count > 0:
                st.success(f"{stm_count} aktive Eintraege")
                
                # Zeige alle aktiven Einträge
                entries = backend.short_term_memory_v2.get_active_entries()
                for i, entry in enumerate(entries[:20]):  # Max 20 anzeigen
                    with st.expander(f"[{entry.importance}] {entry.category} - {entry.content[:50]}...", expanded=False):
                        st.markdown(f"**Inhalt:** {entry.content}")
                        st.markdown(f"**Kategorie:** {entry.category}")
                        st.markdown(f"**Wichtigkeit:** {entry.importance}")
                        st.markdown(f"**Erstellt:** {entry.created_at}")
                        st.markdown(f"**Laueft ab:** {entry.expires_at}")
                        if entry.migrated:
                            st.info("Bereits migriert")
            else:
                st.info("Keine aktiven Eintraege im Kurzzeitgedächtnis (24h)")
        else:
            st.warning("Short-term Memory V2 nicht verfuegbar")
        
        if st.button("Kurzzeitgedächtnis bereinigen", key="cleanup_stm"):
            if hasattr(backend, 'short_term_memory_v2'):
                migrated = backend.short_term_memory_v2.migrate_expired_entries()
                st.success(f"{migrated} Eintraege ins Langzeitgedächtnis migriert")
                st.rerun()

    if st.button("Schließen", key="close_memories_top", use_container_width=True):
        st.session_state.show_memories = False
        st.rerun()

    # Refresh Button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Refresh", key="refresh_memories"):
            st.rerun()
    with col2:
        # Health Status anzeigen
        health = live_memory.health_check()
        if health["embedding_model_loaded"] and health["chromadb_connected"]:
            st.success(f"Live-Daten ({health['memory_count']} Erinnerungen)")
        else:
            st.error("Memory-System hat Probleme")

    with st.container(border=True):
        # Gesamtzahl der Erinnerungen (unbegrenzt)
        total_count = live_memory.get_memory_count()
        
        if total_count == 0:
            st.info("Keine Erinnerungen vorhanden.")
        else:
            st.markdown(f"**Gesamt: {total_count:,} Erinnerungen**")
            
            # Pagination Setup
            items_per_page = st.selectbox(
                "Erinnerungen pro Seite",
                [50, 100, 250, 500],
                index=1,
                key="memories_per_page"
            )
            
            # Session State für Pagination
            if "memories_page" not in st.session_state:
                st.session_state.memories_page = 0
            
            max_pages = max(1, (total_count - 1) // items_per_page + 1)
            current_page = st.session_state.memories_page
            
            # Filter-Optionen
            col1, col2 = st.columns(2)
            with col1:
                filter_label = st.selectbox("Filter nach Label", ["Alle", "original", "zsm gefasst"])
            with col2:
                filter_type = st.selectbox("Filter nach Typ", ["Alle", "interaction", "summary"])

            # Erinnerungen laden (mit Offset für Pagination)
            offset = current_page * items_per_page
            all_memories = live_memory.get_recent_memories(limit=items_per_page, offset=offset)

            # Filter anwenden - wenn beide Filter auf "Alle", zeige alles direkt
            if filter_label == "Alle" and filter_type == "Alle":
                filtered_memories = all_memories
            else:
                filtered_memories = []
                for mem in all_memories:
                    label = getattr(mem, 'label', 'original')
                    label_match = filter_label == "Alle" or label == filter_label
                    type_match = filter_type == "Alle" or mem.mem_type == filter_type
                    if label_match and type_match:
                        filtered_memories.append(mem)

            st.markdown(f"**Seite {current_page + 1} von {max_pages} | Zeige: {len(filtered_memories)} Erinnerungen**")

            # Pagination Controls
            with st.container():
                nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                with nav_col1:
                    if st.button("◀ Zurück", disabled=current_page == 0, use_container_width=True, key="mem_prev_page"):
                        st.session_state.memories_page = max(0, current_page - 1)
                        st.rerun()
                with nav_col2:
                    # Direkte Seiten-Eingabe
                    new_page = st.number_input(
                        "Gehe zu Seite",
                        min_value=1,
                        max_value=max_pages,
                        value=current_page + 1,
                        key="goto_page"
                    )
                    if new_page != current_page + 1:
                        st.session_state.memories_page = new_page - 1
                        st.rerun()
                with nav_col3:
                    if st.button("Weiter ▶", disabled=current_page >= max_pages - 1, use_container_width=True, key="mem_next_page"):
                        st.session_state.memories_page = min(max_pages - 1, current_page + 1)
                        st.rerun()

            # Erinnerungen anzeigen
            for i, mem in enumerate(filtered_memories):
                render_memory_item(mem, offset + i + 1)
                st.divider()

    st.markdown("---")

