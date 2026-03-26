# Order-to-Cash (O2C) Graph Intelligence System

This repository contains a full-stack Graph Intelligence platform designed to visualize complex SAP Order-to-Cash data relationships and provide a natural language querying interface. 

The system instantly maps 19 interconnected SAP tables (Sales Orders, Deliveries, Billing Docs, Payments, Customers) into a performant 2D force-directed graph. Users can interact with the graph visually or use the integrated AI Chat Agent to query the underlying dataset in plain English.

---

## 🏗️ Architecture

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

## 🚀 Getting Started

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

## 🌍 Deployment Guide

To deploy this project to the public internet, you need to host the backend and frontend separately. The backend is configured with wildcard CORS (`allow_origins=["*"]`) so it will successfully accept requests from your deployed frontend domain.

### 1. Deploying the Backend (Render / Railway / Heroku)
The backend is a standard FastAPI app. The easiest way to deploy it is via a platform-as-a-service like Render.
1. Create a `Procfile` (or configure the start command in your dashboard):
   ```
   web: uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
2. Set the Environment Variable in your dashboard:
   - `GROQ_API_KEY`: `your-production-groq-key`
3. Deploy! Note the public URL (e.g., `https://my-backend.onrender.com`).

### 2. Deploying the Frontend (Vercel / Netlify / GitHub Pages)
Because the frontend connects to the backend, you must point the Vite proxy/API calls to your newly deployed backend URL.

1. In `frontend/vite.config.js`, update the API proxy or replace it with a direct hardcoded fetch URL pointing to your backend in production. The easiest method for Vercel is replacing `fetch('/api/graph')` in the React code with `fetch('https://your-backend-url.com/api/graph')`.
2. Link your GitHub repository to Vercel.
3. Use the build command: `npm run build`
4. Use the output directory: `dist`
5. Deploy!
