# AI Agent Toolkit

A lightweight, extensible AI Agent toolkit for automated diagnostics, code analysis, and workflow orchestration. Powered by LLM APIs.

## Features

- **Diagnostics Agent**: Automatically analyzes system issues, collects logs, and generates fix suggestions
- **Code Review Agent**: Scans codebases for bugs, style issues, and security vulnerabilities
- **Workflow Orchestrator**: Chains multiple AI agents into complex multi-step pipelines
- **Multi-LLM Support**: Works with OpenAI, Claude, and any OpenAI-compatible API endpoint

## Quick Start

```bash
pip install -r requirements.txt
```

### Run Diagnostics Agent

```bash
python -m agents.diagnostic --task "Analyze network connectivity issues in VBox virtual environment"
```

### Run Code Review Agent

```bash
python -m agents.code_review --path ./my-project --report output.md
```

### Run Workflow Pipeline

```bash
python -m agents.orchestrator --config workflows/example.yaml
```

## Configuration

Copy `config.example.yaml` to `config.yaml` and fill in your API keys:

```yaml
llm:
  provider: openai  # openai | claude | custom
  api_key: your-api-key-here
  model: gpt-4o
  base_url: https://api.openai.com/v1  # optional, for custom endpoints
```

## Architecture

```
ai-agent-toolkit/
├── agents/
│   ├── __init__.py
│   ├── base.py          # Base Agent class
│   ├── diagnostic.py    # Diagnostics Agent
│   ├── code_review.py   # Code Review Agent
│   └── orchestrator.py  # Multi-agent workflow engine
├── core/
│   ├── __init__.py
│   ├── llm_client.py    # Unified LLM API client
│   ├── tools.py         # Built-in tools (shell, file, search)
│   └── memory.py        # Conversation memory management
├── workflows/
│   └── example.yaml     # Example workflow definition
├── config.example.yaml  # Configuration template
├── requirements.txt
└── main.py              # CLI entry point
```

## How It Works

The toolkit uses a **ReAct (Reasoning + Acting)** loop pattern:

1. **Reason**: The agent analyzes the task and decides what action to take
2. **Act**: Executes tools (run commands, read files, search code)
3. **Observe**: Processes the results
4. **Repeat**: Continues until the task is complete

Each agent can use built-in tools or custom plugins. The orchestrator chains multiple agents together, passing context between them for complex multi-step tasks.

## Example: Network Diagnostics Pipeline

```yaml
# workflows/network_diag.yaml
name: Network Diagnostics
agents:
  - id: collector
    type: diagnostic
    task: "Collect network configuration and connectivity data"
    tools: [shell, file_read]
  - id: analyzer
    type: diagnostic
    task: "Analyze collected data and identify root cause"
    depends_on: [collector]
  - id: fixer
    type: diagnostic
    task: "Generate step-by-step fix instructions"
    depends_on: [analyzer]
```

## License

MIT
