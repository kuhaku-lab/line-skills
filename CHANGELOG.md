# Changelog

このプロジェクトのすべての主要な変更を記録します。
フォーマットは [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) に準拠し、
バージョニングは [Semantic Versioning](https://semver.org/spec/v2.0.0.html) に従います。

> **0.x の間は API(SKILL.md description / リファレンス構成)が破壊的変更を含む可能性があります。**

## [Unreleased]

## [0.0.1] - 2026-05-13

### Added — 6 つの初版 Skill

- **messaging-api**: Webhook 署名検証、Reply/Push/Multicast/Narrowcast/Broadcast、Flex Message、リッチメニュー、オーディエンス、Coupons API、Mark as Read、Channel access token、URL schemes
- **line-login**: OAuth 2.0、PKCE (S256)、ID Token (JWT) 検証(HS256/ES256)、トークンライフサイクル、ユーザープロフィール、ボットリンク、ログインボタン設計
- **line-liff**: LIFF SDK v2.28+、`liff.init`、`sendMessages`、Share Target Picker、`scanCodeV2`、`requestFriendship`(v2.28.0)、`permission.getGrantedAll`(v2.27.0)、Pluggable SDK、LIFF プラグイン、Server API、CLI、Android edge-to-edge 対応
- **line-mini-app**: サービスメッセージ、共通プロフィール Quick Fill(2025-08 GA)、アプリ内課金(JP 2026-02 GA)、Custom Path、コンソール 3 チャネル、Channel consent simplification、Taiwan / Thailand 公開緩和(2026-03)
- **line-notification-message**: 電話番号ベース PNP 配信(JP / TH / TW)、SHA256 ハッシュ、テンプレート型 / フレキシブル型、配信完了 Webhook、同意フロー、180 日 SMS 認証
- **line-creators-market**: スタンプ 7 種(static / animated / custom / message / big / popup / effect)、絵文字、着せかえ、技術仕様、審査ガイドライン、AI 使用申告、LINE Sticker Maker、日本 / 台湾 / タイ / グローバル市場戦略

### Added — テスト基盤

- `tests/` 配下に pytest + Claude Agent SDK ベースの評価ハーネス
- `simulated` モード(LLM-as-judge、高速)と `e2e` モード(`claude -p` 実行、最終確認用)
- description の自動最適化ループ(`uv run line-skills optimize`)
- 認証未完了の事前検出、60 秒/クエリのタイムアウト、リアルタイム pass/fail 表示

### Coverage

- LINE Developers ドキュメント 2026-05 時点に準拠
- 日本 / タイ / 台湾の地域固有仕様を包含
- E2E トリガー精度: 88-100%(skill 別、計 524 クエリ)

[Unreleased]: https://github.com/kuhaku-lab/line-skills/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/kuhaku-lab/line-skills/releases/tag/v0.0.1
