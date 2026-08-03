import React, { useEffect, useState } from 'react';
import { useStore } from '../store/useStore';
import type { Task } from '../types/api';
import { ListTodo, Play, CheckCircle } from 'lucide-react';

export const TasksPage: React.FC = () => {
  const tasks = useStore(state => state.tasks);
  const fetchTasks = useStore(state => state.fetchTasks);
  const updateTaskStatus = useStore(state => state.updateTaskStatus);
  const activeProject = useStore(state => state.activeProject);

  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);

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

  const getPriorityColor = (priority: Task['priority']) => {
    if (priority === 'high') return 'var(--accent-red)';
    if (priority === 'medium') return 'var(--accent-gold)';
    return 'var(--accent-cyan)';
  };

  return (
    <div style={containerStyle} className="animate-slide-in">
      <div style={headerStyle}>
        <div>
          <h2 style={{ margin: '0 0 4px 0', fontSize: '22px' }}>Kanban Task Board</h2>
          <p style={{ margin: '0', fontSize: '13px', color: 'var(--text-secondary)' }}>
            Manage and track code implementations for {activeProject ? activeProject.split(/[\\/]/).pop() : 'active workspace'}.
          </p>
        </div>
      </div>

      {/* Grid columns */}
      <div style={boardGrid}>
        {columns.map(col => {
          const colTasks = tasks.filter(t => t.status === col.status);
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
                  <div style={emptyState}>No tasks</div>
                ) : (
                  colTasks.map(task => (
                    <div
                      key={task.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, task.id)}
                      style={cardStyle}
                      className="glass-panel"
                    >
                      <div style={cardHeader}>
                        <span style={{
                          ...priorityBadge,
                          backgroundColor: `${getPriorityColor(task.priority)}15`,
                          color: getPriorityColor(task.priority)
                        }}>
                          {task.priority.toUpperCase()}
                        </span>
                      </div>
                      <h4 style={cardTitle}>{task.title}</h4>
                      {task.description && (
                        <p style={cardDesc}>{task.description}</p>
                      )}
                    </div>
                  ))
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
  gap: '16px'
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center'
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
  padding: '16px',
  minHeight: 0,
  transition: 'border-color 0.2s'
};

const columnHeader: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: '16px'
};

const columnTitle: React.CSSProperties = {
  fontSize: '15px',
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
  gap: '12px',
  flex: 1,
  overflowY: 'auto'
};

const cardStyle: React.CSSProperties = {
  padding: '12px',
  cursor: 'grab',
  background: 'rgba(25, 26, 35, 0.4)',
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

const cardTitle: React.CSSProperties = {
  margin: '0',
  fontSize: '14px',
  fontWeight: 500,
  color: '#fff'
};

const cardDesc: React.CSSProperties = {
  margin: '0',
  fontSize: '12px',
  color: 'var(--text-secondary)',
  lineHeight: 1.4
};

const emptyState: React.CSSProperties = {
  textAlign: 'center',
  padding: '32px 0',
  fontSize: '13px',
  color: 'var(--text-muted)'
};
