"""
guardrails.py — Keyword filter to reject off-topic queries before sending to LLM.
"""

import re

O2C_KEYWORDS = {
    # Core entities and common abbreviations
    "order", "orders", "sales", "invoice", "invoices", "billing", "bill", "delivery", "deliver", "deliv",
    "payment", "pay", "payments", "customer", "customers", "cust", "shipment", "ship", "goods", "material",
    "document", "doc", "docs", "accounting", "journal", "amount", "amt", "quantity", "qty", "revenue",
    
    # Financial/logistical terms
    "ar", "receivable", "clearing", "credit", "debit", "fiscal", "ledger",
    "warehouse", "transfer", "plant", "stock", "dispatch", "outstanding",
    "overdue", "dunning", "open", "closed", "cancelled", "status", "date",
    
    # Analytical / query wrappers
    "total", "count", "sum", "average", "avg", "top", "list", "show", "distinct", 
    "unique", "number", "num", "how", "many", "what", "which", "graph", "node", "edge", "o2c", "sap"
}

REJECTION_MESSAGE = (
    "I'm the O2C Graph Agent and can only answer questions about Order-to-Cash data "
    "(sales orders, deliveries, billing, payments, customers, etc.). "
    "Please ask me something related to this data."
)

def is_on_topic(message: str) -> bool:
    """Return True if the message contains at least one O2C keyword based on word tokens."""
    words = set(re.findall(r'\b\w+\b', message.lower()))
    
    # Check for direct word intersection
    if words.intersection(O2C_KEYWORDS):
        return True
        
    return False
