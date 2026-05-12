import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
import docx
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os

# -----------------------
# Page setup
# -----------------------
st.set_page_config(page_title="Tech Watch App", layout="wide")
st.title("Tech Watch App")
st.caption("Upload an article or paste a website link to generate a tech-watch brief.")

# -----------------------
# OpenAI setup
# -----------------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

ARCHIVE_FILE = "techwatch_archive.csv"

# -----------------------
# Read document functions
# -----------------------
def read_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
        text += "\n"
    return text


def read_docx(file):
    document = docx.Document(file)
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


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


# -----------------------
# Archive function
# -----------------------
def save_to_archive(source_type, source, output):
    new_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_type": source_type,
        "source": source,
        "output": output
    }

    df_new = pd.DataFrame([new_entry])

    if os.path.exists(ARCHIVE_FILE):
        df_existing = pd.read_csv(ARCHIVE_FILE)
        df_all = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_all = df_new

    df_all.to_csv(ARCHIVE_FILE, index=False)


# -----------------------
# Input section
# -----------------------
input_mode = st.radio(
    "Choose input type",
    ["Upload document", "Website link", "Paste text"]
)

article_text = ""
source_type = ""
source_name = ""

if input_mode == "Upload document":
    uploaded_file = st.file_uploader(
        "Upload PDF, DOCX, or TXT",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_file is not None:
        source_type = "document"
        source_name = uploaded_file.name

        try:
            if uploaded_file.name.endswith(".pdf"):
                article_text = read_pdf(uploaded_file)
            elif uploaded_file.name.endswith(".docx"):
                article_text = read_docx(uploaded_file)
            elif uploaded_file.name.endswith(".txt"):
                article_text = read_txt(uploaded_file)
        except Exception as e:
            st.error("Could not read this document.")
            st.exception(e)

elif input_mode == "Website link":
    url = st.text_input("Paste website link here")

    if st.button("Read Website"):
        if not url:
            st.warning("Please paste a website link first.")
        else:
            try:
                article_text = read_website(url)
                st.session_state["article_text"] = article_text
                st.session_state["source_type"] = "website"
                st.session_state["source_name"] = url
                st.success("Website read successfully.")
            except Exception as e:
                st.error("Could not read this website. Some websites block automatic reading.")
                st.exception(e)

    article_text = st.session_state.get("article_text", "")
    source_type = st.session_state.get("source_type", "")
    source_name = st.session_state.get("source_name", "")

else:
    pasted_text = st.text_area("Paste article text here", height=250)

    if pasted_text:
        article_text = pasted_text
        source_type = "pasted_text"
        source_name = "Manual paste"


# -----------------------
# Preview section
# -----------------------
if article_text:
    st.subheader("Article Preview")
    st.text_area("Extracted text", article_text[:5000], height=250)

    if st.button("Generate Tech Watch Brief"):
        prompt = f"""
You are a naval technology watch analyst.

Analyse the article below and produce a structured tech-watch brief.

Use these headings:

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
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            output = response.choices[0].message.content

            st.subheader("Tech Watch Brief")
            st.write(output)

            save_to_archive(source_type, source_name, output)
            st.success("Saved to archive.")

        except Exception as e:
            st.error("OpenAI error. Check API key, billing credits, or model access.")
            st.exception(e)


# -----------------------
# Archive section
# -----------------------
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
