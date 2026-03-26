"""
guardrails.py — Keyword filter to reject off-topic queries before sending to LLM.
"""

O2C_KEYWORDS = {
    "order", "sales", "invoice", "billing", "bill", "delivery", "deliver",
    "payment", "pay", "customer", "shipment", "ship", "goods", "material",
    "document", "accounting", "journal", "amount", "quantity", "revenue",
    "ar", "receivable", "clearing", "credit", "debit", "fiscal", "ledger",
    "warehouse", "transfer", "plant", "stock", "dispatch", "outstanding",
    "overdue", "dunning", "open", "closed", "cancelled", "status", "date",
    "total", "count", "sum", "average", "top", "how many", "list", "show"
}

REJECTION_MESSAGE = (
    "I'm the O2C Graph Agent and can only answer questions about Order-to-Cash data "
    "(sales orders, deliveries, billing, payments, customers, etc.). "
    "Please ask me something related to this data."
)


def is_on_topic(message: str) -> bool:
    """Return True if the message contains at least one O2C keyword."""
    lower = message.lower()
    return any(kw in lower for kw in O2C_KEYWORDS)
