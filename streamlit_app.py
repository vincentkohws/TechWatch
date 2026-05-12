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
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# -----------------------------------
# FILES
# -----------------------------------
DEVELOPMENTS_FILE = "developments.csv"
ASSESSMENTS_FILE = "assessments.csv"

# -----------------------------------
# HELPER FUNCTIONS
# -----------------------------------
def read_pdf(file):
    reader = PdfReader(file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_docx(file):
    document = docx.Document(file)
    return "\n".join(p.text for p in document.paragraphs)


def read_txt(file):
    return file.read().decode("utf-8")


def read_website(url):
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(
        url,
        headers=headers,
        timeout=20
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
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


def load_csv(file_name):
    if os.path.exists(file_name):
        return pd.read_csv(file_name)

    return pd.DataFrame()


def save_csv(file_name, df):
    df.to_csv(file_name, index=False)


def append_record(file_name, record):
    df_new = pd.DataFrame([record])

    if os.path.exists(file_name):
        df_old = pd.read_csv(file_name)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new

    save_csv(file_name, df_all)


def delete_row(file_name, row_number):
    df = load_csv(file_name)

    if df.empty:
        return False

    df = df.drop(row_number)
    df = df.reset_index(drop=True)

    save_csv(file_name, df)

    return True


def clear_file(file_name):
    if os.path.exists(file_name):
        os.remove(file_name)
        return True

    return False


# -----------------------------------
# GLOBAL DELETE / RESET SECTION
# -----------------------------------
with st.expander("Danger Zone: Clear Saved Data"):
    st.warning("Use these buttons only if you want to delete saved records.")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Clear All Developments"):
            clear_file(DEVELOPMENTS_FILE)
            st.success("All developments deleted.")

    with col2:
        if st.button("Clear All Assessments"):
            clear_file(ASSESSMENTS_FILE)
            st.success("All assessments deleted.")

    with col3:
        if st.button("Clear Everything"):
            clear_file(DEVELOPMENTS_FILE)
            clear_file(ASSESSMENTS_FILE)
            st.success("All saved CSV data deleted.")


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
# TAB 1: ADD DEVELOPMENT
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

    if input_type == "Website link":
        url = st.text_input("Paste website link")

        if st.button("Read Website"):
            if not url:
                st.warning("Please paste a website link first.")
            else:
                try:
                    article_text = read_website(url)

                    st.session_state["article_text"] = article_text
                    st.session_state["source"] = url

                    st.success("Website loaded.")

                except Exception as e:
                    st.error("Could not read website.")
                    st.exception(e)

        article_text = st.session_state.get("article_text", "")
        source = st.session_state.get("source", "")

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

    else:
        article_text = st.text_area(
            "Paste article text",
            height=300
        )

        source = "Manual paste"

    if article_text:
        st.subheader("Preview")

        st.text_area(
            "Extracted text",
            article_text[:5000],
            height=250
        )

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
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "source": source,
                    "analysis": output
                }

                append_record(DEVELOPMENTS_FILE, record)

                st.success("Development saved to repository.")

            except Exception as e:
                st.error("OpenAI error. Check credits/API key.")
                st.exception(e)


# ===================================
# TAB 2: REPOSITORY
# ===================================
with tab2:
    st.header("Repository")

    df = load_csv(DEVELOPMENTS_FILE)

    if df.empty:
        st.info("No developments saved yet.")
    else:
        df_display = df.copy()
        df_display.index.name = "Row Number"

        st.dataframe(
            df_display,
            use_container_width=True
        )

        st.subheader("Delete One Development")

        delete_index = st.number_input(
            "Enter development row number to delete",
            min_value=0,
            max_value=len(df) - 1,
            step=1
        )

        if st.button("Delete Selected Development"):
            deleted = delete_row(DEVELOPMENTS_FILE, delete_index)

            if deleted:
                st.success("Selected development deleted.")
                st.rerun()
            else:
                st.error("Could not delete development.")

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Repository CSV",
            data=csv,
            file_name="developments.csv",
            mime="text/csv"
        )


# ===================================
# TAB 3: LIVING ASSESSMENT
# ===================================
with tab3:
    st.header("Living Assessment")

    df = load_csv(DEVELOPMENTS_FILE)

    if df.empty:
        st.info("No developments available. Add developments first.")
    else:
        topic = st.text_input(
            "Enter topic",
            placeholder="Example: USV mine warfare"
        )

        if st.button("Generate Assessment"):
            if not topic:
                st.warning("Please enter a topic first.")
            else:
                try:
                    repository_text = df.to_string(index=False)

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

                    st.subheader("Living Assessment")
                    st.write(assessment)

                    record = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "topic": topic,
                        "assessment": assessment
                    }

                    append_record(ASSESSMENTS_FILE, record)

                    st.success("Assessment saved.")

                except Exception as e:
                    st.error("OpenAI error.")
                    st.exception(e)

    st.divider()

    st.subheader("Saved Assessments")

    assessments_df = load_csv(ASSESSMENTS_FILE)

    if assessments_df.empty:
        st.info("No assessments saved yet.")
    else:
        assessments_display = assessments_df.copy()
        assessments_display.index.name = "Row Number"

        st.dataframe(
            assessments_display,
            use_container_width=True
        )

        st.subheader("Delete One Assessment")

        assessment_delete_index = st.number_input(
            "Enter assessment row number to delete",
            min_value=0,
            max_value=len(assessments_df) - 1,
            step=1
        )

        if st.button("Delete Selected Assessment"):
            deleted = delete_row(ASSESSMENTS_FILE, assessment_delete_index)

            if deleted:
                st.success("Selected assessment deleted.")
                st.rerun()
            else:
                st.error("Could not delete assessment.")

        assessments_csv = assessments_df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download Assessments CSV",
            data=assessments_csv,
            file_name="assessments.csv",
            mime="text/csv"
        )


# ===================================
# TAB 4: WEEKLY BRIEF
# ===================================
with tab4:
    st.header("Weekly Brief")

    developments_df = load_csv(DEVELOPMENTS_FILE)
    assessments_df = load_csv(ASSESSMENTS_FILE)

    if developments_df.empty:
        st.info("No repository data available.")
    else:
        if st.button("Generate Weekly Brief"):
            try:
                developments_text = developments_df.to_string(index=False)

                if assessments_df.empty:
                    assessments_text = "No saved assessments yet."
                else:
                    assessments_text = assessments_df.to_string(index=False)

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

                st.subheader("Weekly Brief")
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
