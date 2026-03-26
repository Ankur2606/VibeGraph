# SAP Order-to-Cash Schema Reference

## Tables Available in DuckDB

### sales_order_headers
Primary key: `salesOrder`
Columns: salesOrder, soldToParty, creationDate, totalNetAmount, transactionCurrency, salesOrganization, distributionChannel, division, salesOrderType, requestedDeliveryDate, shippingCondition, incotermsClassification, customerPurchaseOrderType, customerPurchaseOrderDate, overallSDProcessStatus, totalCreditCheckStatus

### sales_order_items
Foreign key: `salesOrder` → sales_order_headers.salesOrder
Columns: salesOrder, salesOrderItem, material, salesOrderItemCategory, requestedQuantity, requestedQuantityUnit, netAmount, transactionCurrency, storageLocation, plant, shippingPoint, itemBillingBlockReason, sdDocumentRejectionStatus

### outbound_delivery_headers
Primary key: `deliveryDocument`
Columns: deliveryDocument, creationDate, shippingPoint, shipToParty, plannedGoodsIssueDate, actualGoodsMovementDate, deliveryDocumentType, overallDeliveryStatus, overallGoodsMovementStatus, overallPickingStatus, overallWarehouseActivityStatus

### outbound_delivery_items
Foreign keys: `deliveryDocument` → outbound_delivery_headers.deliveryDocument, `referenceSdDocument` → sales_order_headers.salesOrder
Columns: deliveryDocument, deliveryDocumentItem, referenceSdDocument, referenceSdDocumentItem, actualDeliveryQuantity, deliveryQuantityUnit, plant, storageLocation, batch, itemBillingBlockReason, lastChangeDate

### billing_document_headers
Primary key: `billingDocument`
Foreign key: `accountingDocument` → journal_entry_items_accounts_receivable.accountingDocument
Columns: billingDocument, billingDocumentDate, accountingDocument, soldToParty, billingDocumentIsCancelled, billingDocumentType, sdDocumentCategory, transactionCurrency, totalNetAmount, totalTaxAmount

### billing_document_items
Foreign keys: `billingDocument` → billing_document_headers.billingDocument, `referenceSdDocument` → outbound_delivery_headers.deliveryDocument
Columns: billingDocument, billingDocumentItem, material, billingQuantity, billingQuantityUnit, netAmount, transactionCurrency, referenceSdDocument, referenceSdDocumentItem

### journal_entry_items_accounts_receivable
Foreign keys: `accountingDocument` → billing_document_headers.accountingDocument, `referenceDocument` = billingDocument
Columns: companyCode, fiscalYear, accountingDocument, glAccount, referenceDocument, costCenter, profitCenter, transactionCurrency, amountInTransactionCurrency, companyCodeCurrency, amountInCompanyCodeCurrency, postingDate, documentDate, accountingDocumentType, accountingDocumentItem, assignmentReference, lastChangeDateTime, customer, financialAccountType, clearingDate, clearingAccountingDocument, clearingDocFiscalYear

### payments_accounts_receivable
Foreign key: `accountingDocument` matches journal_entry items
Columns: companyCode, fiscalYear, accountingDocument, accountingDocumentItem, clearingDate, clearingAccountingDocument, clearingDocFiscalYear, amountInTransactionCurrency, transactionCurrency, amountInCompanyCodeCurrency, companyCodeCurrency, customer, invoiceReference, invoiceReferenceFiscalYear, salesDocument, salesDocumentItem, postingDate, documentDate, assignmentReference, glAccount, financialAccountType, profitCenter, costCenter

## Join Chain (O2C Flow)
```
SalesOrder → Delivery:
  outbound_delivery_items.referenceSdDocument = sales_order_headers.salesOrder

Delivery → BillingDoc:
  billing_document_items.referenceSdDocument = outbound_delivery_headers.deliveryDocument

BillingDoc → JournalEntry:
  billing_document_headers.accountingDocument = journal_entry_items_accounts_receivable.accountingDocument

BillingDoc → Payment:
  billing_document_headers.accountingDocument = payments_accounts_receivable.accountingDocument
```

## Example Queries

**How many sales orders?**
```sql
SELECT COUNT(DISTINCT salesOrder) FROM sales_order_headers
```

**Total billed amount by customer?**
```sql
SELECT soldToParty, SUM(CAST(totalNetAmount AS DOUBLE)) as total
FROM billing_document_headers
WHERE billingDocumentIsCancelled = 'false' OR billingDocumentIsCancelled IS NULL
GROUP BY soldToParty ORDER BY total DESC
```

**Orders with no delivery?**
```sql
SELECT soh.salesOrder FROM sales_order_headers soh
LEFT JOIN outbound_delivery_items odi ON odi.referenceSdDocument = soh.salesOrder
WHERE odi.deliveryDocument IS NULL
```
