import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
import docx
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="Naval Tech Watch", layout="wide")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

DEVELOPMENTS_FILE = "developments.csv"
ASSESSMENTS_FILE = "assessments.csv"


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
    response = requests.get(url, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def ask_chatgpt(prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def save_development(record):
    df_new = pd.DataFrame([record])

    if os.path.exists(DEVELOPMENTS_FILE):
        df_old = pd.read_csv(DEVELOPMENTS_FILE)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new

    df_all.to_csv(DEVELOPMENTS_FILE, index=False)


def save_assessment(record):
    df_new = pd.DataFrame([record])

    if os.path.exists(ASSESSMENTS_FILE):
        df_old = pd.read_csv(ASSESSMENTS_FILE)
        df_all = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_all = df_new

    df_all.to_csv(ASSESSMENTS_FILE, index=False)


def load_csv(file):
    if os.path.exists(file):
        return pd.read_csv(file)
    return pd.DataFrame()


st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    [
        "1. Add Development",
        "2. Repository",
        "3. Living Assessment",
        "4. Weekly Brief"
    ]
)

st.title("Naval Defence Tech Watch System")
st.caption("Repository + living assessments + weekly brief generator")


# -----------------------------
# PAGE 1: ADD DEVELOPMENT
# -----------------------------
if page == "1. Add Development":
    st.header("Add New Development")

    input_type = st.radio(
        "Choose input type",
        ["Website link", "Upload document", "Paste text"]
    )

    article_text = ""
    source = ""

    if input_type == "Website link":
        url = st.text_input("Paste article URL")

        if st.button("Read Website"):
            try:
                article_text = read_website(url)
                source = url
                st.session_state["article_text"] = article_text
                st.session_state["source"] = source
                st.success("Website read successfully.")
            except Exception as e:
                st.error("Could not read website. Try copy-pasting the text instead.")
                st.exception(e)

        article_text = st.session_state.get("article_text", "")
        source = st.session_state.get("source", "")

    elif input_type == "Upload document":
        uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])

        if uploaded_file:
            source = uploaded_file.name

            try:
                if uploaded_file.name.endswith(".pdf"):
                    article_text = read_pdf(uploaded_file)
                elif uploaded_file.name.endswith(".docx"):
                    article_text = read_docx(uploaded_file)
                else:
                    article_text = read_txt(uploaded_file)

                st.success("Document read successfully.")
            except Exception as e:
                st.error("Could not read document.")
                st.exception(e)

    else:
        article_text = st.text_area("Paste article text here", height=250)
        source = "Manual paste"

    if article_text:
        st.subheader("Preview")
        st.text_area("Extracted text", article_text[:5000], height=250)

        if st.button("Analyse and Save"):
            prompt = f"""
You are a naval defence technology watch analyst.

Analyse the article below for a naval capability development organisation.

Return the answer in this exact format:

Title:
Date of development:
Source:
Main topic:
Sub-topic:
Actors / organisations:
Country:
Type of development:
Maturity level:
Importance score R1-R5:
Executive summary:
What happened:
Why it matters:
Naval / defence relevance:
Relevance to unmanned systems:
Technology stack layer:
Evidence quality:
Risks / caveats:
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
                    "input_type": input_type,
                    "source": source,
                    "analysis": output
                }

                save_development(record)
                st.success("Saved into repository.")

            except Exception as e:
                st.error("OpenAI error. Check API credits or key.")
                st.exception(e)


# -----------------------------
# PAGE 2: REPOSITORY
# -----------------------------
elif page == "2. Repository":
    st.header("Repository of Developments")

    df = load_csv(DEVELOPMENTS_FILE)

    if df.empty:
        st.info("No developments saved yet.")
    else:
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Repository CSV",
            data=csv,
            file_name="developments.csv",
            mime="text/csv"
        )


# -----------------------------
# PAGE 3: LIVING ASSESSMENT
# -----------------------------
elif page == "3. Living Assessment":
    st.header("Generate Living Assessment")

    df = load_csv(DEVELOPMENTS_FILE)

    if df.empty:
        st.info("No repository data yet. Add developments first.")
    else:
        topic = st.text_input("Enter topic to assess", placeholder="Example: USV mine warfare")

        if st.button("Generate Current Assessment"):
            relevant_records = df.to_string(index=False)

            prompt = f"""
You are a naval defence technology analyst.

Using the repository records below, generate a living assessment for this topic:

Topic: {topic}

The assessment must not only summarise recent items.
It must explain the current state of play based on all historical evidence.

Use this structure:

1. Current Assessment
2. Evidence Base
3. Maturity Trend
4. Key Actors
5. What Has Changed Over Time
6. Confidence Level
7. Implications for Our Organisation
8. Open Questions
9. Recommended Next Actions

Repository records:
{relevant_records[:20000]}
"""

            try:
                assessment = ask_chatgpt(prompt)

                st.subheader("Living Assessment")
                st.write(assessment)

                record = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "topic": topic,
                    "assessment": assessment
                }

                save_assessment(record)
                st.success("Living assessment saved.")

            except Exception as e:
                st.error("OpenAI error.")
                st.exception(e)

    st.divider()
    st.subheader("Saved Living Assessments")

    assessments_df = load_csv(ASSESSMENTS_FILE)

    if assessments_df.empty:
        st.info("No living assessments saved yet.")
    else:
        st.dataframe(assessments_df, use_container_width=True)


# -----------------------------
# PAGE 4: WEEKLY BRIEF
# -----------------------------
elif page == "4. Weekly Brief":
    st.header("Generate Weekly Brief")

    df = load_csv(DEVELOPMENTS_FILE)
    assessments_df = load_csv(ASSESSMENTS_FILE)

    if df.empty:
        st.info("No developments saved yet.")
    else:
        if st.button("Generate Weekly Tech Watch Brief"):
            developments_text = df.to_string(index=False)
            assessments_text = assessments_df.to_string(index=False) if not assessments_df.empty else "No saved assessments yet."

            prompt = f"""
You are preparing a weekly naval defence technology watch brief for senior staff.

Use the repository and living assessments below.

The brief must not just list news.
It must explain:
- what happened this week
- what changed in our assessment
- what the current state of play is
- what to watch next

Use this format:

Title:
Executive Summary:

1. Key Developments This Week
2. What Changed in Our Assessment
3. Current State of Play
4. Implications for Our Organisation
5. Priority Open Questions
6. Recommended Actions
7. Items to Watch Next Week

Repository:
{developments_text[:20000]}

Living assessments:
{assessments_text[:12000]}
"""

            try:
                brief = ask_chatgpt(prompt)

                st.subheader("Weekly Brief")
                st.write(brief)

                st.download_button(
                    "Download Weekly Brief",
                    data=brief,
                    file_name="weekly_tech_watch_brief.txt",
                    mime="text/plain"
                )

            except Exception as e:
                st.error("OpenAI error.")
                st.exception(e)
