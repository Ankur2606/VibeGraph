"""
graph_builder.py — Builds a NetworkX graph from DuckDB and returns JSON for Sigma.js.
Capped at 800 nodes for browser performance.
"""
from data_loader import get_con

MAX_NODES = 800

NODE_COLORS = {
    "SalesOrder":   "#4A9EFF",
    "Delivery":     "#00C9A7",
    "BillingDoc":   "#FF6B8A",
    "JournalEntry": "#FFA500",
    "Payment":      "#22C55E",
    "Customer":     "#A855F7",
}

NODE_SIZES = {
    "SalesOrder":   8,
    "Delivery":     7,
    "BillingDoc":   9,
    "JournalEntry": 6,
    "Payment":      6,
    "Customer":     10,
}


def build_graph() -> dict:
    con = get_con()
    nodes = {}
    edges = []

    def add_node(node_id: str, node_type: str, props: dict):
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "label": node_id,
                "type": node_type,
                "color": NODE_COLORS.get(node_type, "#888888"),
                "size": NODE_SIZES.get(node_type, 6),
                **props,
            }

    # ── 1. Sales Orders ──────────────────────────────────────────────────────
    so_rows = con.execute(
        "SELECT salesOrder, soldToParty, creationDate, totalNetAmount, transactionCurrency "
        "FROM sales_order_headers LIMIT 200"
    ).fetchall()
    so_cols = ["salesOrder", "soldToParty", "creationDate", "totalNetAmount", "transactionCurrency"]

    for row in so_rows:
        r = dict(zip(so_cols, row))
        so_id = f"SO_{r['salesOrder']}"
        add_node(so_id, "SalesOrder", {
            "salesOrder": r["salesOrder"],
            "soldToParty": r["soldToParty"],
            "creationDate": str(r["creationDate"]) if r["creationDate"] else None,
            "totalNetAmount": r["totalNetAmount"],
            "currency": r["transactionCurrency"],
        })
        # Add customer node
        if r["soldToParty"]:
            cust_id = f"CUST_{r['soldToParty']}"
            add_node(cust_id, "Customer", {"customerId": r["soldToParty"]})
            edges.append({"source": cust_id, "target": so_id, "type": "PLACED_ORDER"})

    # ── 2. Deliveries (linked to Sales Orders) ──────────────────────────────
    del_rows = con.execute(
        "SELECT DISTINCT odi.deliveryDocument, odi.referenceSdDocument, "
        "odh.creationDate, odh.shippingPoint "
        "FROM outbound_delivery_items odi "
        "LEFT JOIN outbound_delivery_headers odh ON odh.deliveryDocument = odi.deliveryDocument "
        "WHERE odi.referenceSdDocument IS NOT NULL LIMIT 200"
    ).fetchall()
    del_cols = ["deliveryDocument", "referenceSdDocument", "creationDate", "shippingPoint"]

    for row in del_rows:
        r = dict(zip(del_cols, row))
        del_id = f"DEL_{r['deliveryDocument']}"
        add_node(del_id, "Delivery", {
            "deliveryDocument": r["deliveryDocument"],
            "creationDate": str(r["creationDate"]) if r["creationDate"] else None,
            "shippingPoint": r["shippingPoint"],
        })
        so_id = f"SO_{r['referenceSdDocument']}"
        if so_id in nodes:
            edges.append({"source": so_id, "target": del_id, "type": "HAS_DELIVERY"})

    # ── 3. Billing Documents (linked to Deliveries) ──────────────────────────
    bill_rows = con.execute(
        "SELECT DISTINCT bdi.billingDocument, bdi.referenceSdDocument, "
        "bdh.billingDocumentDate, bdh.accountingDocument, bdh.soldToParty, "
        "bdh.billingDocumentIsCancelled, bdh.totalNetAmount "
        "FROM billing_document_items bdi "
        "LEFT JOIN billing_document_headers bdh ON bdh.billingDocument = bdi.billingDocument "
        "WHERE bdi.referenceSdDocument IS NOT NULL LIMIT 200"
    ).fetchall()
    bill_cols = ["billingDocument", "referenceSdDocument", "billingDocumentDate",
                 "accountingDocument", "soldToParty", "billingDocumentIsCancelled", "totalNetAmount"]

    for row in bill_rows:
        r = dict(zip(bill_cols, row))
        bill_id = f"BILL_{r['billingDocument']}"
        add_node(bill_id, "BillingDoc", {
            "billingDocument": r["billingDocument"],
            "billingDocumentDate": str(r["billingDocumentDate"]) if r["billingDocumentDate"] else None,
            "accountingDocument": r["accountingDocument"],
            "soldToParty": r["soldToParty"],
            "isCancelled": str(r["billingDocumentIsCancelled"]),
            "totalNetAmount": r["totalNetAmount"],
        })
        del_id = f"DEL_{r['referenceSdDocument']}"
        if del_id in nodes:
            edges.append({"source": del_id, "target": bill_id, "type": "HAS_BILLING"})

    # ── 4. Journal Entries (linked to Billing via accountingDocument) ─────────
    je_rows = con.execute(
        "SELECT DISTINCT j.accountingDocument, j.referenceDocument, "
        "j.amountInTransactionCurrency, j.transactionCurrency, j.postingDate "
        "FROM journal_entry_items_accounts_receivable j LIMIT 100"
    ).fetchall()
    je_cols = ["accountingDocument", "referenceDocument", "amountInTransactionCurrency",
               "transactionCurrency", "postingDate"]

    # Build a lookup: accountingDocument → billingDocument nodes
    acc_to_bill = {}
    for nid, ndata in nodes.items():
        if ndata["type"] == "BillingDoc" and ndata.get("accountingDocument"):
            acc_to_bill[ndata["accountingDocument"]] = nid

    for row in je_rows:
        r = dict(zip(je_cols, row))
        je_id = f"JE_{r['accountingDocument']}"
        add_node(je_id, "JournalEntry", {
            "accountingDocument": r["accountingDocument"],
            "referenceDocument": r["referenceDocument"],
            "amount": r["amountInTransactionCurrency"],
            "currency": r["transactionCurrency"],
            "postingDate": str(r["postingDate"]) if r["postingDate"] else None,
        })
        bill_node = acc_to_bill.get(r["accountingDocument"])
        if bill_node:
            edges.append({"source": bill_node, "target": je_id, "type": "HAS_JOURNAL"})

    # ── 5. Payments (linked to Journal Entries via accountingDocument) ────────
    pay_rows = con.execute(
        "SELECT DISTINCT accountingDocument, amountInTransactionCurrency, "
        "transactionCurrency, customer, clearingDate "
        "FROM payments_accounts_receivable "
        "WHERE CAST(amountInTransactionCurrency AS DOUBLE) > 0 LIMIT 100"
    ).fetchall()
    pay_cols = ["accountingDocument", "amountInTransactionCurrency",
                "transactionCurrency", "customer", "clearingDate"]

    for row in pay_rows:
        r = dict(zip(pay_cols, row))
        pay_id = f"PAY_{r['accountingDocument']}"
        add_node(pay_id, "Payment", {
            "accountingDocument": r["accountingDocument"],
            "amount": r["amountInTransactionCurrency"],
            "currency": r["transactionCurrency"],
            "customerId": r["customer"],
            "clearingDate": str(r["clearingDate"]) if r["clearingDate"] else None,
        })
        
        # 1. Link to Journal Entry (if exists)
        je_node = f"JE_{r['accountingDocument']}"
        if je_node in nodes:
            edges.append({"source": je_node, "target": pay_id, "type": "CLEARED_BY"})
            
        # 2. Link to Customer
        if r["customer"]:
            cust_id = f"CUST_{r['customer']}"
            if cust_id not in nodes:
                add_node(cust_id, "Customer", {"customerId": r["customer"]})
            edges.append({"source": cust_id, "target": pay_id, "type": "MADE_PAYMENT"})

    # ── Enforce node cap ─────────────────────────────────────────────────────
    node_list = list(nodes.values())
    if len(node_list) > MAX_NODES:
        # Priority: Customer, SalesOrder, BillingDoc first
        priority_order = ["Customer", "SalesOrder", "BillingDoc", "Delivery", "JournalEntry", "Payment"]
        node_list.sort(key=lambda n: priority_order.index(n["type"]) if n["type"] in priority_order else 99)
        node_list = node_list[:MAX_NODES]
        kept_ids = {n["id"] for n in node_list}
        edges = [e for e in edges if e["source"] in kept_ids and e["target"] in kept_ids]

    # Deduplicate edges
    seen_edges = set()
    deduped_edges = []
    for e in edges:
        key = (e["source"], e["target"], e["type"])
        if key not in seen_edges:
            seen_edges.add(key)
            deduped_edges.append(e)

    return {"nodes": node_list, "edges": deduped_edges}
