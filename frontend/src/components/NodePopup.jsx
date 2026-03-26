const NODE_COLORS = {
  SalesOrder: '#4A9EFF',
  Delivery: '#00C9A7',
  BillingDoc: '#FF6B8A',
  JournalEntry: '#FFA500',
  Payment: '#22C55E',
  Customer: '#A855F7',
}

// Fields to skip in the props display
const SKIP_FIELDS = new Set(['id', 'label', 'type', 'color', 'size', 'nodeType', 'x', 'y', 'connections'])

// Human-friendly field labels
const FIELD_LABELS = {
  salesOrder: 'Sales Order',
  soldToParty: 'Sold To Party',
  creationDate: 'Creation Date',
  totalNetAmount: 'Net Amount',
  currency: 'Currency',
  deliveryDocument: 'Delivery Doc',
  shippingPoint: 'Shipping Point',
  billingDocument: 'Billing Doc',
  billingDocumentDate: 'Billing Date',
  accountingDocument: 'Accounting Doc',
  isCancelled: 'Cancelled',
  referenceDocument: 'Reference Doc',
  amount: 'Amount',
  postingDate: 'Posting Date',
  clearingDate: 'Clearing Date',
  customer: 'Customer ID',
  customerId: 'Customer ID',
}

export default function NodePopup({ node, onClose }) {
  if (!node) return null

  const displayType = node.nodeType || node.type || 'Unknown'
  const color = NODE_COLORS[displayType] || '#888888'

  // Filter props to display
  const props = Object.entries(node)
    .filter(([k, v]) => !SKIP_FIELDS.has(k) && v !== null && v !== undefined && v !== '')
    .slice(0, 10) // limit to 10 fields

  const hiddenCount = Object.keys(node).filter(
    (k) => !SKIP_FIELDS.has(k) && node[k] !== null && node[k] !== undefined && node[k] !== ''
  ).length - props.length

  return (
    <div className="node-popup">
      <div className="popup-header">
        <div className="popup-type-badge" style={{ background: color }}>
          {displayType}
        </div>
        <button className="popup-close" onClick={onClose}>×</button>
      </div>

      <div className="popup-id">{node.id}</div>

      <div className="popup-props">
        {props.map(([key, value]) => (
          <div className="popup-prop" key={key}>
            <span className="popup-prop-key">{FIELD_LABELS[key] || key}</span>
            <span className="popup-prop-value">{String(value)}</span>
          </div>
        ))}
      </div>

      <div className="popup-connections">
        🔗 Connections: <strong>{node.connections ?? 0}</strong>
      </div>

      {hiddenCount > 0 && (
        <div className="popup-footer">
          {hiddenCount} additional field{hiddenCount > 1 ? 's' : ''} hidden for readability
        </div>
      )}
    </div>
  )
}
