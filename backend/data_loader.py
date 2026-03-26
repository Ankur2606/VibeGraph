"""
data_loader.py — Loads all SAP O2C JSONL tables into an in-memory DuckDB connection.
"""
import os
import glob
import duckdb
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.getenv("DATA_DIR", "../sap-o2c-data")
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), DATA_DIR))

# All 19 table directories
TABLES = [
    "sales_order_headers",
    "sales_order_items",
    "outbound_delivery_headers",
    "outbound_delivery_items",
    "billing_document_headers",
    "billing_document_items",
    "journal_entry_items_accounts_receivable",
    "payments_accounts_receivable",
    "customer_master",
    "material_master",
    "plant_master",
    "sales_organization",
    "distribution_channel",
    "division",
    "shipping_point",
    "storage_location",
    "goods_issue",
    "transfer_order",
    "warehouse_transfer",
]

_con = None


def get_con() -> duckdb.DuckDBPyConnection:
    """Return the singleton DuckDB in-memory connection, loading data on first call."""
    global _con
    if _con is not None:
        return _con

    _con = duckdb.connect(database=":memory:")

    for table in TABLES:
        table_dir = os.path.join(DATA_DIR, table)
        if not os.path.isdir(table_dir):
            continue  # silently skip tables that don't exist in this dataset
        pattern = os.path.join(table_dir, "*.jsonl").replace("\\", "/")
        files = glob.glob(pattern)
        if not files:
            continue
        # Use DuckDB's read_json_auto to load all part files at once
        files_sql = ", ".join(f"'{f.replace(chr(92), '/')}'" for f in files)
        _con.execute(
            f"CREATE TABLE IF NOT EXISTS {table} AS "
            f"SELECT * FROM read_json_auto([{files_sql}], ignore_errors=true)"
        )
        print(f"[data_loader] Loaded table: {table} ({len(files)} files)")

    print("[data_loader] All tables loaded into DuckDB.")
    return _con
