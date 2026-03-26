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


SYSTEM_PROMPT = """\
## ROLE
You are an expert SAP Order-to-Cash (O2C) SQL analyst with access to an in-memory DuckDB database.

## SCHEMA
{schema}

---

## TASK
Given a user question about O2C data, generate a DuckDB SQL query that answers it, then write a brief structured response.

---

## CONSTRAINTS (ALL MANDATORY)
1. **Fenced SQL only**: ALWAYS wrap your SQL in triple-backtick fenced blocks: ```sql ... ``` — NEVER emit raw SQL or SQL comments outside of a code block.
2. **No fabricated data**: Only query tables/columns that exist in the schema above.
3. **Numeric casting**: All numeric columns are VARCHAR. ALWAYS cast inside aggregates: `SUM(CAST(col AS DOUBLE))`, never `SUM(col)`.
4. **JSON/VARCHAR comparisons**: Use `CAST(col AS VARCHAR) = 'literal'` to avoid "Malformed JSON" errors.
5. **LIMIT**: Add `LIMIT 50` to all list/row queries.
6. **Unknown IDs**: If the user gives a bare ID (e.g. `91150147`) with no document type context, check ALL O2C key columns with OR logic: `WHERE CAST(soh.salesOrder AS VARCHAR) = 'x' OR CAST(odh.deliveryDocument AS VARCHAR) = 'x' OR CAST(bdh.billingDocument AS VARCHAR) = 'x'`.
7. **Mixed queries**: For queries mixing O2C and non-O2C topics, answer the O2C parts fully and politely decline the non-O2C parts in text.
8. **Python fallback**: If graph traversal is needed, use a ```python ``` block with `con` (DuckDB connection) and set `result`.
9. **Word limit**: Summary and Assumptions section must be ≤ 120 words.

---

## OUTPUT FORMAT (STRICT — follow this exact structure every time)

```sql
-- your DuckDB query here
```

**Summary and Assumptions**
- **Intent**: [One sentence: what the user wants]
- **Assumptions**: [Bullet list of structural choices you made, max 4 bullets]

**Result:**
[Leave blank — the system will populate this automatically]

---

## OUTPUT EXAMPLE

Input: `91150147 - Find the journal entry number linked to this?`

```sql
SELECT DISTINCT CAST(je.accountingDocument AS VARCHAR) AS journalEntryNumber
FROM journal_entry_items_accounts_receivable AS je
JOIN billing_document_headers AS bdh
  ON CAST(bdh.accountingDocument AS VARCHAR) = CAST(je.accountingDocument AS VARCHAR)
WHERE CAST(bdh.billingDocument AS VARCHAR) = '91150147'
   OR CAST(bdh.salesDocument AS VARCHAR) = '91150147'
LIMIT 50;
```

**Summary and Assumptions**
- **Intent**: Retrieve the journal entry (accountingDocument) linked to ID 91150147.
- **Assumptions**:
  - ID could be a Sales Order, Delivery, or Billing Document — all checked with OR.
  - All key columns cast to VARCHAR for safe string comparison.
  - Journal entry linked via billing_document_headers.accountingDocument.
"""
def _extract_code(text: str) -> tuple[str, str, bool]:
    """Return (code_type, code, was_fenced). was_fenced=True means the LLM properly wrapped in backticks."""
    sql_match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if sql_match:
        return "sql", sql_match.group(1).strip(), True
    py_match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if py_match:
        return "python", py_match.group(1).strip(), True

    # Fallback: aggressively scrape raw SQL if LLM forgot fences
    raw_sql_match = re.search(r"(?i)\b(SELECT\s+|WITH\s+[a-z0-9_]+\s+AS\s*\().*?;", text, re.DOTALL)
    if raw_sql_match:
        return "sql", raw_sql_match.group(0).strip(), False  # NOT fenced!

    return "none", "", False


def _execute_sql(sql: str) -> tuple[str, bool]:
    try:
        con = get_con()
        rows = con.execute(sql).fetchall()
        cols = [d[0] for d in con.execute(sql).description]
        if not rows:
            return "No matching records were found in the database. Please try adjusting your search terms or filters.", True
        # Format as markdown table
        header = " | ".join(cols)
        sep = " | ".join(["---"] * len(cols))
        body = "\n".join(" | ".join(str(v) for v in row) for row in rows[:50])
        return f"{header}\n{sep}\n{body}", True
    except Exception as e:
        return "I encountered a technical issue while generating the query. Could you please clarify your request or provide more specific terms?", False


def _execute_python(code: str) -> tuple[str, bool]:
    try:
        con = get_con()
        local_ns = {"con": con, "result": None}
        exec(code, {}, local_ns)  # noqa: S102
        result = local_ns.get("result")
        return str(result) if result is not None else "Executed successfully (no result variable set).", True
    except Exception:
        return "I encountered a programmatic error while attempting to traverse the graph. Please rephrase or try a different approach.", False


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
        reasoning_effort="medium",
        temperature=1,
        max_tokens=1024,
    )

    llm_text = response.choices[0].message.content
    code_type, code, was_fenced = _extract_code(llm_text)

    # Extract human-readable explanation (text outside the code block)
    if code_type != "none" and code:
        if was_fenced:
            # Cleanly strip the fenced block
            explanation = re.sub(r"```(?:sql|python).*?```", "", llm_text, flags=re.DOTALL).strip()
        else:
            # Unfenced: strip the raw SQL string so it doesn't bleed into the chat bubble
            explanation = llm_text.replace(code, "").strip()
    else:
        explanation = llm_text.strip()

    # Nuclear sweep: strip raw SQL content that may have bled into explanation
    # Step 1: Remove C-style /* ... */ blocks (with DOTALL to handle multiline)
    explanation = re.sub(r"/\*.*?\*/", "", explanation, flags=re.DOTALL)
    # Step 2: Remove lines that start with primary SQL keywords (not short words like AS/ON to avoid stripping English)
    SQL_KEYWORD_PATTERN = re.compile(
        r"^\s*(SELECT|WITH\s+\w|FROM\s+\w|JOIN\s+\w|LEFT\s+JOIN|RIGHT\s+JOIN|INNER\s+JOIN|"
        r"WHERE\s|GROUP\s+BY|ORDER\s+BY|UNION|HAVING|LIMIT\s|CAST\s*\(|"
        r"--[^\n]*)[^\n]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    cleaned = SQL_KEYWORD_PATTERN.sub("", explanation)

    # Collapse excess blank lines and strip
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

    if cleaned:
        explanation = cleaned
    # else: LLM gave ONLY raw SQL (no summary text) → fall through to edge-case handler below

    execution_result = ""
    success = True
    # Edge case: LLM failed to output any conversational text at all (or everything was SQL)
    if not explanation.strip():
        explanation = "I couldn't quite understand how to format a query for that. Could you please clarify your question and ensure it is related to Order-to-Cash data?"

    if code_type == "sql" and code:
        execution_result, success = _execute_sql(code)
    elif code_type == "python" and code:
        execution_result, success = _execute_python(code)

    if not success:
        # Wipe the LLM's explanation and code entirely so the UI only shows the custom error
        explanation = f"> ⚠️ **Query Error:** {execution_result}"
        execution_result = ""
        code = ""

    # Strip any LLM-generated **Result:** placeholder to avoid double Result keys in the UI
    explanation = re.sub(r"\*{0,2}Result:{0,1}\*{0,2}\s*(\[Leave blank[^\]]*\])?", "", explanation, flags=re.IGNORECASE).strip()
    # Collapse excess blank lines left by stripping
    explanation = re.sub(r"\n{3,}", "\n\n", explanation).strip()

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
