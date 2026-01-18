import streamlit as st

from web_infrastructure.components import render_memory_item

def render_memories_overlay(backend):
    """Rendert das Overlay für alle Erinnerungen."""
    if not st.session_state.show_memories:
        return

    st.markdown("## Alle Erinnerungen")

    if st.button("Schließen", key="close_memories_top", use_container_width=True):
        st.session_state.show_memories = False
        st.rerun()

    with st.container(border=True):
        # Alle Erinnerungen laden
        all_memories = backend.memory.get_recent_memories(limit=1000)

        if not all_memories:
            st.info("Keine Erinnerungen vorhanden.")
        else:
            st.markdown(f"**Gesamt: {len(all_memories)} Erinnerungen**")

            # Filter-Optionen
            col1, col2 = st.columns(2)
            with col1:
                filter_label = st.selectbox("Filter nach Label", ["Alle", "original", "zsm gefasst"])
            with col2:
                filter_type = st.selectbox("Filter nach Typ", ["Alle", "interaction", "summary"])

            # Filter anwenden
            filtered_memories = []
            for mem in all_memories:
                label = getattr(mem, 'label', 'original')
                label_match = filter_label == "Alle" or label == filter_label
                type_match = filter_type == "Alle" or mem.mem_type == filter_type
                if label_match and type_match:
                    filtered_memories.append(mem)

            st.markdown(f"**Angezeigt: {len(filtered_memories)} Erinnerungen**")

            # Erinnerungen anzeigen
            for i, mem in enumerate(filtered_memories):
                render_memory_item(mem, i + 1)
                st.divider()

    st.markdown("---")
