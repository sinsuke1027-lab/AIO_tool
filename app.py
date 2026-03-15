import streamlit as st
import asyncio
import os
from dotenv import load_dotenv
from core.scraper import Scraper
from core.analyzer import AIOAnalyzer
from core.models import AnalysisResult, DomainAnalysisResult

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="AIO Optimization Tool - Phase 1 MVP",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for premium look
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stHeader {
        background: linear-gradient(90deg, #4b6cb7 0%, #182848 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    .insight-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border-left: 5px solid #4b6cb7;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .before-after {
        display: flex;
        gap: 1rem;
        margin-top: 0.5rem;
    }
    .ba-col {
        flex: 1;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.9rem;
    }
    .before { background-color: #ffebee; border: 1px solid #ffcdd2; }
    .after { background-color: #e8f5e9; border: 1px solid #c8e6c9; }
</style>
""", unsafe_allow_html=True)

def setup_sidebar():
    st.sidebar.title("⚙️ Settings")
    api_key = st.sidebar.text_input("Gemini API Key", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    st.session_state["api_key"] = api_key
    
    selected_model = "gemini-1.5-pro" # Default
    if api_key:
        try:
            # Configure genai with the provided key to list models
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            
            # Explicitly reload core modules to avoid dataclass caching issues
            import importlib
            from core import models, analyzer
            importlib.reload(models)
            importlib.reload(analyzer)
            
            available_models = analyzer.get_available_models()
            # Try to find a good default (1.5 pro is best for this tool)
            default_index = 0
            for i, m in enumerate(available_models):
                if "1.5-pro" in m:
                    default_index = i
                    break
            selected_model = st.sidebar.selectbox("Select Gemini Model", options=available_models, index=default_index)
        except Exception as e:
            st.sidebar.error(f"Error fetching models: {e}")
            selected_model = st.sidebar.text_input("Model Name (Fallback)", value="gemini-1.5-pro")
    analysis_mode = st.sidebar.radio("Analysis Mode", ["Single Page", "Domain (Multi-page)"])
        
    return api_key, selected_model, analysis_mode

async def run_analysis(url: str, api_key: str, model_name: str, analysis_mode: str):
    scraper = Scraper()
    analyzer = AIOAnalyzer(api_key=api_key)
    
    with st.status("Analyzing Website...", expanded=True) as status:
        if analysis_mode == "Single Page":
            st.write("🔍 Scraping content...")
            scraped_data = await scraper.scrape(url)
            
            st.write(f"🧠 Evaluating with Gemini AI ({model_name})...")
            result = await analyzer.analyze(scraped_data, model_name=model_name)
        else:
            st.write("🔍 Identifying internal links...")
            links = await scraper.extract_internal_links(url, limit=5)
            urls_to_analyze = [url] + links
            
            st.write(f"📂 Scraping {len(urls_to_analyze)} pages...")
            scraped_pages = []
            for u in urls_to_analyze:
                st.write(f"  - Scraping: {u}")
                scraped_pages.append(await scraper.scrape(u))
            
            st.write(f"🧠 Performing Domain-wide Evaluation ({model_name})...")
            result = await analyzer.analyze_domain(scraped_pages, model_name=model_name)
        
        status.update(label="Analysis Complete!", state="complete", expanded=False)
    return result

def main():
    st.markdown('<div class="stHeader"><h1>AIO Optimization Tool <small>(Phase 4)</small></h1><p>AI回答性・独自性評価モード: 高度なAI検索エンジンへの適合状況を可視化します</p></div>', unsafe_allow_html=True)
    
    api_key, model_name, analysis_mode = setup_sidebar()
    
    url = st.text_input("分析したいURLを入力してください", placeholder="https://example.com")
    
    if st.button("分析開始", type="primary"):
        if not api_key:
            st.error("APIキーが設定されていません。サイドバーから入力してください。")
            return
        
        if not url:
            st.warning("URLを入力してください。")
            return
            
        try:
            result = asyncio.run(run_analysis(url, api_key, model_name, analysis_mode))
            if isinstance(result, AnalysisResult):
                display_results(result)
            else:
                display_domain_results(result)
        except Exception as e:
            st.error(f"エラーが発生しました: {str(e)}")
            import traceback
            st.expander("Show detailed error").code(traceback.format_exc())

def display_domain_results(result: DomainAnalysisResult):
    st.divider()
    st.header(f"🌐 ドメイン解析結果: {result.root_url}")
    
    # Domain Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>Domain AIO Score</h3><h1 style="color:#2ecc71;">{result.domain_total_score}</h1></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h3>Consistency</h3><h1 style="color:#3498db;">{result.thematic_consistency_score}</h1></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><h3>Linking</h3><h1 style="color:#9b59b6;">{result.internal_linking_score}</h1></div>', unsafe_allow_html=True)

    st.subheader("📝 ドメイン・サマリー")
    st.info(result.overall_summary)

    st.subheader("💡 ドメインレベルの改善点")
    for insight in result.domain_insights:
        st.markdown(f"""
        <div class="insight-card">
            <strong>[{insight.category}] {insight.issue}</strong><br>
            <small>Impact: {insight.impact}</small><br>
            <p>💡 {insight.suggestion_after}</p>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("📄 各ページの解析状況")
    tabs = st.tabs([f"Page {i+1}" for i in range(len(result.page_results))])
    for i, res in enumerate(result.page_results):
        with tabs[i]:
            st.write(f"**URL:** {res.scraped_data.url}")
            st.write(f"**AIO Score:** {res.total_score}")
            st.progress(res.total_score / 100)
            if st.button(f"詳細を表示: Page {i+1}", key=f"page_btn_{i}"):
                display_results(res)

def display_results(result: AnalysisResult):
    st.divider()
    
    # Overview metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>Overall AIO Score</h3><h1 style="color:#4b6cb7;">{result.total_score}</h1></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h3>Information Gain</h3><h1>{"High" if result.sub_scores.get("Information Gain", 0) > 70 else "Normal"}</h1></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><h3>Direct Answer</h3><h1>{"Yes" if result.sub_scores.get("Direct Answerability", 0) > 70 else "Needs Fix"}</h1></div>', unsafe_allow_html=True)

    # Sub-metrics progress bars
    st.subheader("📊 解析サブ指標 (Advanced AIO Metrics)")
    s_col1, s_col2 = st.columns(2)
    sub_metrics = result.sub_scores
    for i, (name, val) in enumerate(sub_metrics.items()):
        target_col = s_col1 if i % 2 == 0 else s_col2
        with target_col:
            st.write(f"**{name}**")
            st.progress(val / 100, text=f"{val}/100")

    # AIO Evidence
    st.subheader("🔍 AIO引用・回答根拠 (Evidence Found)")
    e_col1, e_col2 = st.columns(2)
    with e_col1:
        st.write("**Extracted Tables (Data Items):**")
        if result.scraped_data.tables:
            for t in result.scraped_data.tables[:2]:
                st.caption(f"Table Data: {t[:100]}...")
        else:
            st.caption("No tables found (Information Gain may be lower).")
    with e_col2:
        st.write("**Expert Voices / Citations:**")
        if result.scraped_data.citations:
            for c in result.scraped_data.citations[:2]:
                st.caption(f"Quote: {c[:100]}...")
        else:
            st.caption("No blockquotes or citations found (EEAT target).")

    st.subheader("🤖 各AIモデル別の適合度 (Model Simulation)")
    m_cols = st.columns(len(result.model_scores))
    for i, model_score in enumerate(result.model_scores):
        with m_cols[i]:
            st.metric(model_score.model_name, f"{model_score.score}%")
            st.caption(model_score.reasoning)

    st.subheader("💡 改善のインサイト (Refined AI Insights)")
    for insight in result.insights:
        # Determine color based on impact or category
        color = "#4b6cb7" # Default
        if "EEAT" in insight.category: color = "#e91e63"
        elif "Technical" in insight.category: color = "#ff9800"

        st.markdown(f"""
        <div class="insight-card" style="border-left-color: {color};">
            <div style="display:flex; justify-content:space-between;">
                <strong><span style="color:{color};">[{insight.category}]</span> {insight.issue}</strong>
                <span style="color:{color}; font-weight:bold;">Impact: {insight.impact}</span>
            </div>
            <div class="before-after">
                <div class="ba-col before"><strong>Current / Issue:</strong><br>{insight.suggestion_before}</div>
                <div class="ba-col after"><strong>Recommendation / Rewrite:</strong><br>{insight.suggestion_after}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("📝 総合サマリー")
    st.info(result.summary)

    # --- NEW: Phase 5 Content Generator ---
    st.divider()
    st.subheader("✨ AIO最適化コンテンツ案 (Optimized Preview)")
    st.write("解析結果に基づき、AI検索エンジンに評価されやすい形式へリライト案を作成します。")
    
    # State key for this URL
    gen_key = f"optimized_content_{result.scraped_data.url}"
    
    if st.button("✨ 修正案を生成する", type="secondary", key=f"gen_btn_{result.scraped_data.url}"):
        with st.spinner("AIがコンテンツをリライト中..."):
            analyzer = AIOAnalyzer(api_key=st.session_state.get("api_key"))
            # We need to ensure we have the API key. In run_analysis it was passed.
            # Here we might need to get it from sidebar state or global.
            opt_content = asyncio.run(analyzer.generate_optimized_content(result))
            st.session_state[gen_key] = opt_content

    if gen_key in st.session_state:
        st.markdown(f'<div class="insight-card" style="border-left-color: #2ecc71; background-color: #f0fff4;">', unsafe_allow_html=True)
        st.markdown("**【リライト提案】**")
        st.markdown(st.session_state[gen_key])
        st.markdown('</div>', unsafe_allow_html=True)
        st.download_button("テキストをダウンロード", st.session_state[gen_key], file_name="aio_optimized_content.md")
    # --------------------------------------

    with st.expander("詳細な取得データを確認"):
        st.json({
            "title": result.scraped_data.title,
            "description": result.scraped_data.description,
            "h1": result.scraped_data.h1,
            "tables_found": len(result.scraped_data.tables),
            "citations_found": len(result.scraped_data.citations),
            "json_ld_count": len(result.scraped_data.json_ld),
            "sub_metrics": result.sub_scores
        })


if __name__ == "__main__":
    main()
