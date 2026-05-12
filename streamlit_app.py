import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
import docx
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os

# -----------------------------------
# PAGE CONFIG
# -----------------------------------
st.set_page_config(
    page_title="Naval Defence Tech Watch",
    layout="wide"
)

st.title("Naval Defence Tech Watch System")
st.caption("Repository + Living Assessments + Weekly Brief Generator")

# -----------------------------------
# OPENAI CLIENT
# -----------------------------------
client = OpenAI(
    api_key=st.secrets["OPENAI_API_KEY"]
)

# -----------------------------------
# FILES
# -----------------------------------
DEVELOPMENTS_FILE = "developments.csv"
ASSESSMENTS_FILE = "assessments.csv"

# -----------------------------------
# HELPERS
# -----------------------------------
def read_pdf(file):
    reader = PdfReader(file)
    text = ""

    for page in reader.pages:
        text += page.extract_text() or ""
        text += "\n"

    return text


def read_docx(file):
    document = docx.Document(file)
    return "\n".join(p.text for p in document.paragraphs)


def read_txt(file):
    return file.read().decode("utf-8")


def read_website(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    for tag in soup([
        "script",
        "style",
        "nav",
        "footer",
        "header"
    ]):
        tag.decompose()

    text = soup.get_text(separator="\n")

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    return "\n".join(lines)


def ask_chatgpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


def save_csv(file_name, record):
    df_new = pd.DataFrame([record])

    if os.path.exists(file_name):
        df_old = pd.read_csv(file_name)
        df_all = pd.concat(
            [df_old, df_new],
            ignore_index=True
        )
    else:
        df_all = df_new

    df_all.to_csv(file_name, index=False)


def load_csv(file_name):
    if os.path.exists(file_name):
        return pd.read_csv(file_name)

    return pd.DataFrame()

# -----------------------------------
# TABS
# -----------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "Add Development",
    "Repository",
    "Living Assessment",
    "Weekly Brief"
])

# ===================================
# TAB 1
# ===================================
with tab1:

    st.header("Add Development")

    input_type = st.radio(
        "Choose input type",
        [
            "Website link",
            "Upload document",
            "Paste text"
        ]
    )

    article_text = ""
    source = ""

    # -------------------------------
    # WEBSITE
    # -------------------------------
    if input_type == "Website link":

        url = st.text_input(
            "Paste website link"
        )

        if st.button("Read Website"):

            try:
                article_text = read_website(url)

                st.session_state["article_text"] = article_text
                st.session_state["source"] = url

                st.success("Website loaded.")

            except Exception as e:
                st.error("Could not read website.")
                st.exception(e)

        article_text = st.session_state.get(
            "article_text",
            ""
        )

        source = st.session_state.get(
            "source",
            ""
        )

    # -------------------------------
    # DOCUMENT
    # -------------------------------
    elif input_type == "Upload document":

        uploaded_file = st.file_uploader(
            "Upload PDF, DOCX, TXT",
            type=["pdf", "docx", "txt"]
        )

        if uploaded_file:

            source = uploaded_file.name

            try:

                if uploaded_file.name.endswith(".pdf"):
                    article_text = read_pdf(uploaded_file)

                elif uploaded_file.name.endswith(".docx"):
                    article_text = read_docx(uploaded_file)

                else:
                    article_text = read_txt(uploaded_file)

                st.success("Document loaded.")

            except Exception as e:
                st.error("Could not read document.")
                st.exception(e)

    # -------------------------------
    # PASTE TEXT
    # -------------------------------
    else:

        article_text = st.text_area(
            "Paste article text",
            height=300
        )

        source = "Manual paste"

    # -------------------------------
    # PREVIEW
    # -------------------------------
    if article_text:

        st.subheader("Preview")

        st.text_area(
            "Extracted text",
            article_text[:5000],
            height=250
        )

        # ---------------------------
        # ANALYSE
        # ---------------------------
        if st.button("Analyse and Save"):

            prompt = f"""
You are a naval defence technology watch analyst.

Analyse this development for a naval capability development organisation.

Return:

Title:
Date:
Source:
Main topic:
Sub-topic:
Actors:
Country:
Type of development:
Maturity level:
Importance score:
Executive summary:
What happened:
Why it matters:
Naval relevance:
Unmanned systems relevance:
Tech stack layer:
Evidence quality:
Risks:
Impact on existing assessment:
Open questions:
Recommended action:

Article:
{article_text[:12000]}
"""

            try:

                output = ask_chatgpt(prompt)

                st.subheader("AI Assessment")

                st.write(output)

                record = {
                    "timestamp": datetime.now(),
                    "source": source,
                    "analysis": output
                }

                save_csv(
                    DEVELOPMENTS_FILE,
                    record
                )

                st.success(
                    "Development saved to repository."
                )

            except Exception as e:
                st.error(
                    "OpenAI error. Check credits/API key."
                )
                st.exception(e)

# ===================================
# TAB 2
# ===================================
with tab2:

    st.header("Repository")

    df = load_csv(DEVELOPMENTS_FILE)

    if df.empty:

        st.info("No developments yet.")

    else:

        st.dataframe(
            df,
            use_container_width=True
        )

        csv = df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="Download Repository CSV",
            data=csv,
            file_name="developments.csv",
            mime="text/csv"
        )

# ===================================
# TAB 3
# ===================================
with tab3:

    st.header("Living Assessment")

    df = load_csv(DEVELOPMENTS_FILE)

    if df.empty:

        st.info(
            "No developments available."
        )

    else:

        topic = st.text_input(
            "Enter topic",
            placeholder="Example: USV mine warfare"
        )

        if st.button("Generate Assessment"):

            try:

                repository_text = df.to_string(
                    index=False
                )

                prompt = f"""
You are a naval defence technology analyst.

Generate a living assessment using ALL historical repository evidence.

Topic:
{topic}

Use this structure:

1. Current Assessment
2. Evidence Base
3. Maturity Trend
4. Key Actors
5. What Changed Over Time
6. Confidence Level
7. Implications for Our Organisation
8. Open Questions
9. Recommended Actions

Repository:
{repository_text[:20000]}
"""

                assessment = ask_chatgpt(prompt)

                st.subheader(
                    "Living Assessment"
                )

                st.write(assessment)

                record = {
                    "timestamp": datetime.now(),
                    "topic": topic,
                    "assessment": assessment
                }

                save_csv(
                    ASSESSMENTS_FILE,
                    record
                )

                st.success(
                    "Assessment saved."
                )

            except Exception as e:
                st.error("OpenAI error.")
                st.exception(e)

    st.divider()

    st.subheader("Saved Assessments")

    assessments_df = load_csv(
        ASSESSMENTS_FILE
    )

    if assessments_df.empty:

        st.info("No assessments yet.")

    else:

        st.dataframe(
            assessments_df,
            use_container_width=True
        )

# ===================================
# TAB 4
# ===================================
with tab4:

    st.header("Weekly Brief")

    developments_df = load_csv(
        DEVELOPMENTS_FILE
    )

    assessments_df = load_csv(
        ASSESSMENTS_FILE
    )

    if developments_df.empty:

        st.info(
            "No repository data available."
        )

    else:

        if st.button(
            "Generate Weekly Brief"
        ):

            try:

                developments_text = developments_df.to_string(
                    index=False
                )

                assessments_text = assessments_df.to_string(
                    index=False
                )

                prompt = f"""
You are preparing a weekly naval defence technology brief for senior leadership.

The brief must:
- summarise important developments
- explain what changed in our assessment
- explain current state of play
- identify implications
- identify open questions

Use this structure:

Title:
Executive Summary:

1. Key Developments
2. What Changed in Our Assessment
3. Current State of Play
4. Implications for Our Organisation
5. Priority Open Questions
6. Recommended Actions
7. Items to Watch Next Week

Developments:
{developments_text[:20000]}

Assessments:
{assessments_text[:12000]}
"""

                brief = ask_chatgpt(prompt)

                st.subheader(
                    "Weekly Brief"
                )

                st.write(brief)

                st.download_button(
                    label="Download Weekly Brief",
                    data=brief,
                    file_name="weekly_brief.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error("OpenAI error.")
                st.exception(e)
