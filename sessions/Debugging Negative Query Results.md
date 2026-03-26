# Debugging Negative Query Results

- **Cascade ID**: `c29376bb-3624-432c-9318-7060f86cb30f`
- **Steps**: 27
- **Status**: CASCADE_RUN_STATUS_IDLE
- **Created**: 2026-03-26T06:29:04.139161900Z
- **Last Modified**: 2026-03-26T06:29:47.568991300Z
- **Last User Input**: 2026-03-26T06:29:04.139161900Z
- **Workspace**: file:///c:/Users/bhavy/Desktop/Kaam/Job%20Assessments/DodgeAI/order-to-cash
- **Exported**: 2026-03-26 14:13:12

---

## 🧑 User
why is this in negative? ``` [3/6] Query: Calculate the average amount made in INR payments that were cleared after April 2025.
  Answer: **Explanation:**  
The query selects all payment records whose currency is Indian Rupees (INR) and whose `clearingDate` is later than April 30 2025. It converts the payment amount (`amountInTransactionCurrency`) to a numeric type and then computes the average of those amounts, returning it as `avg_amount_inr`.

**Result:**
avg_amount_inr
---
-8.120488408686859e-15
  Code (sql):
    SELECT 
        AVG(CAST(amountInTransactionCurrency AS DOUBLE)) AS avg_amount_inr
    FROM 
        payments_accounts_receivable
    WHERE 
        transactionCurrency = 'INR'
        AND clearingDate IS NOT NULL
        AND CAST(clearingDate AS DATE) > DATE '2025-04-30';
  Speed:  2.98s
-------------------```

### 🔧 Tool: `list_dir`
`[List Directory]`

### 🔧 Tool: `list_dir`
`[List Directory]`

### 🔧 Tool: `list_dir`
`[List Directory]`

### 🔧 Tool: `view_file`
`file:///c:/Users/bhavy/Desktop/Kaam/Job%20Assessments/DodgeAI/order-to-cash/backend/query_engine.py`

### 🔧 Tool: `view_file`
`file:///c:/Users/bhavy/Desktop/Kaam/Job%20Assessments/DodgeAI/order-to-cash/backend/data_loader.py`

### 🔧 Tool: `code_edit`
[Code Edit] file:///c:/Users/bhavy/Desktop/Kaam/Job%20Assessments/DodgeAI/order-to-cash/inspect_payments.py
Create a script to inspect the data for the user's query.

### 🔧 Tool: `run_command`
```bash
python inspect_payments.py
```

## 🤖 Assistant
The negative result you're seeing—specifically **`-8.120488408686859e-15`**—is a classic example of a **floating-point precision artifact** combined with a perfectly balanced dataset.

Here is the breakdown of why this is happening:

### 1. The Underlying Data is Perfectly Balanced
I inspected the data in the `payments_accounts_receivable` table for INR payments after April 2025. There are **14 records** that appear in pairs of exactly matching positive and negative values:

| Amount | Clearing Date |
| :--- | :--- |
| **591.18** | 2025-05-16 |
| **-591.18** | 2025-05-16 |
| **1355.46** | 2025-05-16 |
| **-1355.46** | 2025-05-16 |
| ... and so on | ... |

Mathematically, the sum of these numbers is **exactly 0**. Therefore, the average should also be exactly 0.

### 2. Floating-Point Precision (`DOUBLE`)
The query uses `CAST(amountInTransactionCurrency AS DOUBLE)`. 
Computers represent `DOUBLE` (64-bit floating point) numbers using binary fractions. Many decimal numbers (like `0.18`) cannot be represented exactly in binary. When the database sums these approximations, the tiny "errors" at the 15th or 16th decimal place don't always cancel out perfectly. 

The result `-8.12e-15` is scientific notation for:  
**`-0.00000000000000812...`**

This is effectively **0**, but the "leftover" noise from binary arithmetic makes it appear as a tiny negative number.

### 3. How to fix it
For financial data where precision is important, you should use the `DECIMAL` type instead of `DOUBLE`. `DECIMAL` uses "fixed-point" math which handles base-10 decimals exactly.

If you change the query to use **`DECIMAL(18,2)`**, the result will be a clean `0.00`:

```sql
SELECT 
    AVG(CAST(amountInTransactionCurrency AS DECIMAL(18,2))) AS avg_amount_inr
FROM 
    payments_accounts_receivable
WHERE 
    transactionCurrency = 'INR'
    AND clearingDate IS NOT NULL
    AND CAST(clearingDate AS DATE) > DATE '2025-04-30';
```

### Summary
*   **The "Why":** The data contains offsetting entries (payments and reversals) that sum to zero.
*   **The Negative Sign:** It's just a tiny bit of "mathematical noise" from using floating-point types (`DOUBLE`) for currency.
