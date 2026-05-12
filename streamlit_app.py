import pandas as pd
from datetime import datetime
import os
import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
import docx
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Tech Watch App", layout="wide")
st.title("Tech Watch App")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def read_pdf(file):
    reader = PdfReader(file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

def read_website(url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
ARCHIVE_FILE = "techwatch_archive.csv"

def save_to_archive(source_type, source, summary):
    new_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_type": source_type,
        "source": source,
        "summary": summary
    }

    df_new = pd.DataFrame([new_entry])

    if os.path.exists(ARCHIVE_FILE):
        df_existing = pd.read_csv(ARCHIVE_FILE)
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_all = df_new

    df_all.to_csv(ARCHIVE_FILE, index=False)

input_mode = st.radio(
    "Choose input type",
    ["Upload document", "Website link"]
)
article_text = ""

if input_mode == "Upload document":
    uploaded_file = st.file_uploader("Upload article", type=["txt", "pdf", "docx"])

    if uploaded_file:
        if uploaded_file.name.endswith(".pdf"):
            article_text = read_pdf(uploaded_file)
        elif uploaded_file.name.endswith(".docx"):
            article_text = read_docx(uploaded_file)
        else:
            article_text = uploaded_file.read().decode("utf-8")

else:
    url = st.text_input("Paste website link")

    if st.button("Read Website"):
        try:
            article_text = read_website(url)
            st.session_state["article_text"] = article_text
        except Exception as e:
            st.error("Cannot read this website. Try another link or copy-paste the article text.")
            st.exception(e)

    article_text = st.session_state.get("article_text", "")

if article_text:
    st.subheader("Article Preview")
    st.text_area("Extracted text", article_text[:5000], height=250)

    if st.button("Generate Tech Watch Brief"):
        prompt = f"""
You are a naval technology watch analyst.

Analyse the article and produce a structured tech-watch brief.

Return the output using these headings:
1. Executive Summary
2. Technology Described
3. What Is New
4. Naval / Defence Relevance
5. Relevance to USV / UUV / UAV / CUxV
6. Tech Stack Layer
7. TRL Estimate
8. Key Companies / Actors
9. Risks and Caveats
10. Recommended Action: Watch / Engage / Experiment / Ignore

Article:
{article_text[:12000]}
"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}]
            )

            st.subheader("Tech Watch Brief")
            st.write(output)
            if input_mode == "Website link":
                save_to_archive(
                    source_type="website",
                    source=url,
                    summary=output[:1000])

        if input_mode == "Upload document":
    save_to_archive(
        source_type="document",
        source=uploaded_file.name,
        summary=output[:1000]
    )

st.divider()
st.header("Archive")

if os.path.exists(ARCHIVE_FILE):
    archive_df = pd.read_csv(ARCHIVE_FILE)
    st.dataframe(archive_df)

    csv = archive_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download Archive CSV",
        data=csv,
        file_name="techwatch_archive.csv",
        mime="text/csv"
    )
else:
    st.info("No archived entries yet.")
        except Exception as e:
            st.error("OpenAI error. Check API credits, model name, or usage limit.")
            st.exception(e)
