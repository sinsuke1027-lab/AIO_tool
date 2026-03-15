---
name: AIO_SEO_Technical
description: JSON-LD（構造化データ）やセマンティックマークアップなど、AIエージェントが情報を正確に理解できるようにするための技術的な最適化手法
---

# AIO Technical SEO (技術的AIO最適化)

このスキルは、人間向けではなく「AIエージェント」が機械的に情報を解析する際の精度を最大化するための、ウェブサイトの技術的な裏側を最適化する手法を定義します。

## 1. 構造化データ (JSON-LD) の徹底

AIは非構造型データよりも構造化データを好みます。以下の主要スキーマの実装を推奨します：

- **Organization**: ブランドの基本情報（ロゴ、公式SNSリンク等）。
- **Article / Product**: コンテンツや製品の詳細。特に `author`, `datePublished`, `review` は重要。
- **FAQPage**: AIが直接回答として引用しやすい形式。`Question` と `Answer` のペア。
- **Speakable**: AIアシスタントによる読み上げに適したセクションを指定（Google SGE/Gemini向け）。

## 2. セマンティック・マークアップ

HTML5 の意味論的なタグ（Semantic Tags）を正しく使い、文書構造をAIに伝えます。

- `header`, `footer`, `nav`, `main` の使い分け。
- `section` と `article` による情報の区切り。
- `h1`〜`h6` の階層構造（AIはその重み付けを要約に利用する）。

## 3. クローラビリティとアクセシビリティ

- **robots.txt**: AIクローラー（例：GPTBot, CCBot, PerplexityBot）を許可し、重要ページをブロックしない。
- **Sitemap.xml**: 最新のコンテンツをAIに即座に通知するための仕組み。
- **ALT属性**: 画像の内容をテキストで説明することで、マルチモーダルAIが文脈を理解する助けにする。

## 4. 実装ガイドライン

- **検証ツール**: `Schema.org Validator` や `Google Rich Results Test` をパスすること。
- **JS不要なレンダリング**: サーバーサイドレンダリング（SSR）を優先し、クローラーが即座にコンテンツを取得できるようにする。
