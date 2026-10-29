import React, { useEffect, useState, useMemo } from 'react';
import { useStore } from '../store/useStore';
import { Trash2, Cpu, CalendarClock, Play, Clock, Zap, Terminal } from 'lucide-react';

export const AutomationPage: React.FC = () => {
  const rules = useStore(state => state.rules);
  const schedules = useStore(state => state.schedules);
  
  const fetchRules = useStore(state => state.fetchRules);
  const fetchSchedule = useStore(state => state.fetchSchedule);
  
  const removeRule = useStore(state => state.removeRule);
  const removeScheduleJob = useStore(state => state.removeScheduleJob);
  const addScheduleCron = useStore(state => state.addScheduleCron);
  const runScheduleJob = useStore(state => state.runScheduleJob);

  // Friendly Task Form State
  const [taskName, setTaskName] = useState('');
  const [taskCmd, setTaskCmd] = useState('');
  const [frequency, setFrequency] = useState('every_15_min');
  const [timeOfDay, setTimeOfDay] = useState('09:00');
  const [dayOfWeek, setDayOfWeek] = useState('1'); // Monday
  const [customCron, setCustomCron] = useState('*/15 * * * *');
  const [errorMsg, setErrorMsg] = useState('');
  const [runningJobId, setRunningJobId] = useState<string | null>(null);

  useEffect(() => {
    fetchRules();
    fetchSchedule();
  }, [fetchRules, fetchSchedule]);

  // Compute cron expression & human readable summary
  const { computedCron, humanSummary } = useMemo(() => {
    const [hStr, mStr] = (timeOfDay || '09:00').split(':');
    const h = parseInt(hStr || '9', 10);
    const m = parseInt(mStr || '0', 10);
    const period = h >= 12 ? 'PM' : 'AM';
    const h12 = h % 12 === 0 ? 12 : h % 12;
    const timeFormatted = `${h12}:${m < 10 ? '0' + m : m} ${period}`;

    const daysMap: Record<string, string> = {
      '1': 'Monday', '2': 'Tuesday', '3': 'Wednesday',
      '4': 'Thursday', '5': 'Friday', '6': 'Saturday', '0': 'Sunday'
    };

    switch (frequency) {
      case 'every_5_min':
        return { computedCron: '*/5 * * * *', humanSummary: 'Runs every 5 minutes' };
      case 'every_15_min':
        return { computedCron: '*/15 * * * *', humanSummary: 'Runs every 15 minutes' };
      case 'every_30_min':
        return { computedCron: '*/30 * * * *', humanSummary: 'Runs every 30 minutes' };
      case 'hourly':
        return { computedCron: '0 * * * *', humanSummary: 'Runs every hour on the hour' };
      case 'every_2_hours':
        return { computedCron: '0 */2 * * *', humanSummary: 'Runs every 2 hours' };
      case 'every_6_hours':
        return { computedCron: '0 */6 * * *', humanSummary: 'Runs every 6 hours' };
      case 'daily':
        return { computedCron: `${m} ${h} * * *`, humanSummary: `Runs every day at ${timeFormatted}` };
      case 'weekdays':
        return { computedCron: `${m} ${h} * * 1-5`, humanSummary: `Runs every weekday (Mon–Fri) at ${timeFormatted}` };
      case 'weekly':
        return { computedCron: `${m} ${h} * * ${dayOfWeek}`, humanSummary: `Runs every ${daysMap[dayOfWeek] || 'Monday'} at ${timeFormatted}` };
      case 'custom':
        return { computedCron: customCron.trim() || '*/15 * * * *', humanSummary: `Custom cron schedule: ${customCron.trim()}` };
      default:
        return { computedCron: '*/15 * * * *', humanSummary: 'Runs every 15 minutes' };
    }
  }, [frequency, timeOfDay, dayOfWeek, customCron]);

  const handleAddJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskName.trim()) {
      setErrorMsg('Please enter a Task Name.');
      return;
    }
    if (!taskCmd.trim()) {
      setErrorMsg('Please enter a command to execute.');
      return;
    }

    // Auto-generate clean job_id (alphanumeric and underscores)
    const safeJobId = taskName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
    if (!safeJobId) {
      setErrorMsg('Task Name must contain letters or numbers.');
      return;
    }

    setErrorMsg('');
    await addScheduleCron(safeJobId, taskCmd.trim(), computedCron);
    setTaskName('');
    setTaskCmd('');
  };

  const handleRunNow = async (jobId: string) => {
    setRunningJobId(jobId);
    await runScheduleJob(jobId);
    setTimeout(() => setRunningJobId(null), 1200);
  };

  const commandPresets = [
    { label: 'git status', cmd: 'git status' },
    { label: 'git pull', cmd: 'git pull' },
    { label: 'npm test', cmd: 'npm test' },
    { label: 'System Check', cmd: 'echo "KLAUSE health nominal"' }
  ];

  return (
    <div style={containerStyle} className="animate-slide-in">
      {/* Page Title */}
      <div style={{ marginBottom: '16px' }}>
        <h2 style={{ margin: '0 0 4px 0', fontSize: '22px' }}>Automation & Workflows</h2>
        <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-secondary)' }}>
          Manage event-driven triggers and background scheduled tasks with plain English controls.
        </p>
      </div>

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
                    <button onClick={() => removeRule(rule.rule_id)} style={deleteBtn} title="Delete rule">
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

        {/* Right Column: User-Friendly Scheduler */}
        <div style={{ ...panelStyle, flex: 3 }} className="glass-panel">
          <div style={sectionHeader}>
            <CalendarClock size={18} color="var(--accent-purple)" />
            <h3 style={sectionTitle}>Schedule a Task</h3>
          </div>

          {/* User Friendly Schedule Form */}
          <form onSubmit={handleAddJob} style={formStyle} className="glass-panel">
            {errorMsg && <div style={errorBanner}>{errorMsg}</div>}
            
            {/* Task Name */}
            <div>
              <label style={labelStyle}>Task Name</label>
              <input 
                type="text" 
                placeholder="e.g. Daily Git Check, Sync Backup, Health Monitor" 
                value={taskName} 
                onChange={e => setTaskName(e.target.value)} 
                style={formInput}
              />
            </div>

            {/* Command to Execute */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <label style={labelStyle}>Command to Execute</label>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Terminal or shell action</span>
              </div>
              <input 
                type="text" 
                placeholder="e.g. git status, python sync.py, dir" 
                value={taskCmd} 
                onChange={e => setTaskCmd(e.target.value)} 
                style={formInput}
              />

              {/* Quick Preset Pills */}
              <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
                {commandPresets.map(preset => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => { setTaskCmd(preset.cmd); if (!taskName) setTaskName(preset.label); }}
                    style={presetPill}
                  >
                    <Terminal size={10} style={{ marginRight: '4px' }} />
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Frequency Dropdown */}
            <div>
              <label style={labelStyle}>How Often Should This Run?</label>
              <select 
                value={frequency} 
                onChange={e => setFrequency(e.target.value)} 
                style={formSelect}
              >
                <option value="every_5_min">⏱️ Every 5 Minutes</option>
                <option value="every_15_min">⏱️ Every 15 Minutes (Standard)</option>
                <option value="every_30_min">⏱️ Every 30 Minutes</option>
                <option value="hourly">⏱️ Every Hour</option>
                <option value="every_2_hours">⏱️ Every 2 Hours</option>
                <option value="every_6_hours">⏱️ Every 6 Hours</option>
                <option value="daily">📅 Daily (Once a day)</option>
                <option value="weekdays">💼 Weekdays (Monday through Friday)</option>
                <option value="weekly">📆 Weekly (Specific day of the week)</option>
                <option value="custom">⚙️ Custom Cron Expression (Advanced)</option>
              </select>
            </div>

            {/* Sub-selectors for Daily, Weekdays, and Weekly */}
            {(frequency === 'daily' || frequency === 'weekdays' || frequency === 'weekly') && (
              <div style={{ display: 'flex', gap: '10px' }}>
                {frequency === 'weekly' && (
                  <div style={{ flex: 1 }}>
                    <label style={labelStyle}>Day of Week</label>
                    <select
                      value={dayOfWeek}
                      onChange={e => setDayOfWeek(e.target.value)}
                      style={formSelect}
                    >
                      <option value="1">Monday</option>
                      <option value="2">Tuesday</option>
                      <option value="3">Wednesday</option>
                      <option value="4">Thursday</option>
                      <option value="5">Friday</option>
                      <option value="6">Saturday</option>
                      <option value="0">Sunday</option>
                    </select>
                  </div>
                )}
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Run Time (Local Time)</label>
                  <input
                    type="time"
                    value={timeOfDay}
                    onChange={e => setTimeOfDay(e.target.value)}
                    style={formInput}
                  />
                </div>
              </div>
            )}

            {/* Custom Cron Input (only shown when Custom is selected) */}
            {frequency === 'custom' && (
              <div>
                <label style={labelStyle}>Cron Expression (5 fields: min hour day month dow)</label>
                <input
                  type="text"
                  placeholder="e.g. 0 9 * * 1-5"
                  value={customCron}
                  onChange={e => setCustomCron(e.target.value)}
                  style={formInput}
                />
              </div>
            )}

            {/* Live Plain-English Schedule Preview Box */}
            <div style={previewBox}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Clock size={14} color="var(--accent-purple)" />
                <span style={{ fontSize: '12px', fontWeight: 600, color: '#fff' }}>
                  {humanSummary}
                </span>
              </div>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                Cron: {computedCron}
              </span>
            </div>
            
            <button type="submit" style={submitBtn}>
              <Zap size={14} color="#fff" style={{ marginRight: '6px' }} />
              Register Scheduled Task
            </button>
          </form>

          {/* Active Jobs List */}
          <div style={{ ...listScroll, marginTop: '12px' }} className="fade-scroll-container">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: '#fff' }}>Active Scheduled Tasks ({schedules.length})</span>
            </div>
            {schedules.length === 0 ? (
              <div style={emptyState}>No scheduled tasks currently active. Use the form above to schedule one.</div>
            ) : (
              schedules.map(job => (
                <div key={job.job_id} style={jobCard} className="glass-panel">
                  <div style={cardHeader}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={ruleIdText}>{job.job_id}</span>
                        <span style={scheduleBadge}>
                          {job.human_schedule || 'Scheduled'}
                        </span>
                      </div>
                      <div style={jobCmd}>Command: <code>{job.command}</code></div>
                      <div style={jobTime}>Next Local Run: <span style={{ color: 'var(--accent-cyan)' }}>{job.next_run_time_local}</span></div>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button 
                        onClick={() => handleRunNow(job.job_id)} 
                        style={runBtn}
                        disabled={runningJobId === job.job_id}
                        title="Run now immediately"
                      >
                        {runningJobId === job.job_id ? (
                          <span style={{ fontSize: '10px' }}>Running...</span>
                        ) : (
                          <>
                            <Play size={12} color="var(--accent-cyan)" style={{ marginRight: '4px' }} />
                            <span style={{ fontSize: '11px', color: 'var(--accent-cyan)' }}>Run Now</span>
                          </>
                        )}
                      </button>
                      <button onClick={() => removeScheduleJob(job.job_id)} style={deleteBtn} title="Remove schedule">
                        <Trash2 size={14} color="var(--accent-red)" />
                      </button>
                    </div>
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
  marginBottom: '14px',
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
  gap: '10px'
};

const emptyState: React.CSSProperties = {
  textAlign: 'center',
  padding: '24px 0',
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
  alignItems: 'flex-start',
  gap: '10px'
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
  padding: '6px 8px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'background-color 0.2s'
};

const runBtn: React.CSSProperties = {
  background: 'rgba(0, 240, 255, 0.1)',
  border: '1px solid rgba(0, 240, 255, 0.2)',
  borderRadius: '6px',
  padding: '4px 8px',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center',
  transition: 'all 0.2s'
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
  padding: '14px',
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
  background: 'rgba(25, 26, 35, 0.3)',
  border: '1px solid var(--border-glass)',
  borderRadius: '12px'
};

const labelStyle: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 500,
  color: 'var(--text-secondary)',
  marginBottom: '4px',
  display: 'block'
};

const formInput: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-glass)',
  borderRadius: '8px',
  padding: '8px 12px',
  color: '#fff',
  fontSize: '13px',
  outline: 'none'
};

const formSelect: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  background: '#13141f',
  border: '1px solid var(--border-glass)',
  borderRadius: '8px',
  padding: '8px 12px',
  color: '#fff',
  fontSize: '13px',
  outline: 'none',
  cursor: 'pointer'
};

const presetPill: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  borderRadius: '12px',
  padding: '2px 8px',
  fontSize: '10px',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
  display: 'flex',
  alignItems: 'center'
};

const previewBox: React.CSSProperties = {
  background: 'rgba(170, 59, 255, 0.08)',
  border: '1px solid rgba(170, 59, 255, 0.25)',
  borderRadius: '8px',
  padding: '8px 12px',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
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
  fontWeight: 600,
  cursor: 'pointer',
  marginTop: '4px',
  boxShadow: '0 4px 12px rgba(170, 59, 255, 0.3)'
};

const errorBanner: React.CSSProperties = {
  background: 'rgba(255, 30, 30, 0.1)',
  border: '1px solid rgba(255, 30, 30, 0.2)',
  borderRadius: '6px',
  padding: '6px 10px',
  fontSize: '11px',
  color: 'var(--accent-red)'
};

const jobCard: React.CSSProperties = {
  padding: '10px 12px',
  background: 'rgba(25, 26, 35, 0.4)',
  border: '1px solid var(--border-glass)',
  borderRadius: '10px'
};

const scheduleBadge: React.CSSProperties = {
  fontSize: '10px',
  fontWeight: 600,
  background: 'rgba(170, 59, 255, 0.15)',
  color: 'var(--accent-purple)',
  padding: '2px 6px',
  borderRadius: '4px'
};

const jobCmd: React.CSSProperties = {
  fontSize: '12px',
  marginTop: '4px',
  color: 'var(--text-primary)'
};

const jobTime: React.CSSProperties = {
  fontSize: '11px',
  color: 'var(--text-secondary)',
  marginTop: '2px'
};
