import streamlit as st
import PyPDF2
import google.generativeai as genai
import pandas as pd
import json
import time  # Added to pause between CVs

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="AI CV Screener", page_icon="📄", layout="wide")
st.title("📄 AI CV Screening & Ranking Agent")
st.markdown("Upload a Job Description and multiple CVs to automatically rank candidates based on your custom criteria.")

# --- 2. SIDEBAR: SETTINGS & WEIGHTS ---
st.sidebar.header("1. API Configuration")
api_key = st.sidebar.text_input("Enter Google Gemini API Key", type="password")

st.sidebar.header("2. Scoring Weights (%)")
st.sidebar.markdown("Ensure the total equals 100%.")
weight_skills = st.sidebar.slider("Technical Skills Match", 0, 100, 50)
weight_exp = st.sidebar.slider("Years of Experience", 0, 100, 30)
weight_edu = st.sidebar.slider("Education/Certifications", 0, 100, 20)

req_experience = st.sidebar.number_input("Minimum Required Experience (Years)", min_value=0, max_value=30, value=3)

total_weight = weight_skills + weight_exp + weight_edu
if total_weight != 100:
    st.sidebar.error(f"Total weight is {total_weight}%. It must be exactly 100%.")

# --- 3. HELPER FUNCTIONS ---
def extract_text_from_pdf(uploaded_file):
    reader = PyPDF2.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def analyze_cv_with_gemini(jd_text, cv_text, api_key):
    genai.configure(api_key=api_key)
    # Using the updated model to prevent 404 errors
    model = genai.GenerativeModel('gemini-3.8-flash')
    
    prompt = f"""
    You are an expert HR recruiter. Compare the candidate's CV against the Job Description.
    Return ONLY a valid JSON object (no markdown, no quotes around the JSON) with this exact structure:
    {{
        "years_of_experience": <float, total professional years found. Put 0 if none>,
        "skills_match_score": <int 0-100, how well skills align with JD>,
        "education_match_score": <int 0-100, how well education aligns with JD>,
        "key_strength": "<string, one sentence summarizing their best fit>"
    }}
    
    Job Description:
    {jd_text}
    
    Candidate CV:
    {cv_text}
    """
    try:
        response = model.generate_content(prompt)
        # Clean up output just in case the AI wraps it in markdown blocks
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        # This will reveal the exact error if the AI fails again
        st.error(f"Error reading CV: {e}") 
        return None

# --- 4. MAIN INTERFACE ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("3. Upload Job Description (JD)")
    jd_file = st.file_uploader("Upload JD as PDF", type=["pdf"], key="jd")

with col2:
    st.subheader("4. Upload Candidate CVs")
    cv_files = st.file_uploader("Upload multiple CVs (PDF)", type=["pdf"], accept_multiple_files=True, key="cvs")

# --- 5. EXECUTION & SCORING ---
if st.button("🚀 Run Screening", type="primary"):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif total_weight != 100:
        st.error("Please adjust the weights in the sidebar to equal exactly 100%.")
    elif not jd_file or not cv_files:
        st.error("Please upload both a Job Description and at least one CV.")
    else:
        with st.spinner("Analyzing candidates... This will take about 15 seconds per CV."):
            jd_text = extract_text_from_pdf(jd_file)
            results = []
            
            # Create a progress bar
            progress_bar = st.progress(0)
            
            for i, cv_file in enumerate(cv_files):
                cv_text = extract_text_from_pdf(cv_file)
                analysis = analyze_cv_with_gemini(jd_text, cv_text, api_key)
                
                if analysis:
                    # Calculate Experience Score (Caps at 100)
                    years_exp = analysis.get("years_of_experience", 0)
                    exp_score = min(100, (years_exp / req_experience) * 100) if req_experience > 0 else 100
                    
                    # Get other scores
                    skills_score = analysis.get("skills_match_score", 0)
                    edu_score = analysis.get("education_match_score", 0)
