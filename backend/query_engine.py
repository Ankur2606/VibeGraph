"""
query_engine.py — Uses Groq LLM to generate and execute SQL/Python against DuckDB.
"""
import os
import re
import traceback
from groq import Groq
from dotenv import load_dotenv
from data_loader import get_con

load_dotenv()

_groq_client = None


def _get_groq() -> Groq:
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            raise ValueError("GROQ_API_KEY not set in backend/.env")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _load_schema() -> str:
    schema_path = os.path.join(os.path.dirname(__file__), "schema.md")
    with open(schema_path, "r", encoding="utf-8") as f:
        return f.read()


SYSTEM_PROMPT = """You are an expert SAP Order-to-Cash data analyst. 
You have access to an in-memory DuckDB database with the following schema:

{schema}

When the user asks a question:
1. Write a SQL query against DuckDB to answer it.
2. Wrap the SQL in a ```sql code block.
3. After the code block, add a clear **Summary and Assumptions** section. Explicitly state the user's intent, and critically, list ANY AND ALL structural assumptions you made to write the query (e.g., "Assumed 'revenue' meant totalNetAmount", "Assumed recent meant 30 days"). Do not provide a generic explanation.
4. NEVER make up data — only use the tables defined in the schema.
5. IMPORTANT: All numeric values in these tables are imported as string/VARCHAR types.
   You MUST explicitly cast them to DOUBLE *inside* any aggregate functions or math operators. 
   Example: Use `SUM(CAST(col AS DOUBLE))` and NOT `SUM(col)`.
6. Use LIMIT clauses (max 50 rows) for list queries.
7. If the question requires graph traversal or path analysis, instead write a Python
   code block using the variable `con` (the DuckDB connection) and `result` as output.
8. IMPORTANT FOR JSON/VARCHAR COMPARISONS: If you are filtering by a string literal (e.g., `WHERE invoiceReference = 'JE_123'`), the left-hand column might have been inferred as a JSON struct by DuckDB. To avoid "Malformed JSON" errors, you MUST cast the column to VARCHAR first: `WHERE CAST(invoiceReference AS VARCHAR) = 'JE_123'`.
9. IMPORTANT FOR MIXED QUERIES (containing both O2C questions and unrelated questions):
   - You MUST identify ALL the domain-related parts of the question.
   - Do NOT ignore any domain-related questions just because an unrelated question exists.
   - Write a single comprehensive SQL query (e.g. using UNION ALL or multiple columns) that answers ALL the domain-related parts.
   - In your plain-English explanation, politely decline the unrelated/non-domain parts (e.g., "I cannot answer about the weather").
10. IMPORTANT FOR UNKNOWN IDs: If the user provides a bare ID (e.g., '90504218') without specifying if it is an order, delivery, or billing doc, DO NOT blindly assume it is a Sales Order! When doing JOIN chains, structure your `WHERE` clause to check ALL relevant tables: e.g., `WHERE CAST(soh.salesOrder AS VARCHAR) = 'x' OR CAST(odh.deliveryDocument AS VARCHAR) = 'x' OR CAST(bdh.billingDocument AS VARCHAR) = 'x'`. This ensures you match the document regardless of its specific type.
"""


def _extract_code(text: str) -> tuple[str, str]:
    """Return (code_type, code) from the first code block found."""
    sql_match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return "sql", sql_match.group(1).strip()
    py_match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if py_match:
        return "python", py_match.group(1).strip()
    return "none", ""


def _execute_sql(sql: str) -> str:
    try:
        con = get_con()
        rows = con.execute(sql).fetchall()
        cols = [d[0] for d in con.execute(sql).description]
        if not rows:
            return "No matching records were found in the database. Please try adjusting your search terms or filters."
        # Format as markdown table
        header = " | ".join(cols)
        sep = " | ".join(["---"] * len(cols))
        body = "\n".join(" | ".join(str(v) for v in row) for row in rows[:50])
        return f"{header}\n{sep}\n{body}"
    except Exception as e:
        return "I encountered a technical issue while generating the query. Could you please clarify your request or provide more specific terms?"


def _execute_python(code: str) -> str:
    try:
        con = get_con()
        local_ns = {"con": con, "result": None}
        exec(code, {}, local_ns)  # noqa: S102
        result = local_ns.get("result")
        return str(result) if result is not None else "Executed successfully (no result variable set)."
    except Exception:
        return "I encountered a programmatic error while attempting to traverse the graph. Please rephrase or try a different approach."


def answer_query(user_message: str) -> dict:
    """Call the LLM, extract code, execute it, return structured response."""
    schema = _load_schema()
    system = SYSTEM_PROMPT.format(schema=schema)

    client = _get_groq()
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        # reasoning_effort="medium",
        temperature=0.8,
        max_tokens=1024,
    )

    llm_text = response.choices[0].message.content
    code_type, code = _extract_code(llm_text)

    # Extract human-readable explanation (text outside the code block)
    explanation = re.sub(r"```.*?```", "", llm_text, flags=re.DOTALL).strip()

    execution_result = ""
    # Edge case: LLM failed to output any format
    if code_type == "none" and not explanation.strip():
        explanation = "I couldn't quite understand how to format a query for that. Could you please clarify your question and ensure it is related to Order-to-Cash data?"

    if code_type == "sql" and code:
        execution_result = _execute_sql(code)
    elif code_type == "python" and code:
        execution_result = _execute_python(code)

    # Build the final answer
    answer_parts = []
    if explanation:
        answer_parts.append(explanation)
    if execution_result:
        answer_parts.append(f"\n**Result:**\n{execution_result}")

    return {
        "answer": "\n".join(answer_parts).strip(),
        "code": code,
        "code_type": code_type,
        "raw_llm": llm_text,
    }
