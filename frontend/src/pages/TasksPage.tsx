import React, { useEffect, useState, useMemo } from 'react';
import { useStore } from '../store/useStore';
import type { Task } from '../types/api';
import { ListTodo, Play, CheckCircle, Plus, Trash2, RotateCw, Clock, Terminal, CheckCircle2 } from 'lucide-react';

export const TasksPage: React.FC = () => {
  const tasks = useStore(state => state.tasks);
  const fetchTasks = useStore(state => state.fetchTasks);
  const updateTaskStatus = useStore(state => state.updateTaskStatus);
  const createTask = useStore(state => state.createTask);
  const deleteTask = useStore(state => state.deleteTask);
  const runScheduleJob = useStore(state => state.runScheduleJob);
  const activeProject = useStore(state => state.activeProject);

  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<'all' | 'scheduled' | 'execution_log' | 'manual'>('all');
  const [showNewTaskModal, setShowNewTaskModal] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState('');
  const [newTaskDesc, setNewTaskDesc] = useState('');
  const [newTaskPriority, setNewTaskPriority] = useState<Task['priority']>('medium');
  const [runningJobId, setRunningJobId] = useState<string | null>(null);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const columns: Array<{ title: string; status: Task['status']; icon: React.ReactNode; color: string }> = [
    { title: 'Pending', status: 'pending', icon: <ListTodo size={16} color="var(--text-secondary)" />, color: 'var(--text-secondary)' },
    { title: 'In Progress', status: 'in_progress', icon: <Play size={16} color="var(--accent-cyan)" />, color: 'var(--accent-cyan)' },
    { title: 'Completed', status: 'done', icon: <CheckCircle size={16} color="var(--accent-purple)" />, color: 'var(--accent-purple)' }
  ];

  // Drag and Drop native handlers
  const handleDragStart = (e: React.DragEvent, taskId: string) => {
    e.dataTransfer.setData('text/plain', taskId);
  };

  const handleDragOver = (e: React.DragEvent, columnStatus: string) => {
    e.preventDefault();
    setDragOverColumn(columnStatus);
  };

  const handleDrop = async (e: React.DragEvent, targetStatus: Task['status']) => {
    e.preventDefault();
    setDragOverColumn(null);
    const taskId = e.dataTransfer.getData('text/plain');
    if (taskId) {
      await updateTaskStatus(taskId, targetStatus);
    }
  };

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTaskTitle.trim()) return;
    await createTask({
      title: newTaskTitle.trim(),
      description: newTaskDesc.trim(),
      priority: newTaskPriority,
      status: 'pending',
      project_id: activeProject || 'global'
    });
    setNewTaskTitle('');
    setNewTaskDesc('');
    setShowNewTaskModal(false);
  };

  const handleRunNow = async (jobId: string) => {
    setRunningJobId(jobId);
    await runScheduleJob(jobId);
    setTimeout(() => setRunningJobId(null), 1200);
  };

  const getPriorityColor = (priority: Task['priority']) => {
    if (priority === 'high') return 'var(--accent-red)';
    if (priority === 'medium') return 'var(--accent-gold)';
    return 'var(--accent-cyan)';
  };

  // Filter tasks based on selected tab
  const filteredTasks = useMemo(() => {
    if (filterType === 'all') return tasks;
    if (filterType === 'scheduled') return tasks.filter(t => t.type === 'scheduled');
    if (filterType === 'execution_log') return tasks.filter(t => t.type === 'execution_log');
    if (filterType === 'manual') return tasks.filter(t => !t.type || t.type === 'manual');
    return tasks;
  }, [tasks, filterType]);

  const scheduledCount = tasks.filter(t => t.type === 'scheduled').length;
  const executionCount = tasks.filter(t => t.type === 'execution_log').length;
  const manualCount = tasks.filter(t => !t.type || t.type === 'manual').length;

  return (
    <div style={containerStyle} className="animate-slide-in">
      {/* Top Header */}
      <div style={headerStyle}>
        <div>
          <h2 style={{ margin: '0 0 4px 0', fontSize: '22px' }}>Kanban Task Board</h2>
          <p style={{ margin: '0', fontSize: '13px', color: 'var(--text-secondary)' }}>
            Track background scheduled tasks, code implementations, and executions for {activeProject ? activeProject.split(/[\\/]/).pop() : 'active workspace'}.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px' }}>
          <button 
            onClick={() => fetchTasks()} 
            style={actionBtnSecondary} 
            title="Refresh tasks"
          >
            <RotateCw size={14} color="var(--text-secondary)" />
          </button>
          <button 
            onClick={() => setShowNewTaskModal(prev => !prev)} 
            style={actionBtnPrimary}
          >
            <Plus size={14} color="#fff" style={{ marginRight: '6px' }} />
            New Task
          </button>
        </div>
      </div>

      {/* Filter Tabs Bar */}
      <div style={filterBar}>
        <button
          onClick={() => setFilterType('all')}
          style={{ ...filterPill, ...(filterType === 'all' ? activeFilterPill : {}) }}
        >
          All Tasks ({tasks.length})
        </button>
        <button
          onClick={() => setFilterType('scheduled')}
          style={{ ...filterPill, ...(filterType === 'scheduled' ? activeFilterPill : {}) }}
        >
          ⏰ Scheduled Tasks ({scheduledCount})
        </button>
        <button
          onClick={() => setFilterType('execution_log')}
          style={{ ...filterPill, ...(filterType === 'execution_log' ? activeFilterPill : {}) }}
        >
          ✔ Executed Runs ({executionCount})
        </button>
        <button
          onClick={() => setFilterType('manual')}
          style={{ ...filterPill, ...(filterType === 'manual' ? activeFilterPill : {}) }}
        >
          📋 Manual Tasks ({manualCount})
        </button>
      </div>

      {/* Inline New Task Drawer */}
      {showNewTaskModal && (
        <form onSubmit={handleCreateTask} style={newTaskDrawer} className="glass-panel">
          <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#fff' }}>Create New Kanban Task</h4>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Task Title (e.g. Implement user authentication flow)"
              value={newTaskTitle}
              onChange={e => setNewTaskTitle(e.target.value)}
              style={{ ...drawerInput, flex: 2, minWidth: '200px' }}
              autoFocus
            />
            <input
              type="text"
              placeholder="Description (optional)"
              value={newTaskDesc}
              onChange={e => setNewTaskDesc(e.target.value)}
              style={{ ...drawerInput, flex: 3, minWidth: '250px' }}
            />
            <select
              value={newTaskPriority}
              onChange={e => setNewTaskPriority(e.target.value as Task['priority'])}
              style={drawerSelect}
            >
              <option value="low">Low Priority</option>
              <option value="medium">Medium Priority</option>
              <option value="high">High Priority</option>
            </select>
            <button type="submit" style={drawerSubmitBtn}>Add to Board</button>
            <button type="button" onClick={() => setShowNewTaskModal(false)} style={drawerCancelBtn}>Cancel</button>
          </div>
        </form>
      )}

      {/* Grid columns */}
      <div style={boardGrid}>
        {columns.map(col => {
          const colTasks = filteredTasks.filter(t => t.status === col.status);
          const isOver = dragOverColumn === col.status;

          return (
            <div
              key={col.status}
              onDragOver={(e) => handleDragOver(e, col.status)}
              onDragLeave={() => setDragOverColumn(null)}
              onDrop={(e) => handleDrop(e, col.status)}
              style={{
                ...columnStyle,
                borderColor: isOver ? col.color : 'var(--border-glass)'
              }}
              className="glass-panel"
            >
              <div style={columnHeader}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {col.icon}
                  <span style={columnTitle}>{col.title}</span>
                </div>
                <span style={taskCountBadge}>{colTasks.length}</span>
              </div>

              <div style={cardsContainer} className="fade-scroll-container">
                {colTasks.length === 0 ? (
                  <div style={emptyState}>
                    {col.status === 'pending' ? 'No pending tasks' : col.status === 'in_progress' ? 'No tasks in progress' : 'No completed tasks yet'}
                  </div>
                ) : (
                  colTasks.map(task => {
                    const isScheduled = task.type === 'scheduled';
                    const isExecutionLog = task.type === 'execution_log';

                    return (
                      <div
                        key={task.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, task.id)}
                        style={{
                          ...cardStyle,
                          borderLeft: isScheduled 
                            ? '3px solid var(--accent-purple)' 
                            : isExecutionLog 
                              ? '3px solid var(--accent-cyan)' 
                              : `1px solid var(--border-glass)`
                        }}
                        className="glass-panel"
                      >
                        <div style={cardHeader}>
                          {/* Badges */}
                          <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                            {isScheduled ? (
                              <span style={scheduledBadge}>
                                <Clock size={10} style={{ marginRight: '3px' }} />
                                SCHEDULED
                              </span>
                            ) : isExecutionLog ? (
                              <span style={logBadge}>
                                <CheckCircle2 size={10} style={{ marginRight: '3px' }} />
                                RUN RECORD
                              </span>
                            ) : (
                              <span style={{
                                ...priorityBadge,
                                backgroundColor: `${getPriorityColor(task.priority)}15`,
                                color: getPriorityColor(task.priority)
                              }}>
                                {task.priority.toUpperCase()}
                              </span>
                            )}
                          </div>

                          {/* Card Top Actions */}
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            {isScheduled && task.job_id && (
                              <button
                                onClick={(e) => { e.stopPropagation(); handleRunNow(task.job_id!); }}
                                style={cardRunBtn}
                                disabled={runningJobId === task.job_id}
                                title="Run now immediately"
                              >
                                <Play size={10} color="var(--accent-cyan)" />
                                <span style={{ fontSize: '10px', color: 'var(--accent-cyan)' }}>
                                  {runningJobId === task.job_id ? 'Running' : 'Run'}
                                </span>
                              </button>
                            )}
                            <button
                              onClick={(e) => { e.stopPropagation(); deleteTask(task.id); }}
                              style={cardDeleteBtn}
                              title="Delete task"
                            >
                              <Trash2 size={12} color="var(--text-muted)" />
                            </button>
                          </div>
                        </div>

                        {/* Title */}
                        <h4 style={cardTitle}>{task.title}</h4>

                        {/* Scheduled Task Details */}
                        {isScheduled && (
                          <div style={scheduledDetailsBox}>
                            {task.command && (
                              <div style={detailRow}>
                                <Terminal size={11} color="var(--accent-cyan)" style={{ flexShrink: 0 }} />
                                <code style={cmdCode}>{task.command}</code>
                              </div>
                            )}
                            {task.next_run && (
                              <div style={detailRow}>
                                <Clock size={11} color="var(--accent-purple)" style={{ flexShrink: 0 }} />
                                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                                  Next run: <strong style={{ color: '#fff' }}>{task.next_run}</strong>
                                </span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Description */}
                        {task.description && !isScheduled && (
                          <p style={cardDesc}>{task.description}</p>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// --- Styles ---
const containerStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  width: '100%',
  gap: '12px'
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
};

const actionBtnPrimary: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '8px 14px',
  background: 'linear-gradient(135deg, var(--accent-purple) 0%, #aa3bff 100%)',
  border: 'none',
  borderRadius: '8px',
  color: '#fff',
  fontSize: '12px',
  fontWeight: 600,
  cursor: 'pointer',
  boxShadow: '0 4px 12px rgba(170, 59, 255, 0.25)'
};

const actionBtnSecondary: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '8px 12px',
  background: 'rgba(255, 255, 255, 0.05)',
  border: '1px solid var(--border-glass)',
  borderRadius: '8px',
  cursor: 'pointer'
};

const filterBar: React.CSSProperties = {
  display: 'flex',
  gap: '8px',
  overflowX: 'auto',
  paddingBottom: '2px'
};

const filterPill: React.CSSProperties = {
  background: 'rgba(25, 26, 35, 0.4)',
  border: '1px solid var(--border-glass)',
  borderRadius: '20px',
  padding: '4px 12px',
  fontSize: '11px',
  color: 'var(--text-secondary)',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
  transition: 'all 0.2s'
};

const activeFilterPill: React.CSSProperties = {
  background: 'rgba(170, 59, 255, 0.15)',
  borderColor: 'var(--accent-purple)',
  color: '#fff',
  fontWeight: 600
};

const newTaskDrawer: React.CSSProperties = {
  padding: '12px 16px',
  borderRadius: '12px',
  border: '1px solid var(--border-glass)',
  background: 'rgba(25, 26, 35, 0.6)'
};

const drawerInput: React.CSSProperties = {
  background: 'var(--bg-secondary)',
  border: '1px solid var(--border-glass)',
  borderRadius: '8px',
  padding: '8px 12px',
  color: '#fff',
  fontSize: '12px',
  outline: 'none'
};

const drawerSelect: React.CSSProperties = {
  background: '#13141f',
  border: '1px solid var(--border-glass)',
  borderRadius: '8px',
  padding: '8px 12px',
  color: '#fff',
  fontSize: '12px',
  outline: 'none',
  cursor: 'pointer'
};

const drawerSubmitBtn: React.CSSProperties = {
  background: 'var(--accent-purple)',
  border: 'none',
  borderRadius: '8px',
  padding: '8px 14px',
  color: '#fff',
  fontSize: '12px',
  fontWeight: 600,
  cursor: 'pointer'
};

const drawerCancelBtn: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid var(--border-glass)',
  borderRadius: '8px',
  padding: '8px 14px',
  color: 'var(--text-secondary)',
  fontSize: '12px',
  cursor: 'pointer'
};

const boardGrid: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(3, 1fr)',
  gap: '16px',
  flex: 1,
  minHeight: 0
};

const columnStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  padding: '14px',
  minHeight: 0,
  transition: 'border-color 0.2s',
  borderRadius: '14px'
};

const columnHeader: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '12px'
};

const columnTitle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 600,
  color: '#fff'
};

const taskCountBadge: React.CSSProperties = {
  fontSize: '11px',
  background: 'var(--bg-secondary)',
  padding: '2px 8px',
  borderRadius: '10px',
  color: 'var(--text-secondary)'
};

const cardsContainer: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '10px',
  flex: 1,
  overflowY: 'auto'
};

const cardStyle: React.CSSProperties = {
  padding: '12px',
  cursor: 'grab',
  background: 'rgba(25, 26, 35, 0.45)',
  display: 'flex',
  flexDirection: 'column',
  gap: '8px',
  border: '1px solid var(--border-glass)',
  borderRadius: '12px',
  transition: 'transform 0.15s, box-shadow 0.15s'
};

const cardHeader: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
};

const priorityBadge: React.CSSProperties = {
  fontSize: '9px',
  fontWeight: 600,
  padding: '2px 6px',
  borderRadius: '4px',
  letterSpacing: '0.5px'
};

const scheduledBadge: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  fontSize: '9px',
  fontWeight: 700,
  padding: '2px 6px',
  borderRadius: '4px',
  background: 'rgba(170, 59, 255, 0.2)',
  color: '#c977ff',
  letterSpacing: '0.5px'
};

const logBadge: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  fontSize: '9px',
  fontWeight: 700,
  padding: '2px 6px',
  borderRadius: '4px',
  background: 'rgba(0, 240, 255, 0.15)',
  color: 'var(--accent-cyan)',
  letterSpacing: '0.5px'
};

const cardRunBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '4px',
  background: 'rgba(0, 240, 255, 0.1)',
  border: '1px solid rgba(0, 240, 255, 0.25)',
  borderRadius: '4px',
  padding: '2px 6px',
  cursor: 'pointer'
};

const cardDeleteBtn: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'transparent',
  border: 'none',
  padding: '3px',
  borderRadius: '4px',
  cursor: 'pointer'
};

const cardTitle: React.CSSProperties = {
  margin: '0',
  fontSize: '13px',
  fontWeight: 600,
  color: '#fff',
  lineHeight: 1.3
};

const cardDesc: React.CSSProperties = {
  margin: '0',
  fontSize: '12px',
  color: 'var(--text-secondary)',
  lineHeight: 1.4
};

const scheduledDetailsBox: React.CSSProperties = {
  background: 'rgba(0, 0, 0, 0.25)',
  border: '1px solid rgba(255, 255, 255, 0.05)',
  borderRadius: '6px',
  padding: '6px 8px',
  display: 'flex',
  flexDirection: 'column',
  gap: '4px'
};

const detailRow: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px'
};

const cmdCode: React.CSSProperties = {
  fontSize: '11px',
  fontFamily: 'var(--font-mono)',
  color: 'var(--accent-cyan)',
  background: 'rgba(0, 240, 255, 0.05)',
  padding: '1px 4px',
  borderRadius: '3px',
  wordBreak: 'break-all'
};

const emptyState: React.CSSProperties = {
  textAlign: 'center',
  padding: '32px 0',
  fontSize: '13px',
  color: 'var(--text-muted)'
};
