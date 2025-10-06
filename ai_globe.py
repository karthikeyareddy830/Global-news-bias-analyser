# app.py
import re
import subprocess
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
import streamlit as st

# ---------------------------
# 1️⃣ Auto-install helper
# ---------------------------
def install_and_import(package_name: str, import_name: str = None):
    import_name = import_name or package_name
    try:
        globals()[import_name] = __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
        globals()[import_name] = __import__(import_name)

# Install required packages
install_and_import("newspaper3k", "newspaper")
install_and_import("beautifulsoup4", "bs4")
install_and_import("nltk")
install_and_import("vaderSentiment")

# ---------------------------
# 2️⃣ Imports after install
# ---------------------------
from newspaper import Article
from bs4 import BeautifulSoup
import nltk
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Ensure nltk data is available
nltk.download("punkt", quiet=True)
nltk.download("stopwords", quiet=True)

# ---------------------------
# 3️⃣ API Keys (put your keys here)
# ---------------------------
NEWSAPI_KEY = "8017824e875745209e722c6de9cba449"      # <--- replace with your NewsAPI key
GEMINI_API_KEY = "AIzaSyDAXkUPh2C233PtCBUw_L67ow-8iMDIPk8" # <--- replace with Gemini key (optional)

# ---------------------------
# 4️⃣ Agent 1: Normalize query
# ---------------------------
def agent1_normalize_query(user_query: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", user_query)
    return cleaned.strip().lower()

# ---------------------------
# 5️⃣ Agent 2: Fetch news articles
# ---------------------------
def agent2_fetch_articles(query: str, api_key: str, max_articles: int = 5) -> List[Dict[str, Any]]:
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&sortBy=relevancy&apiKey={api_key}"
    response = requests.get(url)
    if response.status_code != 200:
        return []

    articles = response.json().get("articles", [])
    results = []

    for art in articles[:max_articles]:
        article_data = {"title": art["title"], "url": art["url"], "content": None}
        try:
            news_article = Article(art["url"])
            news_article.download()
            news_article.parse()
            article_data["content"] = news_article.text
        except:
            try:
                html = requests.get(art["url"]).text
                soup = BeautifulSoup(html, "html.parser")
                article_data["content"] = " ".join([p.get_text() for p in soup.find_all("p")])
            except:
                article_data["content"] = art.get("description", "")
        results.append(article_data)
    return results

# ---------------------------
# 6️⃣ Agent 3: Bias analysis
# ---------------------------
def agent3_analyze_bias(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    analyzer = SentimentIntensityAnalyzer()
    opinion_words = ["must", "should", "never", "always", "clearly", "obviously"]

    results = []
    for art in articles:
        text = art.get("content", "") or ""
        sentiment = analyzer.polarity_scores(text)
        bias_score = sum(word in text.lower() for word in opinion_words)
        results.append({
            "title": art["title"],
            "url": art["url"],
            "bias_score": bias_score,
            "sentiment": sentiment,
            "content_preview": text[:300] + "..." if len(text) > 300 else text
        })
    return results

# ---------------------------
# 7️⃣ Agent 4: Neutral summary
# ---------------------------
def agent4_generate_neutral_article(articles: List[Dict[str, Any]]) -> str:
    if not articles:
        return "No articles available to summarize."

    combined_text = " ".join(art["content_preview"] for art in articles)
    if GEMINI_API_KEY:
        return (
            "Neutral Summary (mock): Based on multiple sources, "
            "this report balances perspectives to avoid bias."
        )
    else:
        return combined_text[:1000]

# ---------------------------
# 8️⃣ Streamlit UI
# ---------------------------
st.set_page_config(page_title="Global News Bias Analyzer", layout="wide")
st.title("🌍 Global News Bias Analyzer")
st.markdown("Analyze bias in global news articles using AI Agents")

user_query = st.text_input("Enter a news topic (e.g., climate change, elections, AI):")

if st.button("Analyze News"):
    if not user_query:
        st.error("Please enter a topic.")
    elif not NEWSAPI_KEY or NEWSAPI_KEY == "your_newsapi_key_here":
        st.error("Please set your NewsAPI key at the top of the file.")
    else:
        with st.spinner("Fetching and analyzing articles..."):
            query = agent1_normalize_query(user_query)
            articles = agent2_fetch_articles(query, NEWSAPI_KEY)
            if not articles:
                st.error("No articles found or NewsAPI limit reached.")
            else:
                results = agent3_analyze_bias(articles)

                st.subheader("📌 Articles & Bias Analysis")
                for r in results:
                    st.markdown(f"**[{r['title']}]({r['url']})**")
                    st.write(f"Bias Score: {r['bias_score']} | Sentiment: {r['sentiment']}")
                    st.write(r["content_preview"])
                    st.markdown("---")

                st.subheader("📰 Neutral Summary")
                summary = agent4_generate_neutral_article(results)
                st.success(summary)
