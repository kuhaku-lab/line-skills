# line-skills

**Claude Code Skills for LINE platform development.**

API references, design guides, and expert knowledge for the LINE platform, packaged as six Skills aligned with the latest LINE Developers documentation. Covers Messaging API, LINE Login, LIFF, LINE MINI App, Notification Messages, and Creators Market.

[`日本語`](README.md) ・ `English` ・ [`Skills`](#skills) ・ [`Quick Start`](#quick-start) ・ [`Testing`](#testing)

---

## Quick Start

### A. Install as a Claude Code Plugin (recommended)

```bash
/plugin marketplace add kuhaku-lab/line-skills
/plugin install line-skills@kuhaku-lab-line-skills
```

Then `/reload-plugins` to activate.

### B. Install as Skills (à la carte)

```bash
# All skills
npx skills add kuhaku-lab/line-skills

# Pick specific ones
npx skills add kuhaku-lab/line-skills@messaging-api
npx skills add kuhaku-lab/line-skills@line-liff
# ... see table below for skill names
```

### C. Try locally (no install)

```bash
git clone https://github.com/kuhaku-lab/line-skills.git
claude --plugin-dir ./line-skills
```

---

## Skills

| Skill | Coverage | Example triggers |
|-------|----------|------------------|
| [**messaging-api**](skills/messaging-api/) | Webhook signature verification / Reply・Push・Multicast・Narrowcast・Broadcast / Flex Message / Rich Menu / Audience / Coupons / Insights / Mark as Read | "Send a push from a LINE bot", "Design a Flex Message", "Switch rich menu tabs" |
| [**line-login**](skills/line-login/) | OAuth 2.0 / PKCE / ID Token (JWT) verification / Token refresh / User profile / Bot linking / Login button design | "Implement LINE Login", "Verify an ID token", "Prompt friend-add" |
| [**line-liff**](skills/line-liff/) | LIFF SDK v2.28+ / `liff.init` / `sendMessages` / Share Target Picker / `scanCodeV2` / `requestFriendship` / Pluggable SDK / LIFF plugins / Server API / CLI | "Build a LIFF app", "QR scan in LIFF", "Generate a permanent link" |
| [**line-mini-app**](skills/line-mini-app/) | Service Messages / Common Profile Quick Fill / In-App Purchase (JP) / Console (3 channels) / Custom Path / Submission review | "Submit MINI App", "Send a service message", "Implement Quick Fill" |
| [**line-notification-message**](skills/line-notification-message/) | Phone-number-based PNP push (LINE通知メッセージ / LON) / SHA256 hashing / Template & flexible types / Delivery webhook / Consent flow / SMS auth | "Send LINE via phone number", "PNP webhook", "LON template" |
| [**line-creators-market**](skills/line-creators-market/) | 7 sticker types / Emoji / Themes / Technical specs / Review guidelines / Revenue model / AI usage declaration / LINE Sticker Maker / Market strategy | "Create LINE stickers", "APNG specs", "Review criteria" |

> Each Skill covers region-specific details for **Japan**, **Thailand**, and **Taiwan**.
> Skills load progressively — metadata is always in context, SKILL.md body loads on trigger, references load on demand.

---

## Testing

A pytest + Claude Agent SDK harness for trigger-accuracy testing lives under `tests/`. See [`tests/README.md`](tests/README.md) for full details.

### Setup

```bash
brew install uv         # or: curl -LsSf https://astral.sh/uv/install.sh | sh
cd tests
uv sync
```

### Common commands

```bash
# Fast evaluation of all skills (simulated mode)
uv run pytest

# Focused run on one skill
uv run line-skills eval messaging-api -v

# E2E mode (real claude -p invocation)
uv run line-skills eval messaging-api --mode e2e --runs 3 -v

# Auto-optimize a description
uv run line-skills optimize line-login --iterations 3
```

<details>
<summary><b>Current scores</b> (click to expand)</summary>

Each Skill has an assessment set across 4 languages (en, ja, zh-TW, th) with both `should_trigger: true` and `should_trigger: false` queries.

| Skill | E2E accuracy | Simulated accuracy | Queries | Measured |
|-------|-------------:|-------------------:|--------:|----------|
| line-notification-message | **100%** | **100%** | 73 | 2026-03-23 |
| line-liff | 96% | 92% | 72 | 2026-03-20 |
| line-login | 95% | 92% | 65 | 2026-03-20 |
| line-mini-app | 94% | 99% | 176 | 2026-03-23 |
| messaging-api | 93% | **100%** | 70 | 2026-03-20 |
| line-creators-market | 88% | **100%** | 68 | 2026-03-20 |

- **E2E**: runs real `claude -p` and detects `Skill` tool calls via stream-json
- **Simulated**: shows the description alone to Claude Agent SDK and asks whether the skill should trigger (fast & cheap)

</details>

---

## License

See [LICENSE](LICENSE).
