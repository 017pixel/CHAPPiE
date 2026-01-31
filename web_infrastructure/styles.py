import streamlit as st

def inject_modern_css():
    st.markdown("""
    <style>
        /* Import Font: Outfit */
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');

        /* --- GLOBAL RESET & VARS --- */
        :root {
            --bg-color: #0d1117;
            --sidebar-bg: #010409;
            --card-bg: #161b22;
            --accent-green: #1a5c20; /* Dark Green Border */
            --accent-green-bright: #2ea043;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --border-color: #30363d;
        }

        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif !important;
            background-color: var(--bg-color) !important;
            color: var(--text-primary);
        }

        /* --- BUTTONS --- */
        .stButton button {
            background-color: var(--card-bg) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 4px !important;
            transition: all 0.2s ease-in-out;
            font-weight: 500;
            width: 100% !important;
            padding: 10px 15px !important;
            margin-bottom: 5px !important;
            white-space: nowrap !important;
            display: inline-block !important;
            overflow: hidden !important;
            text-overflow: ellipsis;
            text-align: left !important;
        }

        /* Refresh Button specific styling */
        .refresh-btn button {
            background: linear-gradient(135deg, rgba(26, 92, 32, 0.2) 0%, rgba(22, 27, 34, 0.8) 100%) !important;
            border: 1px solid var(--accent-green) !important;
            box-shadow: 0 2px 8px rgba(26, 92, 32, 0.3) !important;
        }

        .refresh-btn button:hover {
            background: linear-gradient(135deg, rgba(46, 160, 67, 0.3) 0%, rgba(22, 27, 34, 0.9) 100%) !important;
            box-shadow: 0 4px 12px rgba(46, 160, 67, 0.5) !important;
            transform: translateY(-1px) !important;
        }

        .stButton button:hover, .stButton button:active, .stButton button:focus {
            border-color: var(--accent-green) !important;
            box-shadow: 0 0 8px rgba(26, 92, 32, 0.4) !important;
            color: #fff !important;
            background-color: #1c2128 !important;
        }

        /* Ensure the top row buttons are wider and spaced correctly */
        [data-testid="column"] .stButton button {
            width: 160px !important;
            justify-content: center !important;
            text-align: center !important;
        }
        
        div[data-testid="stHorizontalBlock"] {
            gap: 8px !important;
        }

        /* Sidebar Spacing */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
            gap: 0.4rem !important;
        }

        /* --- SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: var(--sidebar-bg) !important;
            border-right: 1px solid var(--border-color);
        }
        
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
             color: #fff !important;
             font-weight: 700;
        }

        /* --- MAIN AREA --- */
        .stApp {
            background-color: var(--bg-color);
        }

        /* Chat Input - Proper positioning within Streamlit layout */
        section[data-testid="stMain"] {
            padding-bottom: 80px !important;
        }
        .stChatInputContainer {
            position: sticky !important;
            bottom: 10px !important;
            background-color: var(--bg-color) !important;
            padding: 15px 20px !important;
            margin-top: 20px !important;
            border-top: 1px solid var(--border-color) !important;
            z-index: 100 !important;
        }
        .stChatInputContainer textarea {
            background-color: var(--card-bg) !important;
            color: #fff !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 12px !important;
            min-height: 50px !important;
        }
        .stChatInputContainer textarea:focus {
            border-color: var(--accent-green) !important;
            box-shadow: 0 0 0 2px rgba(46, 160, 67, 0.3) !important;
        }
        
        /* Thoughts & Code Block Wrapping (Fix horizontal scroll) */
        code {
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
        }
        
        /* Status Bars */
        .emotion-bar-bg {
            background-color: #21262d;
            border-radius: 4px;
            height: 6px;
            width: 100%;
            margin-bottom: 12px;
            margin-top: 4px;
        }
        .emotion-bar-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }

        /* Header Logo */
        .header-logo {
            font-size: 1.5rem;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        /* Command Buttons (oben) - rechteckig und einheitlich */
        [data-testid="stHorizontalBlock"] .stButton button {
            background-color: var(--card-bg) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 4px !important; /* RECHTECKIG */
            transition: all 0.2s ease-in-out !important;
            font-weight: 500 !important;
            width: 100% !important;
            padding: 8px 10px !important;
            font-size: 0.85rem !important;
            text-align: center !important;
            height: 40px !important; /* Einheitliche Hoehe */
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }

        [data-testid="stHorizontalBlock"] .stButton button:hover {
            border-color: #2ea043 !important; /* GRUENER HOVER */
            box-shadow: 0 0 10px rgba(46, 160, 67, 0.4) !important;
            color: #fff !important;
            background-color: #1c2128 !important;
        }
        
        /* ============================================ */
        /* BRAIN MONITOR STYLES */
        /* ============================================ */
        
        .brain-monitor {
            background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px;
            margin-top: 10px;
            font-family: 'Consolas', 'Monaco', monospace;
        }
        
        .brain-monitor-header {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #58a6ff;
            font-weight: 600;
            font-size: 0.9rem;
            margin-bottom: 10px;
            cursor: pointer;
        }
        
        .brain-monitor-section {
            background: rgba(22, 27, 34, 0.8);
            border-left: 3px solid #30363d;
            padding: 8px 12px;
            margin: 8px 0;
            border-radius: 0 4px 4px 0;
        }
        
        .brain-monitor-section.input {
            border-left-color: #58a6ff;
        }
        
        .brain-monitor-section.thought {
            border-left-color: #a371f7;
        }
        
        .brain-monitor-section.emotion {
            border-left-color: #f85149;
        }
        
        .brain-monitor-section.memory {
            border-left-color: #3fb950;
        }
        
        .emotion-delta-positive {
            color: #3fb950;
            font-weight: 600;
        }
        
        .emotion-delta-negative {
            color: #f85149;
            font-weight: 600;
        }
        
        .emotion-delta-neutral {
            color: #8b949e;
        }
        
        .memory-item {
            background: rgba(48, 54, 61, 0.5);
            border-radius: 4px;
            padding: 6px 10px;
            margin: 4px 0;
            font-size: 0.8rem;
        }
        
        .memory-score {
            color: #3fb950;
            font-weight: 600;
        }
        
        /* ============================================ */
        /* DEEP THINK STYLES */
        /* ============================================ */
        
        .deep-think-container {
            background: linear-gradient(135deg, #0d1117 0%, #1a1f2e 100%);
            border: 1px solid #238636;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
        }
        
        .deep-think-header {
            color: #58a6ff;
            font-size: 1.2rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }
        
        .deep-think-step {
            background: rgba(22, 27, 34, 0.9);
            border-left: 3px solid #a371f7;
            padding: 12px 16px;
            margin: 10px 0;
            border-radius: 0 8px 8px 0;
        }
        
        .deep-think-step-number {
            color: #a371f7;
            font-weight: 700;
            font-size: 0.9rem;
        }
        
        .deep-think-thought {
            color: #c9d1d9;
            margin-top: 8px;
            line-height: 1.6;
        }
        
        .deep-think-controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .deep-think-btn {
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        
        .deep-think-btn-continue {
            background: #238636;
            border: 1px solid #2ea043;
            color: #fff;
        }
        
        .deep-think-btn-stop {
            background: #21262d;
            border: 1px solid #f85149;
            color: #f85149;
        }
        
        .deep-think-stop-btn .stButton button {
            background-color: #3d1515 !important;
            border-color: #f85149 !important;
        }

        .deep-think-stop-btn .stButton button:hover {
            background-color: #f85149 !important;
            box-shadow: 0 0 15px rgba(248, 81, 73, 0.6) !important;
        }

        /* Deep Think Sleep Button Special Style */
        .deep-think-sleep-btn .stButton button {
            background-color: #1a3a5c !important;
            border-color: #58a6ff !important;
        }

        .deep-think-sleep-btn .stButton button:hover {
            background-color: #58a6ff !important;
            box-shadow: 0 0 15px rgba(88, 166, 255, 0.6) !important;
        }
        
        /* --- DEEP THINK MENU --- */
        .deep-think-menu {
            background-color: var(--card-bg) !important;
            border: 1px solid var(--accent-green) !important;
            border-radius: 8px !important;
            padding: 20px !important;
            margin: 20px 0 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        }

        .deep-think-menu h3 {
            color: #fff !important;
            font-weight: 600 !important;
            margin-bottom: 15px !important;
            border-bottom: 1px solid var(--border-color) !important;
            padding-bottom: 10px !important;
        }

        .deep-think-buttons {
            display: flex !important;
            gap: 10px !important;
            flex-wrap: wrap !important;
            margin-top: 15px !important;
        }

        .deep-think-buttons .stButton button {
            background-color: #21262d !important;
            color: #fff !important;
            border: 1px solid var(--accent-green) !important;
            border-radius: 6px !important;
            padding: 12px 20px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out !important;
            min-width: 160px !important;
            flex: 1 !important;
        }

        .deep-think-buttons .stButton button:hover {
            background-color: var(--accent-green) !important;
            box-shadow: 0 0 15px rgba(46, 160, 67, 0.6) !important;
            transform: translateY(-2px) !important;
        }

        .deep-think-buttons .stButton button:active {
            transform: translateY(0) !important;
        }

        /* Deep Think Selectbox Styling */
        .deep-think-buttons .stSelectbox > div > div {
            background-color: #21262d !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 6px !important;
        }

        .deep-think-buttons .stSelectbox label {
            color: var(--text-secondary) !important;
            font-size: 0.9rem !important;
        }

        /* Pagination styling */
        .pagination-container {
            background: linear-gradient(135deg, rgba(22, 27, 34, 0.8) 0%, rgba(13, 17, 23, 0.9) 100%) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            padding: 15px !important;
            margin: 10px 0 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        }

        .pagination-container .stButton button {
            background: linear-gradient(135deg, rgba(26, 92, 32, 0.2) 0%, rgba(22, 27, 34, 0.8) 100%) !important;
            border: 1px solid var(--accent-green) !important;
            border-radius: 6px !important;
            font-size: 0.9rem !important;
            padding: 8px 12px !important;
            min-width: 80px !important;
            text-align: center !important;
        }

        .pagination-container .stButton button:hover {
            background: linear-gradient(135deg, rgba(46, 160, 67, 0.3) 0%, rgba(22, 27, 34, 0.9) 100%) !important;
            box-shadow: 0 2px 8px rgba(46, 160, 67, 0.4) !important;
        }

        .pagination-container .stNumberInput input {
            background-color: var(--card-bg) !important;
            color: var(--text-primary) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 4px !important;
            padding: 8px !important;
        }

        /* ============================================ */
        /* RESPONSIVE DESIGN & MOBILE OPTIMIZATION */
        /* ============================================ */
        
        /* Standard: Show Desktop, Hide Mobile */
        .desktop-only {
            display: block !important;
        }
        .mobile-only {
            display: none !important;
        }

        @media screen and (max-width: 768px) {
            /* Toggle visibility */
            .desktop-only {
                display: none !important;
            }
            .mobile-only {
                display: block !important;
            }
            
            /* Better font scaling on mobile */
            h2 {
                font-size: 1.5rem !important;
            }
            
            /* Status Cards auto-stacking adjustments */
            .status-card-container {
                margin-bottom: 10px !important;
            }
            
            /* Ensure buttons in mobile menu take full width */
            .mobile-only button {
                width: 100% !important;
                margin: 5px 0 !important;
            }
            
            /* Adjust Top padding for mobile to save space */
             [data-testid="stMain"] {
                padding-top: 50px !important;
             }
        }

    </style>
    """, unsafe_allow_html=True)
