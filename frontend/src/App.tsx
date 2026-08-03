import React, { useEffect, useState, useCallback } from 'react';
import { useStore } from './store/useStore';
import { useParallax } from './hooks/useParallax';
import { useOrbState } from './hooks/useOrbState';
import { ChatPage } from './pages/ChatPage';
import { TasksPage } from './pages/TasksPage';
import { AutomationPage } from './pages/AutomationPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { NetworkBackground } from './components/network/NetworkBackground';
import { ToastFeed } from './components/ToastFeed';
import { MessageSquare, Kanban, Cpu, BrainCircuit, X, Terminal } from 'lucide-react';

type TabId = 'chat' | 'tasks' | 'automation' | 'knowledge';

export default function App() {
  useParallax();

  const [activeTab, setActiveTab] = useState<TabId | null>(null);
  const [bootStage, setBootStage] = useState(0);
  const [navVisible, setNavVisible] = useState(true);

  const initializeAuth = useStore(state => state.initializeAuth);
  const token = useStore(state => state.token);
  const fetchProjects = useStore(state => state.fetchProjects);
  const fetchTasks = useStore(state => state.fetchTasks);
  const amplitude = useStore(state => state.amplitude || 0);

  const { orbState } = useOrbState();
  const voiceActive = useStore(state => state.voiceInputActive);

  // Boot sequence
  useEffect(() => {
    initializeAuth();
    const t1 = setTimeout(() => setBootStage(1), 400);
    const t2 = setTimeout(() => setBootStage(2), 1000);
    const t3 = setTimeout(() => setBootStage(3), 1600);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [initializeAuth]);

  useEffect(() => {
    if (token) { fetchProjects(); fetchTasks(); }
  }, [token, fetchProjects, fetchTasks]);

  const toggleTab = useCallback((tab: TabId) => {
    setActiveTab(prev => prev === tab ? null : tab);
  }, []);

  const closePanel = useCallback(() => setActiveTab(null), []);

  // --- Boot loader ---
  if (bootStage === 0) {
    return (
      <div className="boot-screen">
        <div className="boot-scanner" />
        <span className="boot-text">KLAUSE SYSTEM INITIALIZING...</span>
      </div>
    );
  }

  const isPanelOpen = activeTab !== null;

  return (
    <div className="hud-root parallax-container">
      {/* 3D Neural Network Viewport — Base layer */}
      {bootStage >= 1 && (
        <NetworkBackground 
          orbState={orbState} 
          amplitude={amplitude} 
          isPanelOpen={isPanelOpen} 
        />
      )}

      {/* Screen CRT and Fog Filters */}
      <div className="crt-overlay" />
      <div className="depth-fog" />

      {/* Floating System Status HUD Widgets */}
      {bootStage >= 2 && (
        <div className="hud-stats animate-slide-in">
          <div className="hud-stats__item">
            <Terminal size={12} color="var(--jarvis-primary)" />
            <span className="hud-stats__label">CORE_INDEX //</span>
            <span className="hud-stats__value">{orbState.toUpperCase()}</span>
          </div>
          {voiceActive && (
            <div className="hud-stats__item hud-stats__item--rec">
              <span className="hud-stats__rec-dot" />
              <span className="hud-stats__label">AUDIO_CAP // RECORDING</span>
            </div>
          )}
          <div className="hud-stats__item">
            <Cpu size={12} color="var(--jarvis-primary)" />
            <span className="hud-stats__label">SYS_LOAD //</span>
            <span className="hud-stats__value">NOMINAL</span>
          </div>
        </div>
      )}

      {/* Floating navigation pill */}
      {bootStage >= 3 && (
        <>
          <div className={`nav-pill ${navVisible ? 'nav-pill--visible' : 'nav-pill--hidden'}`}>
            <NavButton
              icon={<MessageSquare size={16} />}
              label="Chat"
              active={activeTab === 'chat'}
              onClick={() => toggleTab('chat')}
            />
            <NavButton
              icon={<Kanban size={16} />}
              label="Tasks"
              active={activeTab === 'tasks'}
              onClick={() => toggleTab('tasks')}
            />
            <NavButton
              icon={<Cpu size={16} />}
              label="Auto"
              active={activeTab === 'automation'}
              onClick={() => toggleTab('automation')}
            />
            <NavButton
              icon={<BrainCircuit size={16} />}
              label="Know"
              active={activeTab === 'knowledge'}
              onClick={() => toggleTab('knowledge')}
            />

            {/* Nav toggle */}
            <button
              className="nav-pill__toggle"
              onClick={() => setNavVisible(false)}
              title="Hide Navigation"
            >
              <span className="nav-pill__toggle-dot" />
            </button>
          </div>

          {!navVisible && (
            <button
              className="nav-trigger-btn"
              onClick={() => setNavVisible(true)}
              title="Show Navigation"
            >
              <span className="nav-trigger-btn__dot" />
            </button>
          )}
        </>
      )}

      {/* Slide-in panel overlay */}
      <div className={`panel-overlay ${isPanelOpen ? 'panel-overlay--open' : ''}`}>
        {isPanelOpen && (
          <div className="panel-container glass-panel glass-panel-glow">
            {/* Panel header */}
            <div className="panel-header">
              <div className="panel-header__title">
                <span className="panel-header__dot" />
                <span className="panel-header__label">
                  {activeTab?.toUpperCase()}
                </span>
              </div>
              <button className="panel-header__close" onClick={closePanel} title="Close Panel">
                <X size={14} color="#fff" />
              </button>
            </div>

            {/* Panel content */}
            <div className="panel-content interactive-flat">
              {activeTab === 'chat' && <ChatPage />}
              {activeTab === 'tasks' && <TasksPage />}
              {activeTab === 'automation' && <AutomationPage />}
              {activeTab === 'knowledge' && <KnowledgePage />}
            </div>
          </div>
        )}
      </div>

      {/* Floating Micro-Feedback Toast alerts */}
      {bootStage >= 2 && <ToastFeed />}
    </div>
  );
}

// --- Small NavButton component ---
interface NavButtonProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}

function NavButton({ icon, label, active, onClick }: NavButtonProps) {
  return (
    <button
      className={`nav-btn ${active ? 'nav-btn--active' : ''}`}
      onClick={onClick}
      title={label}
    >
      <span className="nav-btn__icon">{icon}</span>
      <span className="nav-btn__label">{label}</span>
    </button>
  );
}
