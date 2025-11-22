import streamlit as st
from .database import apply_theme, SUBSEGMENTS

def render_home():
    apply_theme("default")
    st.markdown("## Choose a subsegment")
    st.markdown('<div class="tiles">', unsafe_allow_html=True)

    rows = [SUBSEGMENTS[i:i+3] for i in range(0, len(SUBSEGMENTS), 3)]
    for row in rows:
        cols = st.columns(3, gap="medium")
        for i, name in enumerate(row):
            with cols[i]:
                clicked = st.button(name, key=f"tile_{name}", use_container_width=True)
                if clicked:
                    st.session_state["selected_subsegment"] = name
                    st.session_state["nav_page"] = "Overview"
                    st.experimental_rerun()

    st.markdown("</div>", unsafe_allow_html=True)
