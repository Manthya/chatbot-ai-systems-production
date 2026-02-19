# MCP Server Setup Guide

This guide details the Model Context Protocol (MCP) servers integrated into the Chatbot AI System. These servers extend the chatbot's capabilities with file access, web research, coding tools, and external integrations.

## 🚀 Quick Start

1.  **Install Dependencies**: Ensure you have `npx` (Node.js) installed.
2.  **Configure Environment**: Copy `.env.example` to `.env` and fill in the API keys for the tools you want to use.
3.  **Restart Server**: The chatbot will automatically load enabled servers on startup.

## 🛠️ Available Context Servers

### Core System (The "OS" Layer)
*Basic computer literacy: reading files, memory, and database access.*

| Capability | Server | Env Var Required | Description |
| :--- | :--- | :--- | :--- |
| **File Access** | `filesystem` | None | Access to files in the current working directory. |
| **Long-Term Memory** | `postgres` | `DATABASE_URL` | Access to the chatbot's PostgreSQL database. |
| **Knowledge Graph** | `memory` | None | Graph-based memory for storing concepts and relationships. |
| **Date & Time** | `time` | None | Get current time and timezone information. |

### 🌐 The Researcher (Web & Internet)
*Give your bot eyes to see the web and retrieve fresh information.*

| Capability | Server | Env Var Required | Description |
| :--- | :--- | :--- | :--- |
| **Web Search** | `brave-search` | `BRAVE_API_KEY` | High-quality web search using Brave's API. |
| **Browser Automation**| `puppeteer` | None | Headless browser for scraping and interacting with web pages. |
| **Simple HTTP** | `fetch` | None | Basic HTTP client for fetching web content. |

### 👨‍💻 The Developer (Coding & Ops)
*Essential for a "Coding Bot" to actually build and deploy software.*

| Capability | Server | Env Var Required | Description |
| :--- | :--- | :--- | :--- |
| **GitHub Actions** | `github` | `GITHUB_TOKEN` | Manage repositories, issues, and PRs. |
| **Git Ops** | `git` | None | Local Git operations. |
| **Container Ops** | `docker` | Docker Socket | Manage Docker containers (requires socket access). |
| **Cloud Sandbox** | `e2b` | `E2B_API_KEY` | Run code safely in a cloud sandbox. |

### 🧠 The Brain (Reasoning & Analysis)
*Tools that help the model "think" better before answering.*

| Capability | Server | Env Var Required | Description |
| :--- | :--- | :--- | :--- |
| **Deep Thinking** | `sequential-thinking`| None | Tool for structured, multi-step reasoning. |
| **Data Analysis** | `sqlite` | None | SQLite database for data analysis and storage (`data.db`). |

### 🔌 The Connector (Integrations)
*Connects your bot to real-world work apps.*

| Capability | Server | Env Var Required | Description |
| :--- | :--- | :--- | :--- |
| **Slack** | `slack` | `SLACK_BOT_TOKEN`<br>`SLACK_TEAM_ID` | Send messages and interact with Slack. |
| **Google Maps** | `google-maps` | `GOOGLE_MAPS_API_KEY`| Search places and get directions. |
| **Sentry** | `sentry` | `SENTRY_AUTH_TOKEN` | Check error reports and issues. |

## 🔑 Environment Variables

Add the following to your `.env` file to enable specific servers:

```bash
# Research
BRAVE_API_KEY=your-key-here

# Developer
GITHUB_TOKEN=your-token-here (classic token with repo scope)
E2B_API_KEY=your-key-here

# Integrations
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_TEAM_ID=T12345678
GOOGLE_MAPS_API_KEY=your-key-here
SENTRY_AUTH_TOKEN=your-token-here
```
