import streamlit as st

def load_styles():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500&family=Montserrat:wght@300;400;500&display=swap');

        :root {
            --bg: #FAF9F7;
            --card: #FFFFFF;
            --accent: #A67C52;
            --text-dark: #2B2B2B;
            --text-muted: #777777;
            --border: #ECE7E1;
        }

        .stApp {
            background-color: var(--bg) !important;
            font-family: 'Montserrat', sans-serif !important;
            color: var(--text-dark) !important;
        }

        .block-container, .stMainBlockContainer {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        
        header, footer, #MainMenu, .stDeployButton {
            visibility: hidden !important;
            height: 0 !important;
        }

        h1, h2, h3 {
            font-family: 'Cormorant Garamond', serif !important;
            color: var(--text-dark) !important;
            font-weight: 400 !important;
        }

        h1 { font-size: 3rem !important; }
        h2 { font-size: 2rem !important; }
        h3 { font-size: 1.4rem !important; }

        .results-wrapper {
            max-width: 850px;
            margin: 0 auto;
        }

        .simple-card, 
        .st-key-profile-card, 
        .st-key-upload-card, 
        .st-key-detected-card, 
        .st-key-details-card, 
        .st-key-profile-details-card,
        .st-key-product-results-card {
            background: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 2.5rem 2rem !important;
            margin-bottom: 1.5rem !important;
        }

        .recommendation-hero-card {
            background: #FAF8F5;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1.5rem 1.8rem;
            text-align: center;
            margin-bottom: 1.5rem;
        }

        .badge {
            display: inline-block;
            padding: 0.3rem 0.8rem;
            font-size: 0.75rem;
            background: #E8DDD0;
            color: var(--text-dark);
            border-radius: 15px;
            margin: 0.2rem;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
            border-bottom: 1px solid var(--border);
            justify-content: center;
        }

        .stTabs [data-baseweb="tab"] {
            font-family: 'Montserrat', sans-serif !important;
            font-size: 0.85rem !important;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text-muted) !important;
            border: none !important;
        }

        .stTabs [aria-selected="true"] {
            color: var(--text-dark) !important;
            font-weight: 600 !important;
            border-bottom: 2px solid var(--accent) !important;
        }

        div[data-baseweb="tab-highlight"] {
            display: none !important;
            background-color: transparent !important;
        }

        .stButton > button {
            background-color: var(--text-dark) !important;
            color: #FFFFFF !important;
            border-radius: 25px !important;
            padding: 0.6rem 2rem !important;
            border: none !important;
            font-size: 0.8rem !important;
            text-transform: uppercase !important;
            letter-spacing: 0.1em !important;
            width: 100%;
            transition: background 0.3s ease;
        }

        .stButton > button:hover {
            background-color: var(--accent) !important;
        }

        .stTextInput input, .stSelectbox select, .stTextArea textarea {
            border-radius: 8px !important;
            border: 1px solid var(--border) !important;
        }

        .stProgress > div > div > div > div {
            background-color: var(--accent) !important;
        }

        .stProgress > div > div > div {
            background-color: var(--border) !important;
        }

        .st-key-upload-main-card {
            background: var(--card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 20px !important;
            padding: 3.5rem 3rem !important;
            margin: 0 auto 2rem auto !important;
            width: 78% !important;
            max-width: 1000px !important;
            box-shadow: 0px 12px 35px rgba(0, 0, 0, 0.03) !important;
        }

        /* Face Photo Upload Container */
        .face-upload-container {
            width: 380px !important;
            max-width: 100% !important;
            margin-left: 0 !important;
            margin-right: auto !important;
            margin-top: 1rem !important;
        }

        /* Streamlit File Uploader Box Customization */
        div[data-testid="stFileUploader"] {
            width: 380px !important;
            max-width: 100% !important;
            margin-left: 0 !important;
            margin-right: auto !important;
            margin-bottom: 0px !important;
        }

        div[data-testid="stFileUploaderDropzone"],
        section[data-testid="stFileUploaderDropzone"],
        div[data-testid="stFileUploader"] > section {
            background-color: #F8F9FC !important;
            border: 1.5px dashed #D1D5DB !important;
            border-radius: 16px !important;
            padding: 1.5rem 1rem !important;
            min-height: 160px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            gap: 0.4rem !important;
        }

        div[data-testid="stFileUploaderDropzone"]:hover,
        section[data-testid="stFileUploaderDropzone"]:hover {
            border-color: var(--accent) !important;
            background-color: #FAF8F5 !important;
        }

        /* Controlled Vertical Gap for Navigation Spacer */
        .wizard-nav-spacer {
            margin-top: 1.5rem !important;
            height: 0px !important;
        }

        /* Navigation Buttons Styling for Wizard - Compact Spacing */
        .st-key-wiz_back_btn, 
        .st-key-wiz_next_btn, 
        .st-key-wiz_finish_btn {
            margin-top: 0 !important;
            }

        .st-key-wiz_back_btn > button,
        .st-key-wiz_next_btn > button,
        .st-key-wiz_finish_btn > button {
            background-color: #22252A !important;
            color: #FFFFFF !important;
            border-radius: 30px !important;
            padding: 0.65rem 1.8rem !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.12em !important;
            height: 44px !important;
            border: none !important;
        }

        .st-key-wiz_back_btn > button:hover,
        .st-key-wiz_next_btn > button:hover,
        .st-key-wiz_finish_btn > button:hover {
            background-color: var(--accent) !important;
        }

        .st-key-analyze_btn > button {
            width: 300px !important;
            max-width: 100% !important;
            height: 52px !important;
            background-color: #1F2421 !important;
            color: #FFFFFF !important;
            border-radius: 50px !important;
            font-size: 0.78rem !important;
            letter-spacing: 0.16em !important;
            font-weight: 600 !important;
            margin: 1.2rem auto 0 auto !important;
            display: block !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.06) !important;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }

        .st-key-analyze_btn > button:hover {
            background-color: var(--accent) !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(181, 122, 58, 0.25) !important;
        }

        .pill-beneficial {
            display: inline-block;
            padding: 0.45rem 1rem;
            font-size: 0.82rem;
            background: #F0F7F2;
            color: #2E7D32;
            border: 1px solid #D3EAD7;
            border-radius: 20px;
            margin: 0.25rem;
            font-weight: 500;
        }

        .pill-warning {
            display: inline-block;
            padding: 0.45rem 1rem;
            font-size: 0.82rem;
            background: #FDF2F2;
            color: #C62828;
            border: 1px solid #F8D7D7;
            border-radius: 20px;
            margin: 0.25rem;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)