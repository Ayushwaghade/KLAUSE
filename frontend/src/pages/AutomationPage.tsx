import React, { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import { Trash2, Cpu, CalendarClock, Play } from 'lucide-react';

export const AutomationPage: React.FC = () => {
  const rules = useStore(state => state.rules);
  const schedules = useStore(state => state.schedules);
  
  const fetchRules = useStore(state => state.fetchRules);
  const fetchSchedule = useStore(state => state.fetchSchedule);
  
  const removeRule = useStore(state => state.removeRule);
  const removeScheduleJob = useStore(state => state.removeScheduleJob);
  const addScheduleCron = useStore(state => state.addScheduleCron);

  // New Job Input Fields
  const [newJobId, setNewJobId] = useState('');
  const [newJobCmd, setNewJobCmd] = useState('');
  const [newJobCron, setNewJobCron] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    fetchRules();
    fetchSchedule();
  }, [fetchRules, fetchSchedule]);

  const handleAddJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newJobId.trim() || !newJobCmd.trim() || !newJobCron.trim()) {
      setErrorMsg('All job fields are required.');
      return;
    }
    setErrorMsg('');
    await addScheduleCron(newJobId.trim(), newJobCmd.trim(), newJobCron.trim());
    setNewJobId('');
    setNewJobCmd('');
    setNewJobCron('');
  };

  return (
    <div style={containerStyle} className="animate-slide-in">
      {/* Title */}
      <h2 style={{ margin: '0 0 16px 0', fontSize: '22px' }}>Automation & Workflows</h2>

      <div style={splitLayout}>
        {/* Left Column: Event Rules List */}
        <div style={{ ...panelStyle, flex: 3 }} className="glass-panel">
          <div style={sectionHeader}>
            <Cpu size={18} color="var(--accent-cyan)" />
            <h3 style={sectionTitle}>Active Event Rules ({rules.length}/50)</h3>
          </div>
          
          <div style={listScroll} className="fade-scroll-container">
            {rules.length === 0 ? (
              <div style={emptyState}>No event-driven rules registered.</div>
            ) : (
              rules.map(rule => (
                <div key={rule.rule_id} style={itemCard} className="glass-panel">
                  <div style={cardHeader}>
                    <div>
                      <span style={ruleIdText}>{rule.rule_id}</span>
                      <div style={ruleMeta}>
                        Event: <span style={{ color: 'var(--accent-cyan)' }}>{rule.event_type}</span>
                        {rule.filter_pattern && (
                          <> | Filter: <span style={{ color: 'var(--accent-gold)' }}>"{rule.filter_pattern}"</span></>
                        )}
                      </div>
                    </div>
                    <button onClick={() => removeRule(rule.rule_id)} style={deleteBtn}>
                      <Trash2 size={14} color="var(--accent-red)" />
                    </button>
                  </div>
                  
                  <div style={payloadBlock}>
                    <div style={payloadHeader}>
                      Action: {rule.action_type === 'tool_call' ? 'Execute Tool' : 'Think Prompt'}
                    </div>
                    <pre style={payloadPre}>{JSON.stringify(rule.action_payload, null, 2)}</pre>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Scheduled Cron Jobs */}
        <div style={{ ...panelStyle, flex: 2 }} className="glass-panel">
          <div style={sectionHeader}>
            <CalendarClock size={18} color="var(--accent-purple)" />
            <h3 style={sectionTitle}>Scheduler & Timers</h3>
          </div>

          {/* Add Job Form */}
          <form onSubmit={handleAddJob} style={formStyle} className="glass-panel">
            <h4 style={formTitle}>Schedule Cron Job</h4>
            {errorMsg && <div style={errorBanner}>{errorMsg}</div>}
            
            <input 
              type="text" 
              placeholder="Job ID (e.g. daily_backup)" 
              value={newJobId} 
              onChange={e => setNewJobId(e.target.value)} 
              style={formInput}
            />
            <input 
              type="text" 
              placeholder="Terminal Command (e.g. git push)" 
              value={newJobCmd} 
              onChange={e => setNewJobCmd(e.target.value)} 
              style={formInput}
            />
            <input 
              type="text" 
              placeholder="Cron (e.g. */5 * * * *)" 
              value={newJobCron} 
              onChange={e => setNewJobCron(e.target.value)} 
              style={formInput}
            />
            
            <button type="submit" style={submitBtn}>
              <Play size={14} color="#fff" style={{ marginRight: '6px' }} />
              Schedule Job
            </button>
          </form>

          {/* Active Jobs List */}
          <div style={{ ...listScroll, marginTop: '16px' }} className="fade-scroll-container">
            {schedules.length === 0 ? (
              <div style={emptyState}>No cron jobs currently active.</div>
            ) : (
              schedules.map(job => (
                <div key={job.job_id} style={jobCard} className="glass-panel">
                  <div style={cardHeader}>
                    <div>
                      <span style={ruleIdText}>{job.job_id}</span>
                      <div style={jobCmd}>Command: <code>{job.command}</code></div>
                      <div style={jobTime}>Next Local Run: {job.next_run_time_local}</div>
                    </div>
                    <button onClick={() => removeScheduleJob(job.job_id)} style={deleteBtn}>
                      <Trash2 size={14} color="var(--accent-red)" />
                    </button>
                  </div>
                </div>
              ))
            )}
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
  display: 'flex',
  flexDirection: 'column',
  padding: '16px',
  minHeight: 0
};

const sectionHeader: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  marginBottom: '16px',
  borderBottom: '1px solid var(--border-glass)',
  paddingBottom: '8px'
};

const sectionTitle: React.CSSProperties = {
  margin: '0',
  fontSize: '15px',
  fontWeight: 600,
  color: '#fff'
};

const listScroll: React.CSSProperties = {
  flex: 1,
  overflowY: 'auto',
  display: 'flex',
  flexDirection: 'column',
  gap: '12px'
};

const emptyState: React.CSSProperties = {
  textAlign: 'center',
  padding: '32px 0',
  fontSize: '13px',
  color: 'var(--text-muted)'
};

const itemCard: React.CSSProperties = {
  padding: '12px',
  background: 'rgba(25, 26, 35, 0.4)',
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  border: '1px solid var(--border-glass)',
  borderRadius: '12px'
};

const cardHeader: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'flex-start'
};

const ruleIdText: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#fff'
};

const ruleMeta: React.CSSProperties = {
  fontSize: '11px',
  color: 'var(--text-secondary)',
  marginTop: '2px'
};

const deleteBtn: React.CSSProperties = {
  background: 'rgba(255, 30, 30, 0.1)',
  border: 'none',
  borderRadius: '6px',
  padding: '6px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'background-color 0.2s'
};

const payloadBlock: React.CSSProperties = {
  background: '#07080c',
  border: '1px solid rgba(255, 255, 255, 0.03)',
  borderRadius: '8px',
  padding: '8px'
};

const payloadHeader: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 500,
  color: 'var(--text-secondary)',
  marginBottom: '4px'
};

const payloadPre: React.CSSProperties = {
  margin: '0',
  fontSize: '11px',
  fontFamily: 'var(--font-mono)',
  color: 'var(--accent-cyan)',
  overflowX: 'auto'
};

const formStyle: React.CSSProperties = {
  padding: '12px',
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  background: 'rgba(25, 26, 35, 0.2)',
  border: '1px solid var(--border-glass)',
  borderRadius: '12px',
  marginBottom: '8px'
};

const formTitle: React.CSSProperties = {
  margin: '0 0 4px 0',
  fontSize: '13px',
  fontWeight: 600,
  color: '#fff'
};

const formInput: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-glass)',
  borderRadius: '8px',
  padding: '8px 12px',
  color: '#fff',
  fontSize: '13px',
  outline: 'none'
};

const submitBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '10px',
  background: 'linear-gradient(135deg, var(--accent-purple) 0%, #aa3bff 100%)',
  border: 'none',
  borderRadius: '8px',
  color: '#fff',
  fontSize: '13px',
  fontWeight: 500,
  cursor: 'pointer',
  marginTop: '4px'
};

const errorBanner: React.CSSProperties = {
  background: 'rgba(255, 30, 30, 0.1)',
  border: '1px solid rgba(255, 30, 30, 0.2)',
  borderRadius: '6px',
  padding: '6px 10px',
  fontSize: '11px',
  color: 'var(--accent-red)',
  marginBottom: '4px'
};

const jobCard: React.CSSProperties = {
  padding: '10px 12px',
  background: 'rgba(25, 26, 35, 0.4)',
  border: '1px solid var(--border-glass)',
  borderRadius: '10px'
};

const jobCmd: React.CSSProperties = {
  fontSize: '12px',
  marginTop: '4px',
  color: 'var(--text-primary)'
};

const jobTime: React.CSSProperties = {
  fontSize: '10px',
  color: 'var(--text-secondary)',
  marginTop: '2px'
};
