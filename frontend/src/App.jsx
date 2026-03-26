import { useState, useCallback } from 'react'
import GraphCanvas from './components/GraphCanvas'
import NodePopup from './components/NodePopup'
import ChatSidebar from './components/ChatSidebar'

export default function App() {
  const [selectedNode, setSelectedNode] = useState(null)
  const [isMinimized, setIsMinimized] = useState(false)

  const handleNodeSelect = useCallback((nodeData) => {
    setSelectedNode(nodeData)
  }, [])

  return (
    <div className="app-container">
      {/* Top Bar */}
      <div className="top-bar">
        <div className="breadcrumb">
          <span className="breadcrumb-item">Mapping</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-item active">Order to Cash</span>
          <span className="breadcrumb-sep" style={{marginLeft: '12px', marginRight: '8px', color: '#e5e7eb'}}>|</span>
          <span style={{ fontSize: '11px', color: '#9ca3af', fontWeight: 'normal' }}>
             Note: Backend is deployed on Render (free tier). Initial load may take ~50s to wake up.
          </span>
        </div>
        <div className="top-bar-actions">
          <button className="btn-ghost" onClick={() => setSelectedNode(null)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Hide Granular Overlay
          </button>
          <button className="btn-ghost" onClick={() => setIsMinimized(!isMinimized)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {isMinimized ? (
                <>
                  <polyline points="15 3 21 3 21 9" />
                  <polyline points="9 21 3 21 3 15" />
                  <line x1="21" y1="3" x2="14" y2="10" />
                  <line x1="3" y1="21" x2="10" y2="14" />
                </>
              ) : (
                <>
                  <polyline points="4 14 10 14 10 20" />
                  <polyline points="20 10 14 10 14 4" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                  <line x1="3" y1="21" x2="14" y2="10" />
                </>
              )}
            </svg>
            {isMinimized ? "Expand Chat" : "Minimize"}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-area">
        {/* Graph Panel */}
        <div style={{ position: 'relative', flex: isMinimized ? '1' : '0 0 65%', height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column', transition: 'flex 0.3s ease' }}>
          <GraphCanvas onNodeSelect={handleNodeSelect} />
          {selectedNode && (
            <NodePopup node={selectedNode} onClose={() => setSelectedNode(null)} />
          )}
        </div>

        {/* Chat Sidebar */}
        {!isMinimized && <ChatSidebar />}
      </div>
    </div>
  )
}
