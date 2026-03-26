import { useEffect, useCallback, useState } from 'react'
import Graph from 'graphology'
import { SigmaContainer, useLoadGraph, useSigma } from '@react-sigma/core'
import '@react-sigma/core/lib/style.css'
import circular from 'graphology-layout/circular'
import { assign as fa2assign } from 'graphology-layout-forceatlas2'

const NODE_COLORS = {
  SalesOrder: '#4A9EFF',
  Delivery: '#00C9A7',
  BillingDoc: '#FF6B8A',
  JournalEntry: '#FFA500',
  Payment: '#22C55E',
  Customer: '#A855F7',
}

const NODE_SIZES = {
  SalesOrder: 7,
  Delivery: 6,
  BillingDoc: 8,
  JournalEntry: 5,
  Payment: 5,
  Customer: 10,
}

const LEGEND_ITEMS = [
  { type: 'Customer', label: 'Customer' },
  { type: 'SalesOrder', label: 'Sales Order' },
  { type: 'Delivery', label: 'Delivery' },
  { type: 'BillingDoc', label: 'Billing Doc' },
  { type: 'JournalEntry', label: 'Journal Entry' },
  { type: 'Payment', label: 'Payment' },
]

// Inner component to load graph into sigma context
function LoadGraph({ graphData, onNodeClick }) {
  const loadGraph = useLoadGraph()
  const sigma = useSigma()
  const [hoveredNode, setHoveredNode] = useState(null)
  const [clickedNode, setClickedNode] = useState(null)

  useEffect(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return

    const g = new Graph({ multi: false, type: 'directed' })

    graphData.nodes.forEach((node) => {
      if (!g.hasNode(node.id)) {
        // Destructure out `type` and `id` so Sigma doesn't use 'SalesOrder' as a renderer
        // eslint-disable-next-line no-unused-vars
        const { type: _type, id: _id, ...rest } = node
        g.addNode(node.id, {
          label: node.id,
          color: NODE_COLORS[node.type] || '#888888',
          size: NODE_SIZES[node.type] || 5,
          type: 'circle',          // Sigma v3 rendering program
          nodeType: node.type,     // Our custom type for popups/colors
          ...rest,
        })
      }
    })

    graphData.edges.forEach((edge) => {
      try {
        if (
          g.hasNode(edge.source) &&
          g.hasNode(edge.target) &&
          !g.hasEdge(edge.source, edge.target)
        ) {
          g.addEdge(edge.source, edge.target, {
            color: 'rgba(100, 150, 255, 0.2)',
            size: 1,
          })
        }
      } catch (_) {}
    })

    // Apply circular layout first (sets initial x,y)
    circular.assign(g)

    // Then run ForceAtlas2 if graph has nodes
    if (g.order > 0) {
      try {
        fa2assign(g, {
          iterations: 120,
          settings: {
            gravity: 1,
            scalingRatio: 5,
            strongGravityMode: false,
            barnesHutOptimize: g.order > 200,
          },
        })
      } catch (e) {
        console.warn('[GraphCanvas] ForceAtlas2 failed, using circular layout:', e)
      }
    }

    loadGraph(g)
  }, [graphData, loadGraph])

  // Node interaction reducers
  useEffect(() => {
    if (!sigma) return

    const graph = sigma.getGraph()
    const activeNode = hoveredNode || clickedNode

    if (!activeNode) {
      sigma.setSetting('nodeReducer', null)
      sigma.setSetting('edgeReducer', null)
      return
    }

    // Get 1-hop neighbors
    let neighbors = new Set()
    try {
      if (graph.hasNode(activeNode)) {
        neighbors = new Set(graph.neighbors(activeNode))
      }
    } catch (_) {}

    neighbors.add(activeNode)

    sigma.setSetting('nodeReducer', (node, data) => {
      const res = { ...data }
      if (!neighbors.has(node)) {
        res.color = '#1f252f' // dimmed
        res.label = ''
        res.zIndex = 0
      } else {
        res.zIndex = 1
        if (node === activeNode) {
          res.highlighted = true
        }
      }
      return res
    })

    sigma.setSetting('edgeReducer', (edge, data) => {
      const res = { ...data }
      try {
        if (graph.hasExtremity(edge, activeNode)) {
          res.color = '#ffffff'
          res.size = 2
          res.zIndex = 1
        } else {
          res.color = 'rgba(0,0,0,0)' // hide disconnected edges
          res.zIndex = 0
        }
      } catch (_) {}
      return res
    })
  }, [sigma, hoveredNode, clickedNode])

  // Mouse / click handlers
  useEffect(() => {
    if (!sigma) return

    const handleEnter = (e) => setHoveredNode(e.node)
    const handleLeave = () => setHoveredNode(null)

    const handleClick = (event) => {
      const nodeId = event.node
      setClickedNode(nodeId)
      const attrs = sigma.getGraph().getNodeAttributes(nodeId)
      const degree = sigma.getGraph().degree(nodeId)
      onNodeClick({ ...attrs, id: nodeId, connections: degree })
    }

    const handleStageClick = () => {
      setClickedNode(null)
      onNodeClick(null)
    }

    sigma.on('enterNode', handleEnter)
    sigma.on('leaveNode', handleLeave)
    sigma.on('clickNode', handleClick)
    sigma.on('clickStage', handleStageClick)

    return () => {
      sigma.off('enterNode', handleEnter)
      sigma.off('leaveNode', handleLeave)
      sigma.off('clickNode', handleClick)
      sigma.off('clickStage', handleStageClick)
    }
  }, [sigma, onNodeClick])

  return null
}

export default function GraphCanvas({ onNodeSelect }) {
  const [graphData, setGraphData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/graph')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => {
        setGraphData(data)
        setLoading(false)
      })
      .catch((e) => {
        setError(e.message)
        setLoading(false)
      })
  }, [])

  const handleNodeClick = useCallback(
    (nodeData) => {
      onNodeSelect(nodeData)
    },
    [onNodeSelect]
  )

  const panelStyle = {
    position: 'relative',
    width: '100%',
    height: '100%',
    flex: 1,
    background: '#0d1117',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  }

  if (loading) {
    return (
      <div style={{ ...panelStyle, alignItems: 'center', justifyContent: 'center', gap: 16 }}>
        <div className="spinner" />
        <span style={{ color: 'var(--text-secondary)' }}>Loading O2C graph data…</span>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ ...panelStyle, alignItems: 'center', justifyContent: 'center', gap: 8, padding: 20, textAlign: 'center' }}>
        <span style={{ fontSize: 24 }}>⚠️</span>
        <strong style={{ color: 'var(--accent-pink)' }}>Could not load graph</strong>
        <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{error}</span>
        <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
          Make sure the backend is running at localhost:8000
        </span>
      </div>
    )
  }

  const nodeCount = graphData?.nodes?.length ?? 0
  const edgeCount = graphData?.edges?.length ?? 0

  return (
    <div style={panelStyle}>
      {/* Stats */}
      <div className="graph-stats">
        <div className="stat-badge"><span>{nodeCount}</span> nodes</div>
        <div className="stat-badge"><span>{edgeCount}</span> edges</div>
      </div>

      {/* Sigma container — explicit 100% h/w, allowInvalidContainer */}
      <SigmaContainer
        style={{ height: '100%', width: '100%', background: '#0d1117' }}
        settings={{
          allowInvalidContainer: true,
          renderEdgeLabels: false,
          defaultEdgeColor: 'rgba(100, 150, 255, 0.2)',
          defaultNodeColor: '#4A9EFF',
          minCameraRatio: 0.05,
          maxCameraRatio: 10,
          enableEdgeEvents: false,
          labelColor: { color: '#8b949e' },
          labelSize: 10,
          labelWeight: '500',
          labelFont: 'Inter, sans-serif',
        }}
      >
        <LoadGraph graphData={graphData} onNodeClick={handleNodeClick} />
      </SigmaContainer>

      {/* Legend */}
      <div className="graph-legend">
        <div className="legend-title">Node Types</div>
        {LEGEND_ITEMS.map((item) => (
          <div className="legend-item" key={item.type}>
            <div className="legend-dot" style={{ background: NODE_COLORS[item.type] }} />
            {item.label}
          </div>
        ))}
      </div>
    </div>
  )
}
