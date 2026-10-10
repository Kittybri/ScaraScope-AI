# ScaraScope AI

<p align="center">
  <img src="assets/readme/hero.svg" alt="ScaraScope AI: financial research made traceable, illustrated with SEC documents, charts, and connected AI nodes" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/Kittybri/ScaraScope-AI/actions/workflows/ci.yml"><img src="https://github.com/Kittybri/ScaraScope-AI/actions/workflows/ci.yml/badge.svg" alt="Python CI status" /></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3C78A8?logo=python&logoColor=white" alt="Python 3.11 or newer" />
  <img src="https://img.shields.io/badge/Backend-FastAPI-078D79?logo=fastapi&logoColor=white" alt="FastAPI backend" />
  <img src="https://img.shields.io/badge/Data-SEC%20EDGAR-243A5C" alt="SEC EDGAR financial data" />
  <img src="https://img.shields.io/badge/Status-Portfolio%20Prototype-355B75" alt="Portfolio prototype" />
</p>

<p align="center">
  <strong>Evidence first. Language second.</strong><br/>
  A modular Python financial-research assistant that combines public SEC financial data,
  reproducible calculations, evidence-linked filing questions, and optional local/cloud AI.
</p>

<p align="center">
  <a href="#what-it-does">Explore features</a> ·
  <a href="#quick-start">Run the demo</a> ·
  <a href="#engineering-evidence">Engineering evidence</a> ·
  <a href="#architecture">Architecture</a> ·
  <a href="docs/ENGINEERING_CASE_STUDY.md">Case study</a>
</p>

> **Project status: v0.4 prototype.** Public-company financial analysis and best-effort filing-text Q&A are implemented, but this is not a trading platform, investment adviser, or production-grade financial-data service. Figures in `DEMO` are fictional. Groq and Oracle Cloud are not configured in the repository.

## What it does

<p align="center">
  <img src="assets/readme/features.svg" alt="Six ScaraScope capabilities: SEC filing Q&A, financial analysis, comparisons and DCF, hybrid inference, report exports, and engineering benchmarks" width="100%" />
</p>

| Research capability | Current implementation |
| --- | --- |
| **SEC financial intelligence** | Retrieve annual US-GAAP XBRL Company Facts for supported U.S. public companies; preserve available filing provenance and reporting periods. |
| **Ask a filing** | Search extracted 10-K and 10-Q sections using **lexical retrieval**; return evidence labels and original filing links, with optional LLM synthesis. |
| **Financial analysis** | Calculate revenue growth and profit margins in Python, not in an LLM. |
| **Comparisons and valuation** | Side-by-side fundamentals and an **illustrative DCF** based on *user-supplied* assumptions, not stock-price predictions. |
| **Hybrid AI** | Configurable Groq and Ollama providers, rule-based selection, graceful fallback, and a `local_only` policy that blocks cloud fallback. |
| **Research outputs** | Bounded research workflows, source-aware PDF/Excel exports, and a manually checked filing watchlist. |
| **Engineering Lab** | Offline benchmarks, automated tests, failure simulations, recorded results, and a dedicated inspection dashboard. |

**Important boundaries:** Filing extraction can miss sections, evidence references are not guaranteed exact paragraph deep links, and citation-label checks do not prove the semantic truth of arbitrary AI answers. Embedding-based RAG and live LLM quality benchmarks are future work.

## Quick start

Run a **fully offline fictional demo**, with no API keys or Oracle account required.

```bash
git clone https://github.com/Kittybri/ScaraScope-AI.git
cd ScaraScope-AI

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e '.[test]'

cp .env.example .env            # Windows: copy .env.example .env
uvicorn scarascope.api:app --reload --host 127.0.0.1 --port 8000
```

| Open locally | Try this |
| --- | --- |
| **[Research dashboard](http://127.0.0.1:8000)** | Enter `DEMO` and run financial analysis, company research, or *Ask a filing*. |
| **[Engineering Lab](http://127.0.0.1:8000/engineering)** | Run the offline benchmark and inspect the cases. |
| **[API reference](http://127.0.0.1:8000/docs)** | Explore FastAPI endpoints and typed request/response models. |

Those localhost links work **after the server starts**. To query a real ticker such as `MSFT`, set `SEC_USER_AGENT` in your untracked `.env` to an application identifier containing your real contact email. No SEC API key is needed for public EDGAR data.

## Engineering evidence

ScaraScope is built as an inspectable software project, not a feature-count competition.

| Independently scoped check | Last verified offline result |
| --- | ---: |
| Historical financial checks using fixed SEC-source-linked references | **34 / 34** |
| Deterministic arithmetic checks | **6 / 6** |
| Synthetic lexical-retrieval checks | **5 / 5** |
| Simulated provider reliability and privacy checks | **6 / 6** |
| Full automated Python test suite | **60 passing tests** |

These are **offline regression/fixture results** from the v0.4 development run, **not real-world LLM answer-accuracy scores**. The fixed financial reference cases use historical Apple FY2023 and Microsoft FY2024 filing values. To reproduce the benchmark:

```bash
python -m pytest -q
python -m scarascope.evaluation.runner --fail-on-regression
```

The CI workflow runs the tests and saves a benchmark JSON artifact. See the [verified v0.4 run](https://github.com/Kittybri/ScaraScope-AI/actions/runs/38070810895), [benchmark methodology](docs/BENCHMARKS.md), and [engineering case study](docs/ENGINEERING_CASE_STUDY.md). Benchmarks are kept separate by category so a passing arithmetic test cannot masquerade as proof of LLM reasoning quality.

## Architecture

<p align="center">
  <img src="assets/readme/architecture.svg" alt="ScaraScope pipeline: browser, API and Discord interfaces; SEC retrieval; deterministic Python analysis; optional Ollama or Groq; reports and engineering checks, with cross-cutting privacy and verification" width="100%" />
</p>

The core is **headless and modular**. Discord and the web dashboard are interfaces, not the research engine.

```text
scarascope/
├── api/                HTTP endpoints and authentication
├── adapters/discord/   Optional Discord client
├── ai/
│   ├── providers/      Ollama and Groq adapters
│   ├── retrieval/      Document ranking and evidence labels
│   └── agents/         Bounded plans and verification steps
├── data/sec/           EDGAR access, XBRL, filing sections
├── finance/            Ratios, peer comparisons, DCF
├── services/           Research and document Q&A workflows
├── reports/            PDF and Excel generators
├── evaluation/         Datasets, test runners, result records
├── verification/       Source, date, unit, claim checks
├── observability/      Provider events and diagnostics
├── storage/            Metadata and watchlist persistence
└── static/             Web dashboard and Engineering Lab
```

Full design constraints are documented in [ARCHITECTURE.md](docs/ARCHITECTURE.md). ScaraScope is **independent of the author's personal Scaramouche and Wanderer projects**.

## Optional integrations

<details>
<summary><strong>Use real SEC data</strong></summary>

Set `SEC_USER_AGENT` in `.env` with a real contact email, restart, and enter a supported U.S. stock ticker. Retrieval is subject to SEC fair-access limits, source formatting, and XBRL taxonomy coverage.

</details>

<details>
<summary><strong>Enable Groq for cloud-eligible research</strong></summary>

```dotenv
GROQ_API_KEY=your-key-here
GROQ_MODEL=openai/gpt-oss-20b
```

Verify your model availability before use. Never commit your real `.env` file.

</details>

<details>
<summary><strong>Enable local Ollama inference</strong></summary>

Install Ollama and pull an appropriate model, then configure:

```dotenv
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=llama3.2:3b
```

When the backend runs on Oracle, `127.0.0.1` refers to the cloud VM, **not your laptop**. Use an authenticated private connection; never expose the Ollama port publicly. `local_only` disables cloud fallback by policy.

</details>

<details>
<summary><strong>Use the optional Discord interface</strong></summary>

```bash
pip install -e '.[discord]'
python -m scarascope.discord_bot
```

Configure `DISCORD_BOT_TOKEN` and run FastAPI separately. Discord remains a thin API client.

</details>

## Documentation and development

| Guide | Purpose |
| --- | --- |
| [Features](docs/FEATURES.md) | Implemented functionality and boundaries |
| [Architecture](docs/ARCHITECTURE.md) | Responsibility boundaries and extension points |
| [Evaluation](docs/EVALUATION.md) | Test methodology and limitations |
| [Benchmarks](docs/BENCHMARKS.md) | Historical reference dataset and reproducibility |
| [Security](docs/SECURITY.md) | Privacy, authentication, rate limits, safe deployment |
| [Engineering case study](docs/ENGINEERING_CASE_STUDY.md) | Engineering decisions and tradeoffs |

**Development roadmap:** robust filing parsing and stronger claim verification; real-world held-out financial QA benchmarks; semantic retrieval if it improves measured quality; secure Oracle deployment and measured Ollama/Groq performance.

> **Deployment caution:** Set `SCARASCOPE_API_KEY` and `SCARASCOPE_REQUIRE_AUTH=true` before any public deployment; use HTTPS, network controls, and appropriate per-user quotas. The existing prototype does not implement full multi-user isolation. Research is informational only and requires source review for consequential decisions.

<sub>README illustrations are conceptual SVG graphics made for this repository, not screenshots or live performance measurements. No software license has been granted in this repository.</sub>
