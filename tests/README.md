# tests/

Trigger-accuracy evaluation and description optimization for line-skills.

> 日本語 ↓ / English follows below.

## セットアップ

### 前提

このテストは内部で **Claude Code(`claude` CLI)** を subprocess 起動します。事前に Claude Code 本体のインストールとログインが完了している必要があります。

```bash
# 1) Claude Code がインストールされていることを確認
claude --version
# 入っていなければ: https://docs.claude.com/en/docs/claude-code/install

# 2) ログイン(初回のみ。ブラウザが開いて OAuth)
claude
# 起動後 /login → ブラウザ認証 → 完了したら /exit で抜ける

# 3) ログイン確認(エラーなく hello と返ればOK)
claude -p "hello"
```

> **API key 経由でもOK**:`export ANTHROPIC_API_KEY=sk-ant-...` でも動作します。CI 環境はこちら推奨。
> **タイムアウト**:1 クエリあたり 60 秒のタイムアウトを設けているので、ログイン未完了でも無限ハングはしません。

### 依存インストール

```bash
# uv 推奨(高速・lockfile 自動管理)
brew install uv          # or: pipx install uv / curl -LsSf https://astral.sh/uv/install.sh | sh
cd tests
uv sync

# pip フォールバック
cd tests
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## 使い方

### Pytest(CI / 日常テスト)

```bash
# 全 skill を simulated モードで一括実行
uv run pytest

# 特定 skill だけ
uv run pytest -k messaging_api

# 並列実行 + 安定化のため 3 runs/query + 閾値 90%
uv run pytest -n auto --runs 3 --threshold 0.9

# JUnit XML を CI に渡す
uv run pytest --junitxml=results.xml
```

環境変数 `SKILL_TEST_RUNS` / `SKILL_TEST_CONCURRENCY` / `SKILL_TEST_THRESHOLD` でも設定可。

### CLI(対話的 / 詳細レポート / 最適化)

```bash
# 全 skill 評価(human-readable)
uv run line-skills eval --verbose

# 特定 skill だけ
uv run line-skills eval messaging-api -v

# e2e モード(実際の claude -p を呼び出す)
uv run line-skills eval messaging-api --mode e2e --runs 3 -v

# JSON を file に保存
uv run line-skills eval --output results.json

# description 最適化ループ(3 イテレーション)
uv run line-skills optimize line-login --iterations 3 --output line-login-opt.json

# Skill 一覧
uv run line-skills list-skills
```

## 構成

```
tests/
├── pyproject.toml          # uv / pip 用依存定義
├── conftest.py             # pytest 共通fixture
├── test_triggers.py        # pytest テスト(6 skill 全件パラメトリ)
├── eval/
│   ├── skill_io.py         # SKILL.md frontmatter + テストデータ ローダー
│   ├── assessor.py         # simulated (Agent SDK as judge) + e2e (claude -p)
│   ├── optimizer.py        # description 改善ループ
│   └── cli.py              # `line-skills` typer CLI
└── data/                   # skill 別の評価データ
    └── <skill-name>/
        ├── assessment_set.json   # [{"query": "...", "should_trigger": true}, ...]
        └── scope.json            # {"knowledge_domain": "...", "assess_scope": [...], ...}
```

## モードの違い

| Mode | 仕組み | 用途 | 速度 |
|------|--------|------|------|
| **simulated**(デフォルト) | Claude Agent SDK で「description のみ」を見せ、trigger するかを LLM judge に判定させる | 高速イテレーション、CI、description 設計 | 速い |
| **e2e** | `claude -p` を実際に起動し、Skill ツール呼び出しを stream-json で検出 | 本番ハーネスでの最終確認 | 遅い |

## 評価データの追加

新しい query を追加するには `data/<skill>/assessment_set.json` を編集するだけ。

```json
[
  { "query": "LINE bot で push メッセージを送る方法を教えて", "should_trigger": true },
  { "query": "Pythonでフィボナッチを実装して", "should_trigger": false }
]
```

`should_trigger` が `true` のクエリは skill を呼ぶべきもの、`false` は呼んではいけないものです。

## 旧スクリプトからの移行

| 旧 | 新 |
|----|----|
| `./test_all.sh` | `uv run pytest` |
| `./test_skill.sh messaging-api -v` | `uv run line-skills eval messaging-api -v` |
| `./test_skill_e2e.sh messaging-api --runs 3 -v` | `uv run line-skills eval messaging-api --mode e2e --runs 3 -v` |
| `python optimize_description.py ...` | `uv run line-skills optimize <skill>` |

---

# English

Trigger-accuracy evaluation and description optimization for line-skills.

## Setup

### Prerequisites

The tests spawn `claude` CLI subprocesses via `claude-agent-sdk`. You need Claude Code installed and logged in (or `ANTHROPIC_API_KEY` set).

```bash
# 1) Verify Claude Code is installed
claude --version
# Install: https://docs.claude.com/en/docs/claude-code/install

# 2) Log in (first time only)
claude            # then /login → browser OAuth → /exit

# 3) Smoke test
claude -p "hello"

# Alternative for CI: export ANTHROPIC_API_KEY=sk-ant-...
```

Each query has a 60-second timeout, so missing auth won't hang forever — it surfaces an error per query.

### Install dependencies

```bash
brew install uv
cd tests
uv sync
```

## Run

```bash
uv run pytest                                  # All skills, simulated
uv run pytest -k messaging_api                 # One skill
uv run pytest -n auto --runs 3 --threshold 0.9 # Parallel, 3 runs, 90% bar

uv run line-skills eval --verbose                          # Human-readable
uv run line-skills eval messaging-api --mode e2e --runs 3  # Real claude -p
uv run line-skills optimize line-login --iterations 3      # Improve description
```

## Layout

```
tests/
├── pyproject.toml
├── conftest.py
├── test_triggers.py
├── eval/
│   ├── skill_io.py    # SKILL.md frontmatter + assessment loader
│   ├── assessor.py    # simulated + e2e modes
│   ├── optimizer.py   # iterative description improvement
│   └── cli.py         # `line-skills` typer CLI
└── data/<skill>/{assessment_set.json,scope.json}
```

| Mode | Behavior |
|------|----------|
| `simulated` (default) | Agent SDK as LLM judge — fast, for CI and design iteration |
| `e2e` | Real `claude -p` subprocess, checks stream-json for `Skill` tool calls |
