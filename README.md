# Helios Autonomous Store (Python)

Priority-driven AI workflow with MCP integration. Implements the CEO orchestrator, agents, and batch/parallel execution described in the HTML spec.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m helios run --dry-run
```

## Commands

- `python -m helios run` – run full workflow
- `python -m helios run --dry-run` – simulate with mock data
- `python -m helios repeat` – repeat the last executed action
- `python -m helios history` – show recent action history
- `python -m helios history --limit 20` – show more history entries
- `python -m helios demo` – print example outputs

## Structure

```
helios/
  __init__.py
  main.py
  config.py
  mcp_client.py
  utils/
    jsonio.py
    timing.py
  providers/
    google_drive.py
    google_sheets.py
  agents/
    ceo.py
    zeitgeist.py
    ethics.py
    audience.py
    product.py
    creative.py
    marketing.py
    publish.py
```

## Notes
- MCP client is a thin HTTP/WebSocket wrapper; adapt to your MCP.
- All agents are async and return structured JSON compatible with the spec.
- Quality gates and decision rules are enforced in `agents/ceo.py`.
