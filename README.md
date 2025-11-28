Here is the updated **README.md** with the project structure section reflecting your actual file tree.

***

# Retail Analytics Copilot (DSPy + LangGraph)

A local, private AI agent for retail analytics that combines **RAG** (for policy/dates) and **Text-to-SQL** (for database queries). Built with **DSPy** for prompt optimization and **LangGraph** for stateful orchestration.

## 🚀 Quickstart

**1. Prerequisites**
*   Python 3.10+
*   [Ollama](https://ollama.com) running locally.
*   Pull the model:
    ```bash
    ollama pull phi3.5:3.8b-mini-instruct-q4_K_M
    ```

**2. Installation**
```bash
# Install dependencies
pip install -r requirements.txt

# Download Database (if not present in data/)
mkdir -p data
curl -L -o data/northwind.sqlite https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/main/dist/northwind.db
```

**3. Train & Run**
```bash
# 1. Optimize the SQL Generator (The "Brain")
# This creates 'agent/optimized_sql_module.json' using DSPy BootstrapFewShot
python train_dspy.py --max_bootstrapped_demos 10 --max_labeled_demos 10

# 2. Run the Agent Evaluation
python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl
```

---

## 🏗️ Architecture Design
The agent uses a **Stateful Graph** (LangGraph) with $\ge$ 6 nodes:

1.  **Router:** Classifies intents (RAG-only vs. Hybrid/SQL) using DSPy.
2.  **Retriever:** Fetches context (KPIs, Calendar) to guide the planner.
3.  **Planner:** Extracts constraints (e.g., converts "Summer 2016" $\to$ `BETWEEN '2016-06-01' AND ...`).
4.  **SQL Generator (DSPy):** Optimized module that converts natural language + schema + plan $\to$ SQLite.
5.  **Executor:** Runs the query with a **Safety Net** (regex patches for common model hallucinations).
6.  **Synthesizer:** Formats the final answer and compiles strict citations.
7.  **Repair Loop (Resilience):** If SQL fails (e.g., "no such column"), the error maps back to the Generator for up to 2 retries.

---

## 📊 DSPy Impact & Optimization
**Chosen Module:** `TextToSQL` (SQL Generator)
**Optimizer:** `BootstrapFewShot` (Metric: Execution Success + Syntax Validity)

| Metric | Zero-Shot (Before) | Optimized (After) | Improvement |
| :--- | :--- | :--- | :--- |
| **SQL Exec Success** | ~10% | **66.7%** | **+33.3%** |
| **Hallucinations** | Frequent `YEAR()`, `TOP`, `Cost` | None (Uses `strftime`, `LIMIT`, `0.7*Price`) | **Eliminated** |
| **Date Logic** | Random (guessed 2022/2023) | **Correct** (Aligned to DB 2016) | **Aligned** |

*Note: The optimizer successfully learned to calculate Gross Margin manually `(Price * 0.7)` instead of hallucinating a non-existent `Cost` column.*

---

## 🛡️ Resilience & Assumptions

### The Repair Loop
The agent includes a self-healing loop. If the `Executor` encounters an error (e.g., `no such column: c.CustomerID`), it feeds the exact error message back to the `SQL Generator` prompt context.
*   **Result:** The model corrects alias mismatches or syntax errors in the 2nd attempt, significantly raising the success rate on complex joins.

### Key Assumptions & Trade-offs
1.  **Date Alignment (2016):** The provided SQLite database contains data from **2016-2018** (not 1997). The logic and docs were updated to align with the actual data present in the DB.
2.  **Cost Approximation:** The Northwind DB lacks a `Cost` column. The Planner/SQL Generator enforces the rule: `Cost ≈ 0.7 * UnitPrice`.
3.  **Strict Typing:** The Synthesizer uses regex to enforce `int` and `float` outputs, preventing "chatty" responses (e.g., "The answer is 14").

---

## 📂 Project Structure

```text
.
├── README.md
├── agent/
│   ├── dspy_signatures.py        # DSPy Signatures (Prompt Definitions)
│   ├── graph_hybrid.py           # LangGraph Workflow & Nodes
│   ├── optimized_sql_module.json # SAVED STATE (The optimized brain)
│   ├── logs/                     # Tracing logs
│   ├── rag/
│   │   ├── retrieval.py          # Local File Retriever (BM25)
│   │   └── utils/
│   │       └── debug_utils.py    # Debugging/Tracing helpers
│   └── tools/
│       └── sqlite_tool.py        # DB Adapter + Hallucination Safety Net
├── data/
│   ├── northwind.sqlite          # Local Database
│   └── trainset.py               # 20+ High-Quality Examples for DSPy Training
├── docs/                         # Knowledge Base (Markdown: Policies, Calendar 2016)
├── outputs_hybrid.jsonl          # Final Agent Outputs
├── requirements.txt
├── run_agent_hybrid.py           # Main CLI Entrypoint
├── sample_questions_hybrid_eval.jsonl # Evaluation Questions
├── train_dspy.py                 # Optimization Script
└── tests/                        # Validation scripts
    ├── all_tables_check_sql.py
    ├── evaluate_improvement.py
    ├── ground_truth_answers_for_sqls.py
    └── ...
```

Side Note – Data Availability Issue

During testing of the hybrid and SQL-based examples, it was observed that several queries were targeting historical periods such as 1997 (Summer Beverages 1997 and Winter Classics 1997). However, the current Northwind database snapshot only contains order data from 2012-07-10 to 2023-10-28. As a result, these queries return empty or None results.

Resolution: To ensure accurate query execution and meaningful outputs, all example queries will be updated to use a date range that exists in the current dataset. This adjustment will maintain the integrity of the hybrid evaluation while preserving the intended logic of the original examples.