import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
import docx

st.set_page_config(page_title="Tech Watch App", layout="wide")
st.title("Tech Watch App")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def read_pdf(file):
    reader = PdfReader(file)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join(p.text for p in doc.paragraphs)

uploaded_file = st.file_uploader("Upload article", type=["txt", "pdf", "docx"])

if uploaded_file:
    if uploaded_file.name.endswith(".pdf"):
        article_text = read_pdf(uploaded_file)
    elif uploaded_file.name.endswith(".docx"):
        article_text = read_docx(uploaded_file)
    else:
        article_text = uploaded_file.read().decode("utf-8")

    st.subheader("Article Preview")
    st.text_area("Extracted text", article_text[:3000], height=250)

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
{article_text}
"""

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        st.subheader("Tech Watch Brief")
        st.write(response.choices[0].message.content)
