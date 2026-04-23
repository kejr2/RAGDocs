# RAGDocs

> Your team's documentation, finally answerable.
> Ask anything. Get a sourced answer in under 2 seconds.

## The Problem

Every engineering team has a hidden tax nobody measures.
New engineers join and spend their first 2–4 weeks
interrupting senior devs with questions that already
have answers — buried in Confluence, API docs, GitHub
READMEs, and internal wikis.

Senior engineers become unpaid support agents.
New engineers feel lost and slow.
The knowledge exists. It is just not accessible when
someone needs it.

## Demo

[INSERT_LOOM_LINK]

## Who This Is For

- Engineering teams onboarding new hires frequently
- Teams where senior devs are the human search engine
- Companies with docs across Confluence, Notion, GitHub
- Anyone tired of "just ask X, he'll know"

## How It Works

Upload your documentation. Ask anything in plain English.
Get a precise, sourced answer in under 2 seconds — with
a confidence score so you know how much to trust it.

**Flow:**
Upload docs → Ask question → LLM enhances query →
Hybrid retrieval → Rerank → Sourced answer + confidence score

**What makes it not a basic RAG:**
- Dual embeddings: separate models for code vs prose
  (understands your API docs AND your code snippets)
- LLM query enhancement: rewrites your question before
  searching so it finds what you meant, not just what you typed
- Hybrid retrieval + reranking across multiple doc types
- Confidence scoring: HIGH / MEDIUM / LOW on every answer
- Hard fallback: refuses to hallucinate if retrieval
  score is below threshold
- Click any source citation → PDF scrolls to that exact page
- Thumbs up/down on every answer feeds a live helpfulness score
- Honest "I don't know" panel shows you what it can't answer yet

**Stack:**
FastAPI · Qdrant · PostgreSQL · Gemini 2.5 Flash ·
React · Docker

## Live Metrics

The built-in dashboard tracks everything in real time.

| Metric | What it tells you |
|--------|-------------------|
| Avg Response Time | Is it fast enough to actually use? |
| Retrieval Quality | Is it finding the right chunks? |
| Fallback Rate | How often it says "I don't know" instead of guessing |
| Helpfulness % | Thumbs-up/down from real usage |
| Cost per Query | Exactly what each answer costs in USD |

Live at: `http://localhost:3001` → Metrics tab

## Set It Up In 10 Minutes

```bash
git clone <repo-url>
cd RAGDocs

# Add your keys
cp .env.example .env
# Fill in GOOGLE_API_KEY and DATABASE_URL

# Run everything
docker compose up -d
```

Frontend: http://localhost:3001  
API docs: http://localhost:8000/docs  
Metrics:  http://localhost:3001 → Metrics tab

## Roadmap

Things I've deliberately not built yet (and why):

- **SSO / Okta** — weeks of OAuth work, 0 user value until there are multiple users
- **Confluence / Notion connectors** — each is a week of OAuth + sync logic
- **Slack bot** — real value, building post-v1
- **Multi-tenant RBAC** — needs teams/orgs schema first
- **Helm chart** — nobody installs from a LinkedIn link

## Want This For Your Team?

Built to be adapted to any team's documentation stack.
Open an issue or reach me directly:

linkedin.com/in/adityakejriwal02
