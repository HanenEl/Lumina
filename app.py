import os
import json
from datetime import datetime, timezone
from typing import Optional, List

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import requests
from PIL import Image
from pydantic import BaseModel
from google import genai
from google.genai import types

from styles import load_styles

# Page Setup
st.set_page_config(
    page_title="LUMINA | AI Skincare Assistant",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)
load_styles()

if "GEMINI_API_KEY" not in os.environ:
    try:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    
if "PRODUCT_ANALYSIS_URL" not in os.environ:
    try:
        os.environ["PRODUCT_ANALYSIS_URL"] = st.secrets["PRODUCT_ANALYSIS_URL"]
    except Exception:
        pass
if "PRODUCT_ANALYSIS_API_KEY" not in os.environ:
    try:
        os.environ["PRODUCT_ANALYSIS_API_KEY"] = st.secrets["PRODUCT_ANALYSIS_API_KEY"]
    except Exception:
        pass

PRODUCT_ANALYSIS_URL = os.environ.get("PRODUCT_ANALYSIS_URL", "")
PRODUCT_ANALYSIS_API_KEY = os.environ.get("PRODUCT_ANALYSIS_API_KEY", "")
PRODUCT_TYPES = ["Cleanser", "Moisturizer", "Serum", "Toner", "Sunscreen", "Face Oil", "Exfoliant", "Mask"]

# Session State
state_defaults = {
    "profile_submitted": False,
    "analysis_completed": False,
    "assessment_started": False,
    "basic_nickname": "",
    "basic_age_range": "Under 18",
    "basic_gender": "Female",
    "wizard_step": 0,
    "wizard_answers": {},
    "skin_profile": None,
    "product_analysis_result": None,
}
for key, val in state_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

GEMINI_MODEL = "gemini-3.5-flash-lite"

class SkinTypeResult(BaseModel):
    value: str
    confidence: float
    source: str

class SensitivityResult(BaseModel):
    value: str
    confidence: float

class VisibleConcern(BaseModel):
    name: str
    severity: str

class GeminiSkinAssessment(BaseModel):
    skin_type: SkinTypeResult
    sensitivity: SensitivityResult
    visible_concerns: List[VisibleConcern]
    observations: List[str]
    summary: str

def _build_gemini_prompt(questionnaire: dict, has_image: bool) -> str:
    image_instruction = (
        "A face photo is attached — use visible skin texture, shine, redness, and pore size as additional evidence alongside the questionnaire."
        if has_image
        else "No face photo was provided — base the assessment on the questionnaire answers alone, and reflect that lower certainty in the confidence scores."
    )
    return f"""You are a dermatological analysis engine. Analyze the user's skin based on their questionnaire answers{" and the attached face photo" if has_image else ""}.

{image_instruction}

Questionnaire answers (raw, as submitted):
{json.dumps(questionnaire, ensure_ascii=False, indent=2)}

Describe the CURRENT STATE of the skin only. Do not suggest products, ingredients, or a routine — that is out of scope for this assessment.

Return your assessment strictly matching the required response schema."""

def _empty_assessment(reason: str) -> dict:
    return {
        "skin_type": {"value": "Unavailable", "confidence": 0.0, "source": "error"},
        "sensitivity": {"value": "Unavailable", "confidence": 0.0},
        "visible_concerns": [],
        "observations": [],
        "summary": f"Analysis failed: {reason}",
    }

def generate_skin_profile(basic_info: dict, questionnaire: dict, uploaded_image=None) -> dict:
    has_image = uploaded_image is not None
    error_message = None

    try:
        client = genai.Client()
        contents = []
        if has_image:
            contents.append(Image.open(uploaded_image))
        contents.append(_build_gemini_prompt(questionnaire, has_image))

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiSkinAssessment,
            ),
        )
        assessment = GeminiSkinAssessment.model_validate_json(response.text).model_dump()
    except Exception as exc:
        error_message = str(exc)
        assessment = _empty_assessment(error_message)

    return {
        "profile_version": "1.0",
        "error": error_message,
        "user": {
            "nickname": basic_info.get("nickname") or "Guest",
            "age_range": basic_info.get("age_range"),
            "gender": basic_info.get("gender"),
        },
        "skin_profile": assessment,
        "special_considerations": {
            "pregnant": questionnaire.get("pregnancy_status"),
        },
        "analysis_metadata": {
            "analysis_source": ["Questionnaire", "Face Image"] if has_image else ["Questionnaire"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

def _empty_product_analysis(reason: str) -> dict:
    return {
        "is_suitable": "Use with Caution",
        "why_suitable_or_not": f"We couldn't complete the analysis: {reason}",
        "key_beneficial_ingredients": [],
        "concerning_ingredients": [],
        "usage_routine": "N/A",
        "daily_use_suitability": "N/A",
        "product_type": "N/A",
        "error": reason,
    }

def analyze_product_via_api(uploaded_image, product_type: str) -> dict:
    if not PRODUCT_ANALYSIS_URL:
        res = _empty_product_analysis("The product-analysis server URL isn't configured yet (PRODUCT_ANALYSIS_URL).")
        res["product_type"] = product_type
        return res

    profile = st.session_state.skin_profile or {}
    skin = profile.get("skin_profile", {}) or {}
    skin_type_value = (skin.get("skin_type") or {}).get("value") or "normal"
    pregnancy_status = profile.get("special_considerations", {}).get("pregnant")

    conditions_list = []
    sensitivity_value = str((skin.get("sensitivity") or {}).get("value", "")).lower()
    if sensitivity_value and sensitivity_value not in ("low", "none", "unavailable", ""):
        conditions_list.append("Sensitive Skin - Fragrance Sensitive")

    for concern in skin.get("visible_concerns", []) or []:
        name = concern.get("name")
        if name:
            conditions_list.append(name)

    form_data = {
        "skin_type": str(skin_type_value).lower(),
        "pregnant": "true" if pregnancy_status == "Yes" else "false",
        "conditions": json.dumps(conditions_list),
        "product_type": product_type,
    }
    files = {
        "image": (uploaded_image.name, uploaded_image.getvalue(), uploaded_image.type or "image/jpeg"),
    }
    headers = {"Authorization": f"Bearer {PRODUCT_ANALYSIS_API_KEY}"}

    try:
        res = requests.post(PRODUCT_ANALYSIS_URL, headers=headers, data=form_data, files=files, timeout=180)
    except requests.exceptions.RequestException as e:
        err_res = _empty_product_analysis(f"Could not reach the analysis server: {e}")
        err_res["product_type"] = product_type
        return err_res

    if res.status_code == 200:
        data = res.json()
        data["product_type"] = product_type
        return data

    try:
        detail = res.json().get("detail", res.text)
    except Exception:
        detail = res.text
    err_res = _empty_product_analysis(f"Request failed ({res.status_code}): {detail}")
    err_res["product_type"] = product_type
    return err_res

# Header
st.markdown(
    """
    <div style="text-align: center; padding: 0.5rem 0;">
        <span style="font-size: 0.75rem; letter-spacing: 0.2em; color: #A67C52; text-transform: uppercase;">AI Skincare Intelligence</span>
        <h1 style="margin: 0.2rem 0;">L U M I N A</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["Home", "Skin Profile", "Skin Analysis"])

# TAB 1: HOME
with tab1:
    st.markdown(
        """
        <div style="text-align: center; max-width: 650px; margin: 2rem auto 3rem auto;">
            <h2>Personalized Dermatological Science</h2>
            <p style="color: #777777; line-height: 1.6;">
                Lumina analyzes ingredient formulations against your unique skin profile to predict compatibility, prevent irritation, and optimize your routine.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="simple-card"><h3>1. Profile</h3><p style="color: #777777; font-size: 0.85rem;">Define your skin type, primary concerns, and daily lifestyle factors.</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="simple-card"><h3>2. Scan</h3><p style="color: #777777; font-size: 0.85rem;">Upload any product ingredient label for instant optical extraction.</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="simple-card"><h3>3. Results</h3><p style="color: #777777; font-size: 0.85rem;">Get clear compatibility scores and personalized usage guidance.</p></div>', unsafe_allow_html=True)

# TAB 2: SKIN PROFILE
def get_dynamic_question_list():
    questions = [{"id": "knows_type", "title": "Skin Type Knowledge", "question": "Do you already know your skin type?", "options": ["Yes", "No"]}]
    
    if st.session_state.wizard_answers.get("knows_type", "Yes") == "Yes":
        questions.append({"id": "known_skin_type", "title": "Select Skin Type", "question": "Which classification best fits your skin?", "options": ["Normal", "Dry", "Oily", "Combination"]})
    else:
        questions.extend([
            {"id": "cleansing_feel", "title": "Cleansing Feel", "question": "How does your skin feel after cleansing?", "options": ["Balanced", "Tight & dry", "Slick & oily", "Oily in T-zone, dry elsewhere"]},
            {"id": "facial_shine", "title": "Facial Shine", "question": "Does your face become shiny within a few hours?", "options": ["Rarely or never", "Only in T-zone", "All over face"]},
            {"id": "uneven_areas", "title": "Uneven Oiliness", "question": "Are some areas oily while others are dry?", "options": ["No, uniform", "Yes, combination"]},
            {"id": "skin_tightness", "title": "Skin Tightness", "question": "How often does your skin feel tight?", "options": ["Rarely", "Often after washing", "Constantly"]}
        ])

    questions.extend([
        {"id": "sens_redness", "title": "Sensitivity Check", "question": "Does your skin often become red after using skincare?", "options": ["No", "Yes"]},
        {"id": "sens_irritation", "title": "Sensitivity Check", "question": "Do new products frequently cause irritation?", "options": ["No", "Yes"]},
        {"id": "sens_stinging", "title": "Sensitivity Check", "question": "Does your skin sting or burn easily?", "options": ["No", "Yes"]}
    ])

    if st.session_state.basic_gender == "Female" and st.session_state.basic_age_range != "Under 18":
        questions.append({"id": "pregnancy_status", "title": "Special Considerations", "question": "Are you currently pregnant?", "options": ["No", "Yes", "Prefer not to say"]})

    questions.append({"id": "face_analysis", "title": "Improve Your Analysis (Optional)", "question": "Upload a clear face photo to help detect visible skin concerns.", "type": "upload"})
    return questions

# TAB 2: SKIN PROFILE
with tab2:
    if not st.session_state.profile_submitted:
        st.markdown("<h2 style='text-align: center; margin-bottom: 1rem;'>Your Skin Profile Setup</h2>", unsafe_allow_html=True)
        with st.container(key="profile-card"):
            st.markdown("<h3>Step 1 — Basic Information</h3>", unsafe_allow_html=True)
            c_name, c_age, c_gender = st.columns(3)
            
            with c_name:
                st.session_state.basic_nickname = st.text_input("Nickname", value=st.session_state.basic_nickname, placeholder="Enter your nickname")
            with c_age:
                st.session_state.basic_age_range = st.selectbox("Age Range", ["Under 18", "18–24", "25–34", "35–44", "45–54", "55+"], index=["Under 18", "18–24", "25–34", "35–44", "45–54", "55+"].index(st.session_state.basic_age_range))
            with c_gender:
                st.session_state.basic_gender = st.selectbox("Gender", ["Female", "Male", "Prefer not to say"], index=["Female", "Male", "Prefer not to say"].index(st.session_state.basic_gender))

            st.markdown("<br>", unsafe_allow_html=True)
            _, c_mid, _ = st.columns([1.5, 1, 1.5])
            with c_mid:
                if st.button("Start Skin Assessment", use_container_width=True):
                    st.session_state.assessment_started = True
                    st.session_state.wizard_step = 0

            if st.session_state.assessment_started:
                st.markdown("<hr style='border: 0; border-top: 1px solid #ECE7E1; margin: 2rem 0;'>", unsafe_allow_html=True)
                question_flow = get_dynamic_question_list()
                
                if st.session_state.wizard_step >= len(question_flow):
                    st.session_state.wizard_step = len(question_flow) - 1

                current_idx = st.session_state.wizard_step
                current_q = question_flow[current_idx]
                total_questions = len(question_flow)

                st.progress(float(current_idx + 1) / float(total_questions))
                st.markdown(f"<h3>Step 2 — {current_q['title']}</h3>", unsafe_allow_html=True)
                st.markdown(f"<p style='color: #777777; font-size: 0.85rem; margin-top: -0.5rem; margin-bottom: 1.5rem;'>Question {current_idx + 1} of {total_questions}</p>", unsafe_allow_html=True)

                q_id = current_q["id"]
                if current_q.get("type", "choice") == "choice":
                    default_ans = st.session_state.wizard_answers.get(q_id, current_q["options"][0])
                    if default_ans not in current_q["options"]:
                        default_ans = current_q["options"][0]
                    st.session_state.wizard_answers[q_id] = st.radio(current_q["question"], current_q["options"], index=current_q["options"].index(default_ans), horizontal=True, key=f"rad_{q_id}_{current_idx}")
                else:
                    st.markdown(f"<p><b>{current_q['question']}</b></p>", unsafe_allow_html=True)
                    uploaded_photo = st.file_uploader("", type=["jpg", "png", "jpeg"], key="wizard_photo_upload")
                    if uploaded_photo:
                        st.session_state.wizard_answers["uploaded_photo"] = uploaded_photo

                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                btn_col1, _, btn_col2 = st.columns([1, 4, 1])

                with btn_col1:
                    if current_idx > 0 and st.button("Back", key="wiz_back_btn"):
                        st.session_state.wizard_step -= 1
                        st.rerun()

                with btn_col2:
                    if current_idx < total_questions - 1:
                        if st.button("Next", key="wiz_next_btn"):
                            st.session_state.wizard_step += 1
                            st.rerun()
                    else:
                        if st.button("Save Profile", key="wiz_finish_btn"):
                            basic_info = {"nickname": st.session_state.basic_nickname, "age_range": st.session_state.basic_age_range, "gender": st.session_state.basic_gender}
                            questionnaire_answers = {k: v for k, v in st.session_state.wizard_answers.items() if k != "uploaded_photo"}
                            st.session_state.skin_profile = generate_skin_profile(basic_info, questionnaire_answers, st.session_state.wizard_answers.get("uploaded_photo"))
                            st.session_state.profile_submitted = True
                            st.rerun()
    else:
        profile = st.session_state.skin_profile
        skin = profile.get("skin_profile", {}) or {}
        skin_type = skin.get("skin_type", {}) or {}
        sensitivity = skin.get("sensitivity", {}) or {}

        head_col1, head_col2 = st.columns([3, 1])
        with head_col1:
            st.markdown("<h2 style='margin-bottom: 0;'>Skin Profile Dashboard</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #777777; font-size: 0.9rem;'>Your active profile summary</p>", unsafe_allow_html=True)
        with head_col2:
            st.markdown("<div style='padding-top: 0.5rem;'>", unsafe_allow_html=True)
            if st.button("Edit Profile", key="edit_profile_btn"):
                st.session_state.profile_submitted = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if profile.get("error"):
            st.error(f"Couldn't generate your profile: {profile['error']}")

        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="simple-card" style="text-align:center;"><span>User</span><h3>{profile.get("user", {}).get("nickname", "Guest")}</h3></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="simple-card" style="text-align:center;"><span>Skin Type</span><h3>{skin_type.get("value", "N/A")}</h3></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="simple-card" style="text-align:center;"><span>Sensitivity</span><h3>{sensitivity.get("value", "N/A")}</h3></div>', unsafe_allow_html=True)
        with m4:
            st.markdown(f'<div class="simple-card" style="text-align:center;"><span>Gender</span><h3>{profile.get("user", {}).get("gender", "N/A")}</h3></div>', unsafe_allow_html=True)

        with st.container(key="profile-details-card"):
            st.markdown("<h3>Dermatological Assessment</h3>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: #2B2B2B; line-height: 1.6;'>{skin.get('summary', '')}</p>", unsafe_allow_html=True)

            if skin.get("observations"):
                st.markdown("<br><b>Observations:</b>", unsafe_allow_html=True)
                for obs in skin.get("observations"):
                    st.markdown(f"<p style='color: #777777; margin: 0.2rem 0;'>• {obs}</p>", unsafe_allow_html=True)

            if skin.get("visible_concerns"):
                st.markdown("<br><b>Visible Concerns:</b>", unsafe_allow_html=True)
                concerns_html = "".join(f'<span class="badge">{c.get("name", "")} — {c.get("severity", "")}</span>' for c in skin.get("visible_concerns"))
                st.markdown(concerns_html, unsafe_allow_html=True)

            pregnant = profile.get("special_considerations", {}).get("pregnant")
            if pregnant and pregnant != "No":
                st.markdown(f"<br><p><b>Special Considerations:</b></p><p style='color: #777777;'>Pregnancy status: {pregnant}</p>", unsafe_allow_html=True)

            st.markdown("<br><p style='font-size: 0.8rem; color: #8C827A; text-align: right; font-weight: 300; letter-spacing: 0.3px;'>Based on your assessment & photo scan</p>", unsafe_allow_html=True)

# TAB 3: SKIN ANALYSIS
with tab3:
    if not st.session_state.analysis_completed:
        st.markdown("<h2 style='text-align: center; margin-bottom: 1rem;'>Analyze Your Product</h2>", unsafe_allow_html=True)

        with st.container(key="upload-main-card"):
            col_info, col_divider, col_upload = st.columns([0.47, 0.06, 0.47], gap="small")

            with col_info:
                st.markdown("<h3 class='serif-heading' style='font-size: 1.45rem; margin-bottom: 0.9rem;'>How Product Analysis Works</h3>", unsafe_allow_html=True)
                st.markdown("<p class='sans-body' style='font-size: 0.86rem; line-height: 1.65; margin-bottom: 2.2rem;'>Lumina extracts the ingredient list using OCR and AI, then compares the detected ingredients with your skin profile to determine whether the product is suitable.</p>", unsafe_allow_html=True)
                st.markdown("<p style='font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #B57A3A; margin-bottom: 1rem;'>PHOTO TIPS</p>", unsafe_allow_html=True)
                
                check_svg = '''<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#B57A3A" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="16 9 10.5 14.5 8 12"></polyline></svg>'''
                tips = ["Capture only the ingredient list.", "Use good lighting.", "Keep the text fully visible.", "Avoid blurry images.", "Crop unnecessary background."]
                tips_html = "".join([f'<div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.85rem;"><span style="display: flex; align-items: center;">{check_svg}</span><span class="sans-body" style="font-size: 0.86rem;">{tip}</span></div>' for tip in tips])
                st.markdown(f'<div style="line-height: 1.2;">{tips_html}</div>', unsafe_allow_html=True)

            with col_divider:
                st.markdown('<div style="border-left: 1px solid #E8E5E2; height: 100%; min-height: 380px; margin: 0 auto; width: 1px;"></div>', unsafe_allow_html=True)

            with col_upload:
                st.markdown("<h3 class='serif-heading' style='font-size: 1.45rem; text-align: center; margin-bottom: 1.2rem;'>Upload Product Label</h3>", unsafe_allow_html=True)
                img = st.file_uploader("Product Image", type=["jpg", "jpeg", "png"], key="prod", label_visibility="collapsed")
                selected_product_type = st.selectbox("Product Type", PRODUCT_TYPES, key="product_type_select", label_visibility="collapsed")

                if not st.session_state.profile_submitted:
                    st.markdown("<p class='sans-body' style='text-align: center; color: #B57A3A; font-size: 0.78rem;'>Tip: complete your Skin Profile in the previous tab first for a personalized result.</p>", unsafe_allow_html=True)

                btn_col1, btn_col2, btn_col3 = st.columns([0.22, 0.6, 0.15])
                with btn_col2:
                    if st.button("ANALYZE PRODUCT", disabled=(img is None), key="analyze_btn"):
                        with st.spinner("Analyzing your product..."):
                            result = analyze_product_via_api(img, selected_product_type)
                            st.session_state.product_analysis_result = result
                            st.session_state.analysis_completed = True
                            st.rerun()

                st.markdown("<p class='sans-body' style='text-align: center; color: #888888; font-size: 0.81rem; margin-top: 0.8rem;'>Upload an image to enable analysis</p>", unsafe_allow_html=True)

    else:
        data = st.session_state.get("product_analysis_result") or {}

        if data.get("error"):
            st.error(f"Analysis issue: {data['error']}")

        raw_suitability = str(data.get("is_suitable", "Use with Caution")).lower()

        if raw_suitability in ("yes", "recommended"):
            recommendation_title = "Recommended"
            title_color = "#2E7D32"
            explanation_text = "This product formulation aligns well with your skin profile and active concerns."
        elif raw_suitability in ("no", "not recommended"):
            recommendation_title = "Not Recommended"
            title_color = "#C62828"
            explanation_text = "This formulation contains key ingredients that may cause irritation or contraindicate your profile."
        else:
            recommendation_title = "Use with Caution"
            title_color = "#A67C52"
            explanation_text = "This formulation is generally compatible but contains ingredients requiring localized patch testing."

        prod_type = data.get("product_type", "Moisturizer")
        daily_use = data.get("daily_use_suitability", "Daily")
        beneficial_list = data.get("key_beneficial_ingredients", [])

        st.markdown('<div class="results-wrapper">', unsafe_allow_html=True)
        with st.container(key="product-results-card"):
            # 1. Recommendation Hero
            st.markdown(
                f"""
                <div class="recommendation-hero-card">
                    <h2 style="margin: 0 0 0.3rem 0; color: {title_color}; font-size: 1.8rem; font-weight: 400;">{recommendation_title}</h2>
                    <p style="margin: 0; color: #777777; font-size: 0.85rem; line-height: 1.5;">{explanation_text}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 2. Summary Cards
            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.markdown(f'<div class="simple-card" style="text-align:center; padding: 1rem !important;"><span>Product Type</span><h3 style="font-size: 1.2rem !important; margin: 0.2rem 0 0 0;">{prod_type}</h3></div>', unsafe_allow_html=True)
            with rc2:
                st.markdown(f'<div class="simple-card" style="text-align:center; padding: 1rem !important;"><span>Daily Use</span><h3 style="font-size: 1.2rem !important; margin: 0.2rem 0 0 0;">{daily_use}</h3></div>', unsafe_allow_html=True)
            with rc3:
                st.markdown(f'<div class="simple-card" style="text-align:center; padding: 1rem !important;"><span>Beneficial Ingredients</span><h3 style="font-size: 1.2rem !important; margin: 0.2rem 0 0 0;">{len(beneficial_list)} Ingredients</h3></div>', unsafe_allow_html=True)

            st.markdown("<hr style='border: 0; border-top: 1px solid #ECE7E1; margin: 1.2rem 0;'>", unsafe_allow_html=True)

            # 3. Why This Recommendation
            st.markdown("<h3 style='font-size: 1.25rem !important;'>Why This Recommendation</h3>", unsafe_allow_html=True)
            st.markdown(f'<p style="color: #2B2B2B; font-size: 0.88rem; line-height: 1.5; margin-top: 0.3rem;">{data.get("why_suitable_or_not", "")}</p>', unsafe_allow_html=True)

            st.markdown("<hr style='border: 0; border-top: 1px solid #ECE7E1; margin: 1.2rem 0;'>", unsafe_allow_html=True)

            # 4. Beneficial Ingredients
            st.markdown("<h3 style='font-size: 1.25rem !important;'>Key Beneficial Ingredients</h3>", unsafe_allow_html=True)
            if beneficial_list:
                pills = "".join([f'<span class="pill-beneficial">{i}</span>' for i in beneficial_list])
                st.markdown(f'<div style="margin-top: 0.4rem;">{pills}</div>', unsafe_allow_html=True)
            else:
                st.markdown("<p style='color: #777777; font-size: 0.85rem; margin-top: 0.3rem;'>No specific key beneficial ingredients detected.</p>", unsafe_allow_html=True)

            st.markdown("<hr style='border: 0; border-top: 1px solid #ECE7E1; margin: 1.2rem 0;'>", unsafe_allow_html=True)

            # 5. Concerning Ingredients
            st.markdown("<h3 style='font-size: 1.25rem !important;'>Concerning Ingredients</h3>", unsafe_allow_html=True)
            concerning = data.get("concerning_ingredients", [])
            if concerning:
                concerns = "".join([f'<span class="pill-warning">{i}</span>' for i in concerning])
                st.markdown(f'<div style="margin-top: 0.4rem;">{concerns}</div>', unsafe_allow_html=True)
            else:
                st.markdown("<p style='color: #777777; font-size: 0.85rem; margin-top: 0.3rem;'>No concerning ingredients detected for your skin profile.</p>", unsafe_allow_html=True)

            st.markdown("<hr style='border: 0; border-top: 1px solid #ECE7E1; margin: 1.2rem 0;'>", unsafe_allow_html=True)

            # 6. Usage Routine
            st.markdown("<h3 style='font-size: 1.25rem !important;'>Usage Routine</h3>", unsafe_allow_html=True)
            st.markdown(f'<p style="color: #2B2B2B; font-size: 0.88rem; line-height: 1.5; margin-top: 0.3rem;">{data.get("usage_routine", "N/A")}</p>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        _, btn_col2, _ = st.columns([0.3, 0.4, 0.3])
        with btn_col2:
            if st.button("ANALYZE ANOTHER PRODUCT", key="reset_btn"):
                st.session_state.analysis_completed = False
                st.session_state.product_analysis_result = None
                st.rerun()

# Footer
st.markdown('<div style="text-align: center; color: #777777; font-size: 0.75rem; margin-top: 4rem;">© 2026 LUMINA BEAUTY INC.</div>', unsafe_allow_html=True)