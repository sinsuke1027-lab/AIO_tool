import google.generativeai as genai
import json
import os
import asyncio
from typing import List, Dict, Optional
from dotenv import load_dotenv
from .models import ScrapedData, AIOScore, AIOInsight, AnalysisResult, DomainAnalysisResult

load_dotenv()

def get_available_models() -> List[str]:
    """Returns a curated and filtered list of Gemini models."""
    preferred = ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-2.0-flash-exp"]
    try:
        models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                name = m.name.split("/")[-1]
                if "gemini" in name.lower() and not any(x in name.lower() for x in ["vision", "tuned", "experimental", "tts", "audio", "embed"]):
                    models.append(name)
        def sort_key(name):
            try: return preferred.index(name)
            except ValueError: return len(preferred)
        if models:
            return sorted(list(set(models)), key=sort_key)
        return preferred
    except Exception:
        return preferred

class AIOAnalyzer:
    def __init__(self, api_key: str = None):
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment or arguments")
        genai.configure(api_key=api_key)

    async def _generate_with_retry(self, model, prompt, generation_config=None, max_retries=3):
        import re
        for attempt in range(max_retries):
            try:
                if generation_config:
                    return model.generate_content(prompt, generation_config=generation_config)
                else:
                    return model.generate_content(prompt)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    # Daily Quota is exhausted -> No point in retrying.
                    if "GenerateRequestsPerDay" in error_msg:
                        raise RuntimeError(f"1日のリクエスト制限(Daily Quota)に達しました。別のモデル（gemini-1.5-flashなど）を選択するか、しばらく時間を空けてから再度お試しください。\n詳細: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        # Attempt to parse retry_delay from the error message
                        delay = 30 # default wait time
                        match = re.search(r"retry_delay\s*\{\s*seconds:\s*(\d+)", error_msg)
                        if match:
                            delay = int(match.group(1)) + 5 # Add 5s buffer 
                        
                        await asyncio.sleep(delay)
                    else:
                        raise RuntimeError(f"APIのレート制限(429)により複数回リトライしましたが失敗しました。モデルを変更するか、さらに時間を空けてから再試行してください。\n詳細: {error_msg}")
                else:
                    raise e

                    
    async def analyze(self, data: ScrapedData, model_name: str = "gemini-1.5-pro") -> AnalysisResult:
        prompt = self._build_prompt(data)
        model = genai.GenerativeModel(model_name)
        response = await self._generate_with_retry(
            model,
            prompt,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
            )
        )
        result_json = json.loads(response.text)
        model_scores = [AIOScore(**score) for score in result_json.get("model_scores", [])]
        insights = [AIOInsight(**insight) for insight in result_json.get("insights", [])]
        return AnalysisResult(
            scraped_data=data,
            total_score=result_json.get("total_score", 0),
            sub_scores=result_json.get("sub_scores", {}),
            model_scores=model_scores,
            insights=insights,
            summary=result_json.get("summary", ""),
            optimized_content=None
        )

    async def generate_optimized_content(self, analysis_result: AnalysisResult, model_name: str = "gemini-1.5-pro") -> str:
        data = analysis_result.scraped_data
        insights_str = "\n".join([f"- {i.issue}: {i.suggestion_after}" for i in analysis_result.insights])
        prompt = f"""
# Role
あなたは世界最高水準のAIO（AI検索エンジン最適化）ライターです。
分析結果とインサイトに基づき、元のコンテンツを「AI検索エンジンに最も引用されやすい形」にリライトしてください。

# Task
ウェブページの内容をリライトしてください。

## 指針
1. **逆ピラミッド構造**: 最も重要な結論（回答）を冒和に配置。
2. **AI回答性**: 簡潔な定義、箇条書き、Q&A形式。
3. **独自性**: 図表や独自データの補完。
4. **構造化**: HTMLまたはMarkdown形式。

## Original Content
- Title: {data.title}
- Current Text: {data.main_text[:4000]}

## Analysis Insights
{insights_str}

---
# Output Requirement
修正後のコンテンツ全体を出力してください。タイトル(H1)、イントロ（AI回答）、メイン詳細、結論を含めます。
"""
        model = genai.GenerativeModel(model_name)
        response = await self._generate_with_retry(model, prompt)
        return response.text

    async def analyze_domain(self, pages: List[ScrapedData], model_name: str = "gemini-1.5-pro") -> DomainAnalysisResult:
        if not pages:
            raise ValueError("No pages provided")
        root_url = pages[0].url
        page_results = []
        for i, page in enumerate(pages):
            result = await self.analyze(page, model_name=model_name)
            page_results.append(result)
            if i < len(pages) - 1:
                await asyncio.sleep(5) # 各ページの解析間に5秒のインターバルを設ける

        
        context_list = [f"Page {i+1} ({p.url}):\nTitle: {p.title}\nH1: {', '.join(p.h1)}" for i, p in enumerate(pages)]
        holistic_context = "\n\n".join(context_list)
        
        prompt = f"""
# Domain Analysis
Pages: {holistic_context}
サイト全体の専門性と一貫性を評価してください。JSON形式で出力。
【重要1: 厳格なスコア基準】
AI特有の甘い採点を排除し、以下の絶対評価基準で厳密に採点してください。
- 0-39点: 専門性が皆無で情報量も極端に少ない。
- 40-59点: 一般的なWebサイト（平均点）。
- 60-79点: ある程度まとまっているが、競合より優れる強い専門性はない。
- 80-100点: ドメイン全体で圧倒的な独自一次情報と強い一貫性が証明されている（非常に厳格な基準）。
【重要2】与えられたPagesの抽出データのみに基づいて厳密に評価してください。AI自身の知識（ブランド知名度など）でスコアを底上げしてはいけません。
【重要3】全体として専門性・一貫性が不足している場合は、domain_total_score を強制的に 50点以下 に落としてください。
【重要4】overall_summary, issue, suggestion_before, suggestion_after, impactなど、すべてのテキスト出力は必ず「日本語」で記述してください。
{{
  "domain_total_score": integer,
  "thematic_consistency_score": integer,
  "internal_linking_score": integer,
  "overall_summary": "string",
  "domain_insights": [{{ "category": "string", "issue": "string", "suggestion_before": "string", "suggestion_after": "string", "impact": "string" }}]
}}
"""
        model = genai.GenerativeModel(model_name)
        response = await self._generate_with_retry(model, prompt, generation_config=genai.GenerationConfig(response_mime_type="application/json"))
        domain_json = json.loads(response.text)
        domain_insights = [AIOInsight(**insight) for insight in domain_json.get("domain_insights", [])]
        return DomainAnalysisResult(
            root_url=root_url, page_results=page_results,
            domain_total_score=domain_json.get("domain_total_score", 0),
            thematic_consistency_score=domain_json.get("thematic_consistency_score", 0),
            internal_linking_score=domain_json.get("internal_linking_score", 0),
            overall_summary=domain_json.get("overall_summary", ""),
            domain_insights=domain_insights
        )

    def _build_prompt(self, data: ScrapedData) -> str:
        content_snippet = data.main_text[:5000]
        json_ld_snippet = json.dumps(data.json_ld[:5])
        return f"""
# AIO Analysis
URL: {data.url}
Title: {data.title}
Content: {content_snippet}
JSON-LD: {json_ld_snippet}

AI検索エンジン向けの適合度を詳細に評価してください。JSON形式で出力。
【重要1: 厳格なスコア基準】
AI特有の甘い採点を排除し、以下の絶対評価基準で厳密に採点してください。
- 0-39点: 独自性がなく、構造化データも存在せず、AIが引用できないレベル。
- 40-59点: どこにでもある一般的なWebコンテンツ（平均点）。
- 60-79点: ある程度AIO最適化されているが、競合より優れる独自情報が弱い。
- 80-100点: AIOとして完璧。独自の一次データ、構造化データ、明確な結論先出し構造がすべて揃っている（特別な例外のみ付与）。
【重要2: ペナルティ要件】
- Contentの情報量が極端に少ない場合、または有益テキストがない場合は各スコアを 30点以下 に減点。
- JSON-LD（構造化データ）が空または不十分な場合、「AI対応度 (AI Readiness)」は 上限40点。
- コンテンツ名から著者、一次情報、明確な引用元が確認できない場合、「権威性と信頼性 (Authority)」は 上限50点。
【重要3】テキストデータのみで評価し、AI自身の知識（ブランド知名度など）でスコアを底上げしないこと。
【重要4】reasoning, issue, suggestion_before, suggestion_after, impact, summaryなど、すべての出力テキストは必ず「日本語」で記述すること。
{{
  "total_score": integer,
  "sub_scores": {{ "AI対応度 (AI Readiness)": int, "直接回答性 (Direct Answerability)": int, "情報増分 (Information Gain)": int, "権威性と信頼性 (Authority)": int, "エンティティ文脈 (Entity Context)": int }},
  "model_scores": [{{ "model_name": "string", "score": int, "reasoning": "string" }}],
  "insights": [{{ "category": "string", "issue": "string", "suggestion_before": "string", "suggestion_after": "string", "impact": "string" }}],
  "summary": "string"
}}
"""
