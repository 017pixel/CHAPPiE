import streamlit as st

def inject_modern_css():
    st.markdown("""
    <style>
        /* Import Font: Outfit (Product Default) */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600&display=swap');

        /* --- UNCODIXIFIED THEME (Obsidian Depth / Normal UI) --- */
        :root {
            --bg-color: #0f0f0f;
            --sidebar-bg: #121212;
            --card-bg: #1a1a1a;
            --accent: #81c784;
            --text-primary: #f5f5f5;
            --text-secondary: #a0a0a0;
            --border-color: #2a2a2a;
            --border-radius: 6px;
        }

        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif !important;
            background-color: var(--bg-color) !important;
            color: var(--text-primary);
        }

        /* --- BUTTONS (NORMAL) --- */
        .stButton button {
            background-color: transparent !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: var(--border-radius) !important;
            transition: background-color 0.15s ease, border-color 0.15s ease;
            font-weight: 500;
            width: 100% !important;
            padding: 8px 12px !important;
            margin-bottom: 4px !important;
            text-align: left !important;
            box-shadow: none !important;
            background: var(--card-bg) !important;
        }

        .stButton button:hover, .stButton button:active, .stButton button:focus {
            border-color: var(--accent) !important;
            color: var(--text-primary) !important;
            background-color: #252525 !important;
            box-shadow: none !important;
            transform: none !important;
        }

        /* Header Buttons */
        [data-testid="stHorizontalBlock"] .stButton button {
            text-align: center !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            height: 38px !important;
        }

        /* Action Buttons (Primary) */
        button[kind="primary"] {
            background-color: var(--accent) !important;
            color: #000 !important;
            border-color: var(--accent) !important;
            font-weight: 600 !important;
        }
        
        button[kind="primary"]:hover {
            background-color: #a5d6a7 !important;
            border-color: #a5d6a7 !important;
        }

        /* --- SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg) !important;
            border-right: 1px solid var(--border-color);
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
             color: var(--text-primary) !important;
             font-weight: 600;
        }

        /* Sidebar Spacing */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
            gap: 0 !important;
        }

        /* --- MAIN AREA & CHAT INPUT --- */
        .stApp {
            background-color: var(--bg-color);
        }

        section[data-testid="stMain"] {
            padding-bottom: 90px !important;
        }

        .stChatInputContainer {
            background-color: var(--bg-color) !important;
            border-top: none !important;
            padding: 16px 24px !important;
            z-index: 99 !important;
        }
        
        /* Make chat input adhere to normal UI */
        [data-testid="stChatInput"] {
            background-color: var(--card-bg) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: var(--border-radius) !important;
            transition: border-color 0.2s ease-in-out;
            padding: 0 !important;
        }
        
        [data-testid="stChatInput"]:focus-within {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 1px var(--accent) !important;
        }
        
        /* Remove inner wrappers borders and fix width */
        [data-testid="stChatInput"] > div,
        [data-testid="stChatInput"] > div > div {
            border: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
        }
        
        [data-testid="stChatInput"] textarea {
            border: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
            outline: none !important;
            width: 100% !important;
            padding-left: 12px !important;
        }
        
        [data-testid="stChatInput"] textarea:focus {
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }

        /* Hover effects for Containers and Expanders */
        [data-testid="stForm"]:hover,
        [data-testid="stVerticalBlockBorderWrapper"]:hover,
        .stExpander:hover {
            border-color: var(--accent) !important;
            transition: border-color 0.2s ease-in-out;
        }

        /* --- INPUTS & SELECTS --- */
        input, select, textarea, .stSelectbox > div > div {
            background-color: var(--card-bg) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: var(--border-radius) !important;
            color: var(--text-primary) !important;
            box-shadow: none !important;
        }

        input:focus, select:focus, textarea:focus {
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 1px var(--accent) !important;
        }

        .stSelectbox label, .stTextInput label, .stNumberInput label, .stSlider label {
            color: var(--text-secondary) !important;
            font-size: 0.85rem !important;
            font-weight: 500 !important;
        }

        /* --- MODALS / EXPANDERS --- */
        .stExpander {
            background-color: var(--sidebar-bg);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            margin-bottom: 8px;
        }
        
        .stExpander header {
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        /* --- METRICS / INFO CARDS (NORMAL) --- */
        .metric-container {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 16px;
            margin-bottom: 16px;
            transition: border-color 0.2s ease-in-out;
        }

        .metric-container:hover {
            border-color: var(--accent) !important;
        }

        .metric-label {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }

        .metric-value {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--text-primary);
        }
        
        .metric-sub {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 2px;
        }

        /* --- BRAIN MONITOR (NORMALIZED) --- */
        .brain-monitor {
            background-color: var(--sidebar-bg);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 12px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.85rem;
            margin-top: 8px;
        }

        .brain-monitor-section {
            border-left: 2px solid var(--border-color);
            padding: 4px 12px;
            margin: 8px 0;
        }
        
        .brain-monitor-section.input { border-left-color: #38bdf8; }
        .brain-monitor-section.thought { border-left-color: #a855f7; }
        .brain-monitor-section.emotion { border-left-color: #f43f5e; }
        .brain-monitor-section.memory { border-left-color: #10b981; }

        .memory-item {
            background-color: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius);
            padding: 8px 12px;
            margin: 4px 0;
            font-size: 0.85rem;
            transition: border-color 0.2s ease-in-out;
        }

        .memory-item:hover {
            border-color: var(--accent) !important;
        }

        /* Status Bars */
        .emotion-bar-bg {
            background-color: var(--border-color);
            height: 4px;
            width: 100%;
            margin-bottom: 8px;
            margin-top: 4px;
            border-radius: 2px;
        }
        
        .emotion-bar-fill {
            height: 100%;
            background-color: var(--accent);
            border-radius: 2px;
        }

        /* JSON Code Blocks */
        .stCodeBlock, .stCodeBlock code {
            background-color: var(--sidebar-bg) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: var(--border-radius) !important;
            font-size: 0.85rem;
        }

        /* --- TABS --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 16px;
        }

        .stTabs [data-baseweb="tab"] {
            color: var(--text-secondary);
            border-bottom: 2px solid transparent !important;
            padding-bottom: 8px;
            background-color: transparent !important;
        }

        .stTabs [aria-selected="true"] {
            color: var(--text-primary) !important;
            border-bottom-color: var(--accent) !important;
        }

        /* Fix Markdown standard output spacing */
        p {
            line-height: 1.5;
            margin-bottom: 12px;
        }
    </style>
    """, unsafe_allow_html=True)
