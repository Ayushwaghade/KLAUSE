import React, { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import { 
  Sliders, 
  FileCode, 
  Save, 
  RotateCcw, 
  User, 
  Cpu, 
  Mic, 
  Globe, 
  Folder, 
  Sparkles
} from 'lucide-react';

export const ConfigPage: React.FC = () => {
  const config = useStore(state => state.config);
  const rawYaml = useStore(state => state.rawYaml);
  const fetchConfig = useStore(state => state.fetchConfig);
  const saveConfig = useStore(state => state.saveConfig);

  const [mode, setMode] = useState<'form' | 'yaml'>('form');
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [yamlText, setYamlText] = useState('');
  const [activeCategory, setActiveCategory] = useState<'identity' | 'ai' | 'voice' | 'browser' | 'storage'>('identity');
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  useEffect(() => {
    if (config) {
      setFormData(JSON.parse(JSON.stringify(config)));
    }
    if (rawYaml) {
      setYamlText(rawYaml);
    }
  }, [config, rawYaml]);

  const updateField = (path: string[], value: any) => {
    setFormData(prev => {
      const next = JSON.parse(JSON.stringify(prev));
      let current = next;
      for (let i = 0; i < path.length - 1; i++) {
        if (!current[path[i]] || typeof current[path[i]] !== 'object') {
          current[path[i]] = {};
        }
        current = current[path[i]];
      }
      current[path[path.length - 1]] = value;
      return next;
    });
    setHasChanges(true);
  };

  const getField = (path: string[], fallback: any = '') => {
    let current = formData;
    for (const p of path) {
      if (current === undefined || current === null) return fallback;
      current = current[p];
    }
    return current !== undefined && current !== null ? current : fallback;
  };

  const handleSave = async () => {
    setIsSaving(true);
    let success = false;
    if (mode === 'yaml') {
      success = await saveConfig({ raw_yaml: yamlText });
    } else {
      success = await saveConfig({ config: formData });
    }
    setIsSaving(false);
    if (success) {
      setHasChanges(false);
    }
  };

  const handleRevert = () => {
    if (config) {
      setFormData(JSON.parse(JSON.stringify(config)));
    }
    if (rawYaml) {
      setYamlText(rawYaml);
    }
    setHasChanges(false);
  };

  const userName = getField(['klause', 'user_name'], getField(['user_name'], 'Ayush'));

  return (
    <div style={containerStyle} className="animate-slide-in">
      {/* Top Action Bar */}
      <div style={topBar}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ margin: 0, fontSize: '20px', letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
              SYSTEM CONFIGURATION
            </h2>
            <span style={userBadge}>
              <User size={12} color="var(--jarvis-primary)" />
              {userName}
            </span>
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            E:\KLAUSE\config.yaml &bull; Live In-Memory Synchronization
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* Mode Switcher */}
          <div style={modeToggleGroup}>
            <button
              style={{ ...modeBtn, ...(mode === 'form' ? activeModeBtn : {}) }}
              onClick={() => setMode('form')}
            >
              <Sliders size={14} />
              Form
            </button>
            <button
              style={{ ...modeBtn, ...(mode === 'yaml' ? activeModeBtn : {}) }}
              onClick={() => {
                setMode('yaml');
              }}
            >
              <FileCode size={14} />
              YAML
            </button>
          </div>

          {/* Revert Button */}
          <button
            style={secondaryBtn}
            onClick={handleRevert}
            disabled={!hasChanges && yamlText === rawYaml}
            title="Discard unsaved changes"
          >
            <RotateCcw size={14} />
            Revert
          </button>

          {/* Save Button */}
          <button
            style={{
              ...primaryBtn,
              opacity: isSaving ? 0.7 : 1,
              boxShadow: hasChanges ? '0 0 16px rgba(79, 195, 247, 0.4)' : 'none'
            }}
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? <Sparkles size={14} className="spin" /> : <Save size={14} />}
            {isSaving ? 'Applying...' : 'Save & Apply'}
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      {mode === 'yaml' ? (
        /* YAML Code Editor View */
        <div style={yamlContainer} className="glass-panel">
          <div style={yamlHeader}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', color: 'var(--text-secondary)' }}>
              config.yaml (Raw Text Editor)
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Saving directly validates YAML and reloads the active runtime.
            </span>
          </div>
          <textarea
            style={yamlTextarea}
            value={yamlText}
            onChange={e => {
              setYamlText(e.target.value);
              setHasChanges(true);
            }}
            spellCheck={false}
          />
        </div>
      ) : (
        /* Visual Category Form View */
        <div style={formLayout}>
          {/* Category Navigation Sidebar */}
          <div style={sidebarStyle} className="glass-panel">
            <button
              style={{ ...catBtn, ...(activeCategory === 'identity' ? activeCatBtn : {}) }}
              onClick={() => setActiveCategory('identity')}
            >
              <User size={16} />
              <span>Identity & User</span>
            </button>

            <button
              style={{ ...catBtn, ...(activeCategory === 'ai' ? activeCatBtn : {}) }}
              onClick={() => setActiveCategory('ai')}
            >
              <Cpu size={16} />
              <span>AI & Models</span>
            </button>

            <button
              style={{ ...catBtn, ...(activeCategory === 'voice' ? activeCatBtn : {}) }}
              onClick={() => setActiveCategory('voice')}
            >
              <Mic size={16} />
              <span>Voice & Audio</span>
            </button>

            <button
              style={{ ...catBtn, ...(activeCategory === 'browser' ? activeCatBtn : {}) }}
              onClick={() => setActiveCategory('browser')}
            >
              <Globe size={16} />
              <span>Browser & Automations</span>
            </button>

            <button
              style={{ ...catBtn, ...(activeCategory === 'storage' ? activeCatBtn : {}) }}
              onClick={() => setActiveCategory('storage')}
            >
              <Folder size={16} />
              <span>Storage & DBs</span>
            </button>
          </div>

          {/* Form Content Panel */}
          <div style={formContentPanel} className="glass-panel fade-scroll-container">
            {activeCategory === 'identity' && (
              <div style={sectionWrapper}>
                <div style={sectionHeader}>
                  <User size={18} color="var(--jarvis-primary)" />
                  <h3 style={sectionTitle}>User & Assistant Identity</h3>
                </div>

                <div style={grid2}>
                  <div style={inputGroup}>
                    <label style={labelStyle}>
                      User Name (What KLAUSE calls you)
                      <span style={hintStyle}>Configures the dynamic prompt address</span>
                    </label>
                    <input
                      style={inputStyle}
                      type="text"
                      placeholder="e.g. Ayush"
                      value={userName}
                      onChange={e => updateField(['klause', 'user_name'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Assistant Name</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['klause', 'name'], 'KLAUSE')}
                      onChange={e => updateField(['klause', 'name'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Voice Wake Word</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['klause', 'wake_word'], 'klause')}
                      onChange={e => updateField(['klause', 'wake_word'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Personality Style</label>
                    <select
                      style={selectStyle}
                      value={getField(['klause', 'personality'], 'hacker')}
                      onChange={e => updateField(['klause', 'personality'], e.target.value)}
                    >
                      <option value="hacker">Hacker (Witty, cheeky, elite peer programmer)</option>
                      <option value="architect">Architect (Direct, authoritative, clean code)</option>
                      <option value="supportive">Supportive (Warm, dedicated companion)</option>
                      <option value="minimalist">Minimalist (Ultra-brief, zero filler)</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {activeCategory === 'ai' && (
              <div style={sectionWrapper}>
                <div style={sectionHeader}>
                  <Cpu size={18} color="var(--jarvis-primary)" />
                  <h3 style={sectionTitle}>AI Provider & LLM Models</h3>
                </div>

                <div style={grid2}>
                  <div style={inputGroup}>
                    <label style={labelStyle}>Primary AI Provider</label>
                    <select
                      style={selectStyle}
                      value={getField(['ai', 'provider'], 'gemini')}
                      onChange={e => updateField(['ai', 'provider'], e.target.value)}
                    >
                      <option value="gemini">Google Gemini (Default)</option>
                      <option value="nvidia">NVIDIA Nemotron / OpenAI API</option>
                    </select>
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Gemini Model</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['ai', 'gemini_model'], 'gemini-3.1-flash-lite-preview')}
                      onChange={e => updateField(['ai', 'gemini_model'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>NVIDIA / Nemotron Model</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['ai', 'nvidia_model'], 'nvidia/nemotron-3-ultra-550b-a55b')}
                      onChange={e => updateField(['ai', 'nvidia_model'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>NVIDIA Base URL</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['ai', 'nvidia_base_url'], 'https://integrate.api.nvidia.com/v1')}
                      onChange={e => updateField(['ai', 'nvidia_base_url'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Max Tokens</label>
                    <input
                      style={inputStyle}
                      type="number"
                      value={getField(['ai', 'max_tokens'], 8192)}
                      onChange={e => updateField(['ai', 'max_tokens'], parseInt(e.target.value) || 8192)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Max ReAct Loop Steps</label>
                    <input
                      style={inputStyle}
                      type="number"
                      value={getField(['ai', 'max_steps'], 10)}
                      onChange={e => updateField(['ai', 'max_steps'], parseInt(e.target.value) || 10)}
                    />
                  </div>
                </div>

                <div style={{ ...subSection, marginTop: '20px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                    <div>
                      <h4 style={{ margin: 0, fontSize: '15px', color: 'var(--jarvis-primary)' }}>Dynamic Model Routing</h4>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        Route simple queries to fast model and deep reasoning to complex model
                      </span>
                    </div>
                    <label style={toggleSwitch}>
                      <input
                        type="checkbox"
                        checked={getField(['ai', 'routing_enabled'], false)}
                        onChange={e => updateField(['ai', 'routing_enabled'], e.target.checked)}
                      />
                      <span style={sliderSpan} />
                    </label>
                  </div>

                  {getField(['ai', 'routing_enabled'], false) && (
                    <div style={grid2}>
                      <div style={inputGroup}>
                        <label style={labelStyle}>Fast Provider</label>
                        <select
                          style={selectStyle}
                          value={getField(['ai', 'fast_provider'], 'gemini')}
                          onChange={e => updateField(['ai', 'fast_provider'], e.target.value)}
                        >
                          <option value="gemini">Gemini</option>
                          <option value="nvidia">NVIDIA</option>
                        </select>
                      </div>

                      <div style={inputGroup}>
                        <label style={labelStyle}>Fast Model</label>
                        <input
                          style={inputStyle}
                          type="text"
                          value={getField(['ai', 'fast_model'], 'gemini-3.1-flash-lite-preview')}
                          onChange={e => updateField(['ai', 'fast_model'], e.target.value)}
                        />
                      </div>

                      <div style={inputGroup}>
                        <label style={labelStyle}>Complex Provider</label>
                        <select
                          style={selectStyle}
                          value={getField(['ai', 'complex_provider'], 'nvidia')}
                          onChange={e => updateField(['ai', 'complex_provider'], e.target.value)}
                        >
                          <option value="nvidia">NVIDIA</option>
                          <option value="gemini">Gemini</option>
                        </select>
                      </div>

                      <div style={inputGroup}>
                        <label style={labelStyle}>Complex Model</label>
                        <input
                          style={inputStyle}
                          type="text"
                          value={getField(['ai', 'complex_model'], 'nvidia/nemotron-3-ultra-550b-a55b')}
                          onChange={e => updateField(['ai', 'complex_model'], e.target.value)}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeCategory === 'voice' && (
              <div style={sectionWrapper}>
                <div style={sectionHeader}>
                  <Mic size={18} color="var(--jarvis-primary)" />
                  <h3 style={sectionTitle}>Voice, Speech & Live Typer</h3>
                </div>

                <div style={grid2}>
                  <div style={inputGroup}>
                    <label style={labelStyle}>Voice Engine Enabled</label>
                    <label style={toggleSwitch}>
                      <input
                        type="checkbox"
                        checked={getField(['voice', 'enabled'], true)}
                        onChange={e => updateField(['voice', 'enabled'], e.target.checked)}
                      />
                      <span style={sliderSpan} />
                    </label>
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Trigger Mode</label>
                    <select
                      style={selectStyle}
                      value={getField(['voice', 'trigger_mode'], 'push_to_talk')}
                      onChange={e => updateField(['voice', 'trigger_mode'], e.target.value)}
                    >
                      <option value="push_to_talk">Push To Talk</option>
                      <option value="wake_word">Wake Word Only</option>
                      <option value="continuous">Continuous Ambient</option>
                    </select>
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Push-to-Talk Hotkey</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['voice', 'hotkey'], 'ctrl+space')}
                      onChange={e => updateField(['voice', 'hotkey'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Speech-To-Text (STT) Engine</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['voice', 'stt_engine'], 'whisper')}
                      onChange={e => updateField(['voice', 'stt_engine'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Text-To-Speech (TTS) Engine</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['voice', 'tts_engine'], 'sapi')}
                      onChange={e => updateField(['voice', 'tts_engine'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Live Typer Hotkey</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['voice', 'live_typer', 'hotkey'], 'ctrl+shift+v')}
                      onChange={e => updateField(['voice', 'live_typer', 'hotkey'], e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeCategory === 'browser' && (
              <div style={sectionWrapper}>
                <div style={sectionHeader}>
                  <Globe size={18} color="var(--jarvis-primary)" />
                  <h3 style={sectionTitle}>Browser & OS Automations</h3>
                </div>

                <div style={grid2}>
                  <div style={inputGroup}>
                    <label style={labelStyle}>Preferred Browser</label>
                    <select
                      style={selectStyle}
                      value={getField(['browser', 'prefer'], 'brave')}
                      onChange={e => updateField(['browser', 'prefer'], e.target.value)}
                    >
                      <option value="brave">Brave Browser</option>
                      <option value="chrome">Google Chrome</option>
                      <option value="msedge">Microsoft Edge</option>
                      <option value="firefox">Mozilla Firefox</option>
                    </select>
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Browser Profile Directory</label>
                    <input
                      style={inputStyle}
                      type="text"
                      placeholder="e.g. Default"
                      value={getField(['browser', 'profile_directory'], 'Default')}
                      onChange={e => updateField(['browser', 'profile_directory'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Desktop State Machine Active</label>
                    <label style={toggleSwitch}>
                      <input
                        type="checkbox"
                        checked={getField(['state_machine', 'enabled'], true)}
                        onChange={e => updateField(['state_machine', 'enabled'], e.target.checked)}
                      />
                      <span style={sliderSpan} />
                    </label>
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Capture Clipboard Telemetry</label>
                    <label style={toggleSwitch}>
                      <input
                        type="checkbox"
                        checked={getField(['state_machine', 'capture_clipboard'], true)}
                        onChange={e => updateField(['state_machine', 'capture_clipboard'], e.target.checked)}
                      />
                      <span style={sliderSpan} />
                    </label>
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Automation Rules Engine</label>
                    <label style={toggleSwitch}>
                      <input
                        type="checkbox"
                        checked={getField(['automation', 'enabled'], true)}
                        onChange={e => updateField(['automation', 'enabled'], e.target.checked)}
                      />
                      <span style={sliderSpan} />
                    </label>
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Max Active Rules</label>
                    <input
                      style={inputStyle}
                      type="number"
                      value={getField(['automation', 'max_rules'], 50)}
                      onChange={e => updateField(['automation', 'max_rules'], parseInt(e.target.value) || 50)}
                    />
                  </div>
                </div>
              </div>
            )}

            {activeCategory === 'storage' && (
              <div style={sectionWrapper}>
                <div style={sectionHeader}>
                  <Folder size={18} color="var(--jarvis-primary)" />
                  <h3 style={sectionTitle}>Storage, Paths & Databases</h3>
                </div>

                <div style={grid2}>
                  <div style={inputGroup}>
                    <label style={labelStyle}>Knowledge Base Path</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['paths', 'knowledge_base'], './knowledge_base')}
                      onChange={e => updateField(['paths', 'knowledge_base'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Projects Directory</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['paths', 'projects'], './projects')}
                      onChange={e => updateField(['paths', 'projects'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>MongoDB URI</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['memory', 'mongo_uri'], 'mongodb://localhost:27017/')}
                      onChange={e => updateField(['memory', 'mongo_uri'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>MongoDB Database Name</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['memory', 'mongo_db'], 'klause')}
                      onChange={e => updateField(['memory', 'mongo_db'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Chroma Vector Store Path</label>
                    <input
                      style={inputStyle}
                      type="text"
                      value={getField(['memory', 'chroma_path'], './data/chroma')}
                      onChange={e => updateField(['memory', 'chroma_path'], e.target.value)}
                    />
                  </div>

                  <div style={inputGroup}>
                    <label style={labelStyle}>Max Conversation History</label>
                    <input
                      style={inputStyle}
                      type="number"
                      value={getField(['memory', 'max_conversation_history'], 100)}
                      onChange={e => updateField(['memory', 'max_conversation_history'], parseInt(e.target.value) || 100)}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// --- STYLES ---

const containerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  gap: '16px',
};

const topBar: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  paddingBottom: '12px',
  borderBottom: '1px solid var(--border-glass)',
};

const userBadge: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '4px',
  padding: '2px 8px',
  background: 'rgba(79, 195, 247, 0.1)',
  border: '1px solid rgba(79, 195, 247, 0.25)',
  borderRadius: '12px',
  fontSize: '11px',
  fontFamily: 'var(--font-mono)',
  color: 'var(--jarvis-primary)',
};

const modeToggleGroup: React.CSSProperties = {
  display: 'flex',
  background: 'rgba(10, 20, 32, 0.6)',
  border: '1px solid var(--border-glass)',
  borderRadius: '6px',
  padding: '2px',
};

const modeBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  padding: '6px 12px',
  border: 'none',
  background: 'transparent',
  color: 'var(--text-secondary)',
  fontSize: '12px',
  borderRadius: '4px',
  cursor: 'pointer',
  transition: 'all 0.15s ease',
};

const activeModeBtn: React.CSSProperties = {
  background: 'rgba(79, 195, 247, 0.15)',
  color: 'var(--jarvis-primary)',
  fontWeight: 600,
};

const primaryBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  padding: '7px 16px',
  background: 'linear-gradient(135deg, rgba(79, 195, 247, 0.25), rgba(0, 184, 212, 0.35))',
  border: '1px solid var(--jarvis-primary)',
  borderRadius: '6px',
  color: '#fff',
  fontSize: '12px',
  fontWeight: 600,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
};

const secondaryBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  padding: '7px 14px',
  background: 'rgba(10, 20, 32, 0.6)',
  border: '1px solid var(--border-glass)',
  borderRadius: '6px',
  color: 'var(--text-secondary)',
  fontSize: '12px',
  cursor: 'pointer',
};

const formLayout: React.CSSProperties = {
  display: 'flex',
  flex: 1,
  gap: '16px',
  minHeight: 0,
};

const sidebarStyle: React.CSSProperties = {
  width: '210px',
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  padding: '12px',
  borderRadius: '8px',
  background: 'var(--bg-glass)',
  border: '1px solid var(--border-glass)',
};

const catBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  padding: '10px 12px',
  border: 'none',
  background: 'transparent',
  color: 'var(--text-secondary)',
  fontSize: '13px',
  borderRadius: '6px',
  cursor: 'pointer',
  textAlign: 'left',
  transition: 'all 0.15s ease',
};

const activeCatBtn: React.CSSProperties = {
  background: 'rgba(79, 195, 247, 0.15)',
  color: 'var(--jarvis-primary)',
  fontWeight: 600,
  borderLeft: '3px solid var(--jarvis-primary)',
};

const formContentPanel: React.CSSProperties = {
  flex: 1,
  padding: '20px',
  borderRadius: '8px',
  background: 'var(--bg-glass)',
  border: '1px solid var(--border-glass)',
  overflowY: 'auto',
};

const sectionWrapper: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '16px',
};

const sectionHeader: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginBottom: '8px',
  paddingBottom: '8px',
  borderBottom: '1px solid var(--border-glass)',
};

const sectionTitle: React.CSSProperties = {
  margin: 0,
  fontSize: '16px',
  fontWeight: 600,
  color: 'var(--text-primary)',
};

const grid2: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: '1fr 1fr',
  gap: '16px',
};

const inputGroup: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '6px',
};

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  fontSize: '12px',
  fontWeight: 500,
  color: 'var(--text-secondary)',
};

const hintStyle: React.CSSProperties = {
  fontSize: '10px',
  color: 'var(--text-muted)',
  marginTop: '2px',
};

const inputStyle: React.CSSProperties = {
  background: 'rgba(2, 5, 8, 0.8)',
  border: '1px solid var(--border-glass)',
  borderRadius: '5px',
  padding: '8px 12px',
  color: 'var(--text-primary)',
  fontSize: '13px',
  fontFamily: 'var(--font-mono)',
  outline: 'none',
  transition: 'border-color 0.2s',
};

const selectStyle: React.CSSProperties = {
  background: 'rgba(2, 5, 8, 0.8)',
  border: '1px solid var(--border-glass)',
  borderRadius: '5px',
  padding: '8px 12px',
  color: 'var(--text-primary)',
  fontSize: '13px',
  outline: 'none',
  cursor: 'pointer',
};

const subSection: React.CSSProperties = {
  background: 'rgba(2, 5, 8, 0.4)',
  border: '1px solid var(--border-glass)',
  borderRadius: '8px',
  padding: '16px',
};

const toggleSwitch: React.CSSProperties = {
  position: 'relative',
  display: 'inline-block',
  width: '38px',
  height: '20px',
};

const sliderSpan: React.CSSProperties = {
  position: 'absolute',
  cursor: 'pointer',
  inset: 0,
  backgroundColor: 'rgba(79, 195, 247, 0.15)',
  border: '1px solid var(--border-glass)',
  borderRadius: '20px',
  transition: '0.2s',
};

const yamlContainer: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  borderRadius: '8px',
  background: 'var(--bg-glass)',
  border: '1px solid var(--border-glass)',
  overflow: 'hidden',
};

const yamlHeader: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '10px 16px',
  background: 'rgba(2, 5, 8, 0.6)',
  borderBottom: '1px solid var(--border-glass)',
};

const yamlTextarea: React.CSSProperties = {
  flex: 1,
  width: '100%',
  background: 'rgba(2, 5, 8, 0.95)',
  color: '#A5D6A7',
  border: 'none',
  padding: '16px',
  fontFamily: 'var(--font-mono)',
  fontSize: '13px',
  lineHeight: '1.6',
  resize: 'none',
  outline: 'none',
  boxSizing: 'border-box',
};
