from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ScrapedData:
    url: str
    title: str
    description: str
    h1: List[str]
    main_text: str
    meta_tags: Dict[str, str]
    json_ld: List[Dict] = field(default_factory=list)
    tables: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)

@dataclass
class AIOScore:
    model_name: str
    score: int  # 0-100
    reasoning: str

@dataclass
class AIOInsight:
    category: str  # Content, Technical, EEAT
    issue: str
    suggestion_before: str
    suggestion_after: str
    impact: str

@dataclass
class AnalysisResult:
    scraped_data: ScrapedData
    total_score: int
    # Sub-metrics: AI Readiness, Authority, Content Clarity, Mention Presence
    sub_scores: Dict[str, int]
    model_scores: List[AIOScore]
    insights: List[AIOInsight]
    summary: str
    optimized_content: Optional[str] = None

@dataclass
class DomainAnalysisResult:
    root_url: str
    page_results: List[AnalysisResult]
    domain_total_score: int
    thematic_consistency_score: int  # 0-100
    internal_linking_score: int      # 0-100
    overall_summary: str
    domain_insights: List[AIOInsight]
