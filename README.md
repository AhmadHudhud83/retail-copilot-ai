***


# Retail Analytics Copilot (DSPy + LangGraph)

A local AI agent that answers retail analytics questions using **RAG** (for policy/dates) and **Text-to-SQL** (for database queries), orchestrated by LangGraph and optimized with DSPy.

## 🏗️ Graph Design
The agent uses a stateful **LangGraph** workflow with 6 main nodes:
*   **Router & Retriever:** Classifies user intent (RAG-only vs. Hybrid) and fetches relevant policy/KPI chunks to ground the model.
*   **Planner:** Analyzes retrieved docs to extract precise constraints (e.g., converting "Summer 2016" into SQL-compatible `BETWEEN` dates) before SQL generation.
*   **SQL Generator (DSPy):** Converts natural language + Schema + Plan into strict SQLite queries.
*   **Executor & Repair Loop:** Runs queries with a regex-based "Safety Net". If execution fails (e.g., "no such column"), the error is fed back to the Generator for self-correction (up to 2 retries).

## 📊 DSPy Optimization Impact
I chose to optimize the **TextToSQL** module (the "Brain") using `BootstrapFewShot` with a custom training set of 20 examples.

| Metric | Before (Zero-Shot) | After (Optimized) | Delta |
| :--- | :--- | :--- | :--- |
| **SQL Exec Success** | ~16% | **67%** | **+50%** |
| **Common Failures** | Hallucinated `YEAR()`, `TOP`, `Cost` | Correct `strftime`, `LIMIT`, `0.7*Price` | **Eliminated** |
| **Data Alignment** | Random years (1997/2022) | Correctly targets **2016** (DB year) | **Aligned** |

*The optimization was critical to stop the model from hallucinating a `Cost` column and force it to calculate Margin manually.*

## ⚖️ Trade-offs & Assumptions
*   **Date Alignment (2016):** The provided Northwind SQLite database actually contains data from **2016–2018**, despite the assignment prompt mentioning "1997". I aligned the docs and logic to **2016** to ensure the agent returns actual data rather than empty sets.
*   **Cost Approximation:** The database lacks a `Cost` or `COGS` column. The system rigidly assumes `Cost = UnitPrice * 0.7` per the prompt instructions.
*   **Strict Typing:** To satisfy the Output Contract, the final Synthesizer uses regex parsing to strip conversational text and return raw `int` or `float` values.
## 🚀 Quickstart

**1. Prerequisites**
*   Python 3.10+
*   [Ollama](https://ollama.com) running locally.
*   Pull the model:
    ```bash
    ollama pull phi3.5:3.8b-mini-instruct-q3_K_M
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
|-- tests
|   |-- all_tables_check_sql.py
|   |-- evaluate_improvement.py
|   |-- ground_truth_answers_for_sqls.py
|   |-- test_dspy.py
|   |-- test_trainset.py
|   |-- verify_sql_dates.py
|   `-- verify_views.py
`-- train_dspy.py

```

Side Note – Data Availability Issue

During testing of the hybrid and SQL-based examples, it was observed that several queries were targeting historical periods such as 1997 (Summer Beverages 1997 and Winter Classics 1997). However, the current Northwind database snapshot only contains order data from 2012-07-10 to 2023-10-28. As a result, these queries return empty or None results.

Resolution: To ensure accurate query execution and meaningful outputs, all example queries will be updated to use a date range that exists in the current dataset. This adjustment will maintain the integrity of the hybrid evaluation while preserving the intended logic of the original examples.
