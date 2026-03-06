import streamlit as st
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from web_infrastructure.components import render_memory_item
from memory.memory_engine import MemoryEngine

def _format_timestamp_german(timestamp_str: str) -> str:
    if not timestamp_str:
        return "Unbekannt"
    try:
        dt = datetime.fromisoformat(timestamp_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        german_tz = ZoneInfo("Europe/Berlin")
        return dt.astimezone(german_tz).strftime("%d.%m.%Y %H:%M:%S")
    except (ValueError, TypeError):
        return timestamp_str

def render_memories_overlay(backend):
    """Rendert das Overlay für alle Erinnerungen mit Pagination (Uncodixified)."""
    if not st.session_state.show_memories:
        return

    live_memory = backend.memory

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown("## Alle Erinnerungen")
    with col2:
        if st.button("Schließen", key="close_memories_top", use_container_width=True):
            st.session_state.show_memories = False
            st.rerun()

    st.markdown("### Kurzzeitgedächtnis (24h)")
    if hasattr(backend, 'short_term_memory_v2'):
        stm_count = backend.short_term_memory_v2.get_count()
        if stm_count > 0:
            st.markdown(f"**Aktive Einträge:** {stm_count}")
            
            entries = backend.short_term_memory_v2.get_active_entries()
            for i, entry in enumerate(entries[:20]):
                with st.expander(f"[{entry.importance}] {entry.category} - {entry.content[:50]}...", expanded=False):
                    st.markdown(f"**Inhalt:** {entry.content}")
                    st.markdown(f"**Kategorie:** {entry.category}")
                    st.markdown(f"**Wichtigkeit:** {entry.importance}")
                    st.markdown(f"**Erstellt:** {_format_timestamp_german(entry.created_at)}")
                    st.markdown(f"**Läuft ab:** {_format_timestamp_german(entry.expires_at)}")
                    if getattr(entry, 'migrated', False):
                        st.info("Bereits migriert")
        else:
            st.info("Keine aktiven Einträge im Kurzzeitgedächtnis (24h)")
            
        if st.button("Kurzzeitgedächtnis bereinigen", key="cleanup_stm", type="secondary"):
            migrated = backend.short_term_memory_v2.migrate_expired_entries()
            st.toast(f"{migrated} Einträge ins Langzeitgedächtnis migriert")
            st.rerun()
    else:
        st.warning("Short-term Memory V2 nicht verfügbar")
        
    st.divider()
    
    col_l1, col_l2 = st.columns([0.5, 0.5])
    with col_l1:
        st.markdown("### Langzeitgedächtnis")
    with col_l2:
        health = live_memory.health_check()
        if health["embedding_model_loaded"] and health["chromadb_connected"]:
            st.success(f"Live-Daten (Verbunden)")
        else:
            st.error("Memory-System hat Probleme")

    total_count = live_memory.get_memory_count()
    if total_count == 0:
        st.info("Keine Erinnerungen vorhanden.")
    else:
        st.markdown(f"**Gesamt:** {total_count:,} Erinnerungen")
        
        c1, c2, c3, c4 = st.columns([1,1,1,1])
        with c1:
            items_per_page = st.selectbox("Pro Seite", [50, 100, 250, 500], index=1, key="memories_per_page")
        with c2:
            filter_label = st.selectbox("Label", ["Alle", "original", "zsm gefasst"], key="filter_label_mem")
        with c3:
            filter_type = st.selectbox("Typ", ["Alle", "interaction", "summary"], key="filter_type_mem")
        with c4:
            if st.button("Aktualisieren", key="refresh_memories"):
                st.rerun()

        label_filter = None if filter_label == "Alle" else filter_label
        type_filter = None if filter_type == "Alle" else filter_type
        
        filtered_count = live_memory.get_filtered_memory_count(mem_type_filter=type_filter, label_filter=label_filter)
        
        if "memories_page" not in st.session_state:
            st.session_state.memories_page = 0
            
        if "last_filter_label" not in st.session_state:
            st.session_state.last_filter_label = filter_label
        if "last_filter_type" not in st.session_state:
            st.session_state.last_filter_type = filter_type
        
        if filter_label != st.session_state.last_filter_label or filter_type != st.session_state.last_filter_type:
            st.session_state.memories_page = 0
            st.session_state.last_filter_label = filter_label
            st.session_state.last_filter_type = filter_type
        
        max_pages = max(1, (filtered_count - 1) // items_per_page + 1)
        current_page = min(st.session_state.memories_page, max_pages - 1)
        st.session_state.memories_page = current_page
        
        offset = current_page * items_per_page
        filtered_memories = live_memory.get_recent_memories(
            limit=items_per_page,
            offset=offset,
            mem_type_filter=type_filter,
            label_filter=label_filter
        )

        st.caption(f"Seite {current_page + 1} von {max_pages} | {filtered_count} gefilterte Einträge")

        nav_c1, nav_c2, nav_c3 = st.columns([1, 2, 1])
        with nav_c1:
            if st.button("◀ Zurück", disabled=current_page == 0, use_container_width=True, key="mem_prev_page"):
                st.session_state.memories_page = max(0, current_page - 1)
                st.rerun()
        with nav_c2:
            safe_max = max(1, max_pages)
            safe_value = min(current_page + 1, safe_max)
            new_page = st.number_input("Gehe zu Seite", min_value=1, max_value=safe_max, value=safe_value, key="goto_page")
            if new_page != current_page + 1:
                st.session_state.memories_page = new_page - 1
                st.rerun()
        with nav_c3:
            if st.button("Weiter ▶", disabled=current_page >= max_pages - 1, use_container_width=True, key="mem_next_page"):
                st.session_state.memories_page = min(max_pages - 1, current_page + 1)
                st.rerun()

        for i, mem in enumerate(filtered_memories):
            render_memory_item(mem, offset + i + 1, format_timestamp=True)
