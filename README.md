# line-skills

**LINE プラットフォーム開発のための Claude Code Skills セット。**

最新の LINE Developers ドキュメントに準拠した API リファレンス・設計ガイド・専門家ナレッジを 6 つの Skill にパッケージ化。Messaging API / LINE Login / LIFF / LINE MINI App / 通知メッセージ / Creators Market を網羅。

`日本語` ・ [`English`](README-EN.md) ・ [`Skill 一覧`](#skill-一覧) ・ [`クイックスタート`](#クイックスタート) ・ [`テスト`](#テスト)

---

## クイックスタート

### A. Claude Code プラグインとして使う(推奨)

```bash
/plugin marketplace add kuhaku-lab/line-skills
/plugin install line-skills@kuhaku-lab-line-skills
```

インストール後 `/reload-plugins` で有効化。

### B. Skills として個別インストール

```bash
# 全部入り
npx skills add kuhaku-lab/line-skills

# 必要なものだけ
npx skills add kuhaku-lab/line-skills@messaging-api
npx skills add kuhaku-lab/line-skills@line-liff
# ... 他の Skill 名は下表を参照
```

### C. ローカル試用(インストールなし)

```bash
git clone https://github.com/kuhaku-lab/line-skills.git
claude --plugin-dir ./line-skills
```

---

## Skill 一覧

| Skill | カバー領域 | こう聞くと起動 |
|-------|-----------|--------------|
| [**messaging-api**](skills/messaging-api/) | Webhook 署名検証 / Reply・Push・Multicast・Narrowcast・Broadcast / Flex Message / リッチメニュー / オーディエンス / クーポン / インサイト / Mark as Read | 「LINE Bot で push 送信」「Flex Message を作って」「リッチメニュー切替」 |
| [**line-login**](skills/line-login/) | OAuth 2.0 / PKCE / ID トークン (JWT) 検証 / トークンリフレッシュ / ユーザープロフィール / ボットリンク / ログインボタン設計 | 「LINE Login 実装」「ID トークン検証」「友だち追加プロンプト」 |
| [**line-liff**](skills/line-liff/) | LIFF SDK v2.28+ / `liff.init` / `sendMessages` / Share Target Picker / `scanCodeV2` / `requestFriendship` / Pluggable SDK / LIFF プラグイン / Server API / CLI | 「LIFF アプリを作る」「QR スキャン」「permalink 生成」 |
| [**line-mini-app**](skills/line-mini-app/) | サービスメッセージ / 共通プロフィール Quick Fill / アプリ内課金 (JP) / コンソール 3 チャネル / Custom Path / 申請レビュー | 「MINI App 申請」「サービスメッセージ送信」「Quick Fill 実装」 |
| [**line-notification-message**](skills/line-notification-message/) | 電話番号ベース PNP 配信(LINE通知メッセージ / LON)/ SHA256 ハッシュ / テンプレート・フレキシブル型 / 配信完了 Webhook / 同意フロー / SMS 認証 | 「電話番号で LINE 通知」「PNP webhook」「LON テンプレート」 |
| [**line-creators-market**](skills/line-creators-market/) | スタンプ 7 種 / 絵文字 / 着せかえ / 技術仕様 / 審査ガイドライン / 収益モデル / AI 使用申告 / LINE Sticker Maker / 市場戦略 | 「スタンプを作りたい」「APNG 仕様」「審査基準」 |

> 各 Skill は **日本 / タイ / 台湾** の地域固有情報を含みます。
> Skill は段階的にロードされます — メタデータは常時、SKILL.md 本文はトリガー時、リファレンスは必要に応じて。

---

## テスト

トリガー精度のテスト基盤を `tests/` 配下に同梱(pytest + Claude Agent SDK)。詳細は [`tests/README.md`](tests/README.md) を参照。

### セットアップ

```bash
brew install uv         # または: curl -LsSf https://astral.sh/uv/install.sh | sh
cd tests
uv sync
```

### よく使うコマンド

```bash
# 全 skill を高速評価(simulated モード)
uv run pytest

# 1 skill だけ集中的に
uv run line-skills eval messaging-api -v

# E2E モード(実際の claude -p を起動して検証)
uv run line-skills eval messaging-api --mode e2e --runs 3 -v

# description を自動最適化
uv run line-skills optimize line-login --iterations 3
```

<details>
<summary><b>現在のスコア</b>(クリックで展開)</summary>

各 Skill には 4 言語(英語・日本語・繁体中文・タイ語)の評価セットがあり、`should_trigger: true/false` の両方をカバー。

| Skill | E2E 精度 | Simulated 精度 | クエリ数 | 計測日 |
|-------|---------:|--------------:|--------:|--------|
| line-notification-message | **100%** | **100%** | 73 | 2026-03-23 |
| line-liff | 96% | 92% | 72 | 2026-03-20 |
| line-login | 95% | 92% | 65 | 2026-03-20 |
| line-mini-app | 94% | 99% | 176 | 2026-03-23 |
| messaging-api | 93% | **100%** | 70 | 2026-03-20 |
| line-creators-market | 88% | **100%** | 68 | 2026-03-20 |

- **E2E**: 実際に `claude -p` を起動し、`Skill` ツールが呼ばれたかを stream-json で検出
- **Simulated**: Claude Agent SDK に description だけ提示し、trigger するかを LLM judge に問う(高速・安価)

</details>

---

## ライセンス

[LICENSE](LICENSE) を参照。
