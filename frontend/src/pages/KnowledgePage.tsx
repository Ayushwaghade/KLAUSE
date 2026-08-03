import React, { useEffect, useState } from 'react';
import { Search, BrainCircuit, History, FileUp, Database, FolderOpen, RefreshCw } from 'lucide-react';
import { useStore } from '../store/useStore';

interface MemoryItem {
  id: string;
  timestamp: string;
  type: string;
  content: string;
  relevance?: number;
}

interface ObsidianStatus {
  vault_path: string;
  last_sync: string;
  total_notes: number;
}

const API_BASE = 'http://127.0.0.1:8000';

export const KnowledgePage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<MemoryItem[]>([]);
  const [timeline, setTimeline] = useState<MemoryItem[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  // Obsidian State
  const [vaultPath, setVaultPath] = useState('');
  const [obsidianStatus, setObsidianStatus] = useState<ObsidianStatus | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isConfiguring, setIsConfiguring] = useState(false);

  const token = useStore(state => state.token);
  const addToast = useStore(state => state.addToast);

  const getHeaders = () => {
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  };

  // Fetch initial data
  useEffect(() => {
    fetchTimeline();
    fetchObsidianStatus();
  }, [token]);

  const fetchTimeline = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/knowledge/timeline`, { headers: getHeaders() });
      if (res.ok) {
        const data = await res.json();
        setTimeline(data);
      }
    } catch (err) {
      console.error("Failed to fetch knowledge timeline:", err);
    }
  };

  const fetchObsidianStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/knowledge/obsidian/status`, { headers: getHeaders() });
      if (res.ok) {
        const data: ObsidianStatus = await res.json();
        setObsidianStatus(data);
        if (data.vault_path) {
          setVaultPath(data.vault_path);
        }
      }
    } catch (err) {
      console.error("Failed to fetch obsidian status:", err);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);

    try {
      const res = await fetch(
        `${API_BASE}/api/knowledge/search?query=${encodeURIComponent(searchQuery)}`, 
        { headers: getHeaders() }
      );
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      } else {
        addToast("Semantic search query failed", "warning");
      }
    } catch (err) {
      console.error("Search error:", err);
      addToast("Failed to connect to search API", "warning");
    } finally {
      setIsSearching(false);
    }
  };

  const handleSaveVaultPath = async () => {
    if (!vaultPath.trim()) {
      addToast("Please enter a valid vault path", "info");
      return;
    }
    setIsConfiguring(true);
    try {
      const res = await fetch(`${API_BASE}/api/knowledge/obsidian/config`, {
        method: 'POST',
        headers: getHeaders(),
        body: JSON.stringify({ vault_path: vaultPath.trim() })
      });
      if (res.ok) {
        addToast("Obsidian vault path updated & synced!", "success");
        fetchObsidianStatus();
        fetchTimeline();
      } else {
        const errData = await res.json();
        addToast(errData.detail || "Failed to configure vault path", "warning");
      }
    } catch (err) {
      console.error("Configure vault path error:", err);
      addToast("Failed to save configuration", "warning");
    } finally {
      setIsConfiguring(false);
    }
  };

  const handleSyncVault = async () => {
    setIsSyncing(true);
    try {
      const res = await fetch(`${API_BASE}/api/knowledge/obsidian/sync`, {
        method: 'POST',
        headers: getHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        addToast(`Sync complete! Indexed ${data.total_notes} notes.`, "success");
        fetchObsidianStatus();
        fetchTimeline();
      } else {
        const errData = await res.json();
        addToast(errData.detail || "Synchronization failed", "warning");
      }
    } catch (err) {
      console.error("Sync error:", err);
      addToast("Failed to synchronize vault", "warning");
    } finally {
      setIsSyncing(false);
    }
  };

  const getIcon = (type: string) => {
    if (type === 'git_commit') return <Database size={14} color="var(--accent-cyan)" />;
    if (type === 'knowledge_ingest') return <FileUp size={14} color="var(--accent-purple)" />;
    if (type === 'obsidian') return <FolderOpen size={14} color="var(--accent-gold)" />;
    return <BrainCircuit size={14} color="var(--accent-gold)" />;
  };

  return (
    <div style={containerStyle} className="animate-slide-in">
      <h2 style={{ margin: '0 0 16px 0', fontSize: '22px' }}>Knowledge Base & Memory</h2>

      <div style={splitLayout}>
        {/* Left Column: Semantic Search explorer */}
        <div style={panelStyle} className="glass-panel">
          <div style={sectionHeader}>
            <BrainCircuit size={18} color="var(--accent-cyan)" />
            <h3 style={sectionTitle}>Vector Semantic Search</h3>
          </div>

          <form onSubmit={handleSearch} style={searchBar}>
            <Search size={16} color="var(--text-secondary)" style={{ marginLeft: '12px' }} />
            <input 
              type="text" 
              placeholder="Query your second brain & documentation..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={searchInput}
            />
            <button type="submit" style={searchBtn} disabled={isSearching}>
              {isSearching ? 'Querying...' : 'Query'}
            </button>
          </form>

          {/* Results list */}
          <div style={listScroll} className="fade-scroll-container">
            {isSearching ? (
              <div style={loadingText}>Running semantic vector matching...</div>
            ) : searchResults.length === 0 ? (
              <div style={emptyState}>Query the database to find related research and notes.</div>
            ) : (
              searchResults.map(item => (
                <div key={item.id} style={resultCard} className="glass-panel">
                  <div style={cardMeta}>
                    <span style={matchBadge}>
                      Match {Math.round((item.relevance || 0) * 100)}%
                    </span>
                    <span style={timeText}>Source: {item.type.toUpperCase()}</span>
                  </div>
                  <p style={cardContent}>{item.content}</p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Obsidian + Memory timeline */}
        <div style={rightColumnContainer} className="right-column-container">
          
          {/* Upper Sub-Panel: Obsidian Integration */}
          <div style={obsidianPanelStyle} className="glass-panel">
            <div style={sectionHeader}>
              <FolderOpen size={18} color="var(--accent-gold)" />
              <h3 style={sectionTitle}>Obsidian Vault Integration</h3>
            </div>

            <div style={obsidianForm}>
              <input
                type="text"
                placeholder="Vault Path (e.g. D:\Obsidian\MyVault)..."
                value={vaultPath}
                onChange={e => setVaultPath(e.target.value)}
                style={obsidianInput}
              />
              <button 
                onClick={handleSaveVaultPath} 
                style={obsidianBtn}
                disabled={isConfiguring || isSyncing}
              >
                {isConfiguring ? 'Linking...' : 'Link Vault'}
              </button>
            </div>

            {obsidianStatus && (
              <div style={syncStatusContainer}>
                <div style={statusRow}>
                  <div style={statusItem}>
                    <span style={statusLabel}>Last Synced</span>
                    <span style={statusValue}>
                      {obsidianStatus.last_sync && obsidianStatus.last_sync !== 'Never'
                        ? obsidianStatus.last_sync.replace('T', ' ').substring(0, 16)
                        : 'Never'}
                    </span>
                  </div>
                  <div style={statusItem}>
                    <span style={statusLabel}>Total Notes</span>
                    <span style={statusValue}>{obsidianStatus.total_notes} files</span>
                  </div>
                </div>

                {obsidianStatus.vault_path && (
                  <button 
                    onClick={handleSyncVault} 
                    style={syncBtnStyle}
                    disabled={isSyncing}
                  >
                    <RefreshCw size={12} className={isSyncing ? "animate-spin" : ""} style={{ marginRight: '6px' }} />
                    {isSyncing ? 'Synchronizing...' : 'Sync Vault Now'}
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Lower Sub-Panel: Timeline Feed */}
          <div style={timelinePanelStyle} className="glass-panel">
            <div style={sectionHeader}>
              <History size={18} color="var(--accent-purple)" />
              <h3 style={sectionTitle}>Timeline Feed</h3>
            </div>

            <div style={listScroll} className="fade-scroll-container">
              {timeline.length === 0 ? (
                <div style={emptyState}>No ingestion activities logged.</div>
              ) : (
                timeline.map(item => (
                  <div key={item.id} style={timelineCard}>
                    <div style={timelineDotContainer}>
                      <div style={timelineLine} />
                      <div style={timelineDot} />
                    </div>
                    
                    <div style={timelineContentBlock} className="glass-panel">
                      <div style={cardHeader}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {getIcon(item.type)}
                          <span style={itemTypeText}>{item.type.replace('_', ' ').toUpperCase()}</span>
                        </div>
                        <span style={timeText}>{item.timestamp}</span>
                      </div>
                      <p style={timelineContentText}>{item.content}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

// --- Styles ---
const containerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  width: '100%'
};

const splitLayout: React.CSSProperties = {
  display: 'flex',
  gap: '16px',
  flex: 1,
  minHeight: 0
};

const panelStyle: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  padding: '16px',
  minHeight: 0
};

const rightColumnContainer: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  gap: '16px',
  minHeight: 0
};

const obsidianPanelStyle: React.CSSProperties = {
  padding: '16px',
  display: 'flex',
  flexDirection: 'column',
  borderRadius: '12px',
  background: 'rgba(25, 26, 35, 0.25)',
  border: '1px solid var(--border-glass)'
};

const timelinePanelStyle: React.CSSProperties = {
  flex: 1,
  padding: '16px',
  display: 'flex',
  flexDirection: 'column',
  minHeight: 0
};

const sectionHeader: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginBottom: '14px',
  borderBottom: '1px solid var(--border-glass)',
  paddingBottom: '8px'
};

const sectionTitle: React.CSSProperties = {
  margin: '0',
  fontSize: '14px',
  fontWeight: 600,
  color: '#fff'
};

const searchBar: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-glass)',
  borderRadius: '12px',
  marginBottom: '16px',
  padding: '4px'
};

const searchInput: React.CSSProperties = {
  flex: 1,
  background: 'transparent',
  border: 'none',
  padding: '8px 10px',
  color: '#fff',
  fontSize: '13px',
  outline: 'none'
};

const searchBtn: React.CSSProperties = {
  padding: '6px 16px',
  background: 'linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-purple) 100%)',
  border: 'none',
  borderRadius: '8px',
  color: '#fff',
  fontSize: '12px',
  fontWeight: 500,
  cursor: 'pointer'
};

const listScroll: React.CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: '12px'
};

const loadingText: React.CSSProperties = {
  textAlign: 'center',
  padding: '32px 0',
  fontSize: '13px',
  color: 'var(--accent-cyan)'
};

const emptyState: React.CSSProperties = {
  textAlign: 'center',
  padding: '32px 0',
  fontSize: '12px',
  color: 'var(--text-muted)'
};

const resultCard: React.CSSProperties = {
  padding: '12px',
  background: 'rgba(25, 26, 35, 0.4)',
  display: 'flex',
  flexDirection: 'column',
  gap: '6px',
  border: '1px solid var(--border-glass)',
  borderRadius: '12px'
};

const cardMeta: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
};

const matchBadge: React.CSSProperties = {
  fontSize: '10px',
  fontWeight: 600,
  background: 'rgba(0, 242, 254, 0.1)',
  color: 'var(--accent-cyan)',
  padding: '2px 6px',
  borderRadius: '4px'
};

const timeText: React.CSSProperties = {
  fontSize: '11px',
  color: 'var(--text-secondary)'
};

const cardContent: React.CSSProperties = {
  margin: '0',
  fontSize: '13px',
  color: 'var(--text-primary)',
  lineHeight: 1.45
};

const timelineCard: React.CSSProperties = {
  display: 'flex',
  gap: '16px'
};

const timelineDotContainer: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  position: 'relative',
  width: '16px'
};

const timelineLine: React.CSSProperties = {
  position: 'absolute',
  top: '0',
  bottom: '-12px',
  width: '2px',
  background: 'var(--border-glass)'
};

const timelineDot: React.CSSProperties = {
  width: '10px',
  height: '10px',
  borderRadius: '50%',
  background: 'var(--accent-purple)',
  border: '2px solid var(--bg-primary)',
  zIndex: 1,
  marginTop: '16px'
};

const timelineContentBlock: React.CSSProperties = {
  flex: 1,
  padding: '12px',
  background: 'rgba(25, 26, 35, 0.4)',
  display: 'flex',
  flexDirection: 'column',
  gap: '6px',
  border: '1px solid var(--border-glass)',
  borderRadius: '12px'
};

const cardHeader: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
};

const itemTypeText: React.CSSProperties = {
  fontSize: '10px',
  fontWeight: 600,
  color: '#fff',
  letterSpacing: '0.5px'
};

const timelineContentText: React.CSSProperties = {
  margin: '0',
  fontSize: '12px',
  color: 'var(--text-primary)',
  lineHeight: 1.4
};

/* Obsidian Specific Styles */
const obsidianForm: React.CSSProperties = {
  display: 'flex',
  gap: '8px',
  alignItems: 'center',
  marginBottom: '12px'
};

const obsidianInput: React.CSSProperties = {
  flex: 1,
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-glass)',
  borderRadius: '10px',
  padding: '8px 12px',
  color: '#fff',
  fontSize: '13px',
  outline: 'none'
};

const obsidianBtn: React.CSSProperties = {
  padding: '8px 16px',
  background: 'rgba(255, 179, 0, 0.15)',
  border: '1px solid rgba(255, 179, 0, 0.3)',
  borderRadius: '10px',
  color: 'var(--accent-gold)',
  fontSize: '12px',
  fontWeight: 500,
  cursor: 'pointer',
  whiteSpace: 'nowrap'
};

const syncStatusContainer: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
  background: 'rgba(10, 10, 15, 0.25)',
  padding: '10px',
  borderRadius: '8px',
  border: '1px solid rgba(255, 255, 255, 0.03)'
};

const statusRow: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  gap: '12px'
};

const statusItem: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  gap: '2px'
};

const statusLabel: React.CSSProperties = {
  fontSize: '10px',
  color: 'var(--text-secondary)',
  textTransform: 'uppercase',
  letterSpacing: '0.5px'
};

const statusValue: React.CSSProperties = {
  fontSize: '12px',
  color: '#fff',
  fontWeight: 500
};

const syncBtnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '8px',
  background: 'linear-gradient(135deg, rgba(79, 195, 247, 0.1) 0%, rgba(0, 184, 212, 0.1) 100%)',
  border: '1px solid rgba(79, 195, 247, 0.2)',
  borderRadius: '8px',
  color: 'var(--accent-cyan)',
  fontSize: '12px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'opacity 0.2s'
};
