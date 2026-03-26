# Order-to-Cash (O2C) Graph Intelligence System
<img width="2558" height="1467" alt="image" src="https://github.com/user-attachments/assets/6155be52-3bf8-4bad-a961-1758623e7e81" />

This repository contains a full-stack Graph Intelligence platform designed to visualize complex SAP Order-to-Cash data relationships and provide a natural language querying interface. 

The system instantly maps 19 interconnected SAP tables (Sales Orders, Deliveries, Billing Docs, Payments, Customers) into a performant 2D force-directed graph. Users can interact with the graph visually or use the integrated AI Chat Agent to query the underlying dataset in plain English.

---

## 🏗️ Architecture & Directory Structure

```text
order-to-cash/
├── backend/               <-- FastAPI & DuckDB API
│   ├── main.py
│   ├── query_engine.py    <-- LLM text-to-SQL logic
│   ├── graph_builder.py   <-- NetworkX graph construction
│   ├── guardrails.py      <-- Query filtering
│   ├── data_loader.py
│   └── schema.md          <-- Schema injected into prompts
├── frontend/              <-- React & Vite SPA
│   ├── src/
│   │   ├── components/
│   │   │   ├── GraphCanvas.jsx  <-- Sigma.js WebGL rendering
│   │   │   ├── ChatSidebar.jsx  <-- LLM chat interface
│   │   │   └── NodePopup.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── sap-o2c-data/          <-- Raw SAP JSONL Datasets
├── sessions/              <-- Exported AI Chat Logs
└── README.md
```

The application is split into a Python backend and a React frontend.

### 1. Backend (`/backend`)
A high-performance API server responsible for data ingestion, graph construction, and NLP-to-SQL translation.
* **FastAPI**: Serves the REST API endpoints (`/api/graph` and `/api/chat`).
* **DuckDB**: An in-memory analytical database used to instantly ingest, join, and query the 19 raw JSONL datasets.
* **NetworkX**: Processes DuckDB results to build the nodes and edges of the O2C graph (enforcing a robust 800-node cap for browser performance).
* **Groq SDK (Llama 3)**: Translates plain English user questions into executable DuckDB SQL commands based on the injected SAP schema.

**Key Files:**
- `data_loader.py`: Ingests JSONL records into DuckDB.
- `graph_builder.py`: Queries DuckDB to construct the nodes and sequential edges (Customer → Sales Order → Delivery → Billing Doc → Journal Entry → Payment).
- `query_engine.py`: Handles LLM prompt engineering, guarding against "mixed" prompts, executing generated SQL, and returning formatted results.
- `guardrails.py`: Hard-rejects out-of-domain chat queries before they consume LLM tokens.

### 2. Frontend (`/frontend`)
A modern, responsive single-page application focused on high-density data visualization.
* **React 18 & Vite**: Core framework and bundler.
* **Sigma.js v3 & React-Sigma**: WebGL accelerating graph visualization engine capable of smoothly rendering thousands of items.
* **Graphology**: Layout algorithms (Circular & ForceAtlas2) to organize the interconnected nodes organically.
* **React-Markdown**: Natively renders rich text, tables, and code blocks returned by the AI Chat Agent.

**Key Components:**
- `GraphCanvas.jsx`: The Sigma graph container. Handles complex WebGL interactions like dimming unconnected nodes and highlighting the 1-hop neighborhood of hovered/clicked entities.
- `ChatSidebar.jsx`: The chat interface for the LLM. 
- `NodePopup.jsx`: Displays key metadata properties for any clicked node.

---

## 🧠 Architecture Decisions & Strategy

### 1. Database Choice: In-Memory DuckDB
To process 19 separate JSONL datasets representing the entire SAP Order-to-Cash flow, we selected **DuckDB**. 
- **Zero-Setup Analytics**: DuckDB natively ingests `.jsonl` files and performs automatic schema inference.
- **Join Performance**: Because O2C analysis heavily relies on deep relational joins (Customer → Order → Delivery → Billing → Payment), an analytical columnar engine like DuckDB outperforms standard SQLite or transactional DBs. 
- **Stateless Execution**: Running in-memory allows the FastAPI server to remain strictly stateless, perfectly suited for cloud deployment (e.g., Render).

### 2. Prompt Engineering & Execution Stability
The Chat Agent is powered by the Groq API (`openai/gpt-oss-120b`). Because 120B opensource models occasionally struggle with strict markdown adherence and formatting, we implemented several novel, highly structured guardrails to guarantee UI stability and SQL correctness:

- **Spec-Style System Prompting**: The system prompt abandons standard prose in favor of a strict machine-readable spec format. It outlines exactly 9 numbered MANDATORY CONSTRAINTS, enforces numeric casting (`SUM(CAST(col AS DOUBLE))`), and provides a rigorous `OUTPUT FORMAT` skeleton followed by a concrete `OUTPUT EXAMPLE`. This drastically reduced formatting hallucinations.
- **Robust ID Tracking (OR-Chaining)**: When users query bare IDs (e.g., `91150147`) without specifying the document type, the Prompt forces the LLM to dynamically construct `WHERE` clauses using `OR` logic across all primary key tables (`salesOrder OR deliveryDocument OR billingDocument`). This completely eliminates zero-result errors caused by the LLM blindly guessing the wrong document type.
- **The "Nuclear SQL Sweep" (Fallback Regex Scraper)**: If the LLM forgets to wrap its output in ` ```sql ` markdown fences, the backend refuses to let the raw code bleed into the chat UI. A two-step regex pipeline (featuring multiline DOTALL capabilities) actively scans the conversational text for C-style comment blocks `/* ... */` and stray SQL lines (`SELECT`, `JOIN`, `WHERE`). It physically surgically extracts the SQL out of the conversational text and forces it into the bounded UI code block.
- **Double-Layer UI Protection**: Even if a query is technically correct, execution failures (like DuckDB type-casting errors) are intercepted before returning to the frontend. The system wipes the hallucinated SQL block and explanation from the payload entirely, replacing it with a polite, conversational fallback message so the end-user never sees a Python stack trace or a massive wall of SQL in their chat bubble. 

### 3. Regex Guardrails & Token Conservation
Large Language Models are expensive and rate-limited. To prevent token waste on unrelated chat queries, we built a token-free Python interceptor:
- **Boundary Filtering**: Before hitting the Groq API, `guardrails.py` performs a set intersection against a large dictionary of O2C synonyms, abbreviations, and financial terms (e.g., `cust`, `deliv`, `dso` `sum`). 
- **Bare ID Allowlist**: The guardrail is fine-tuned to explicitly allow queries consisting purely of scalar integers (Sales Orders) or standard SAP prefixes (like `JE_94006...`), ensuring users can quickly track documents without writing full sentences.
- **Fail-Fast**: If no relevant O2C concepts or valid ID patterns are detected, the API immediately returns a 400 rejection, saving the LLM tokens completely.

---

## 🚀 Getting Started

> **Note on Deployment**: This application's backend is hosted on a free tier instance of Render. If the app hasn't been used in the last 15 minutes, **the initial graph load and chat functionality may take ~50 seconds to wake up**. Please be patient on the first request!

### Prerequisites
- Python 3.10+
- Node.js 18+
- A [Groq API Key](https://console.groq.com/) for the Chat Agent.

### Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate | Mac/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the `backend/` folder and add your Groq API key:
   ```env
   GROQ_API_KEY=your_actual_api_key_here
   ```
4. Start the FastAPI server (it will automatically ingest the `sap-o2c-data` on startup):
   ```bash
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup
1. Open a new terminal and navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
4. Open your browser to `http://localhost:5173`.

---

## ✨ Features

- **Force-Directed Graph**: Watch the data organically pull itself into clusters based on relationships.
- **Node Neighborhood Highlighting**: Click or hover on any entity to dim the rest of the canvas and instantly see its direct upstream/downstream connections.
- **Deep Metadata Extraction**: Click nodes to view hidden properties, currency amounts, and connection counts extracted straight from the SAP JSONL files.
- **Natural Language Analytics**: Ask complex business questions like *"Which customer has the highest total net amount across all their sales orders?"* and let the Chat Agent write and execute the SQL instantly.
- **Responsive Layout**: Minimize the chat window to expand the graph canvas to 100% full-screen width.

---
