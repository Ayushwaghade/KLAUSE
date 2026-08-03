import { create } from 'zustand';
import type { Project, Task, Rule, ScheduleJob, ChatMessage } from '../types/api';

const API_BASE = 'http://127.0.0.1:8000';

interface StoreState {
  token: string | null;
  projects: Project[];
  activeProject: string | null;
  tasks: Task[];
  rules: Rule[];
  schedules: ScheduleJob[];
  messages: ChatMessage[];
  toasts: { id: string; message: string; type: 'info' | 'success' | 'warning' }[];
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  audioConnectionStatus: 'connected' | 'disconnected' | 'connecting';
  orbState: 'idle' | 'listening' | 'processing' | 'responding' | 'error';
  voiceInputActive: boolean;
  amplitude: number;
  
  // Actions
  setToken: (token: string) => void;
  initializeAuth: () => Promise<void>;
  fetchProjects: () => Promise<void>;
  fetchTasks: () => Promise<void>;
  fetchRules: () => Promise<void>;
  fetchSchedule: () => Promise<void>;
  openProject: (path: string) => Promise<void>;
  updateTaskStatus: (taskId: string, newStatus: Task['status']) => Promise<void>;
  addRule: (rule: Omit<Rule, 'enabled'>) => Promise<void>;
  removeRule: (ruleId: string) => Promise<void>;
  addScheduleCron: (jobId: string, command: string, cron: string) => Promise<void>;
  removeScheduleJob: (jobId: string) => Promise<void>;
  addMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  appendToLastMessage: (text: string) => void;
  clearMessages: () => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  addToast: (message: string, type?: 'info' | 'success' | 'warning') => void;
  removeToast: (id: string) => void;
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
  setAudioConnectionStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
  setOrbState: (state: StoreState['orbState']) => void;
  setVoiceInputActive: (active: boolean) => void;
  setAmplitude: (amplitude: number) => void;
}

export const useStore = create<StoreState>((set, get) => {
  const getHeaders = () => {
    const token = get().token;
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    };
  };

  return {
    token: null,
    projects: [],
    activeProject: null,
    tasks: [],
    rules: [],
    schedules: [],
    messages: [],
    toasts: [],
    connectionStatus: 'disconnected',
    audioConnectionStatus: 'disconnected',
    orbState: 'idle',
    voiceInputActive: false,
    amplitude: 0,

    setToken: (token) => set({ token }),

    initializeAuth: async () => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/token`);
        if (res.ok) {
          const data = await res.json();
          if (data.token) {
            set({ token: data.token });
            logger_log("Auth: Loaded startup authorization token.");
          }
        }
      } catch (err) {
        console.error("Auth: Failed to retrieve server authorization token:", err);
      }
    },

    fetchProjects: async () => {
      try {
        const res = await fetch(`${API_BASE}/api/projects`, { headers: getHeaders() });
        if (res.ok) {
          const data = await res.json();
          set({ projects: data });
        }
      } catch (err) {
        console.error("Fetch Projects Error:", err);
      }
    },

    fetchTasks: async () => {
      try {
        const res = await fetch(`${API_BASE}/api/tasks`, { headers: getHeaders() });
        if (res.ok) {
          const data = await res.json();
          set({ tasks: data });
        }
      } catch (err) {
        console.error("Fetch Tasks Error:", err);
      }
    },

    fetchRules: async () => {
      try {
        const res = await fetch(`${API_BASE}/api/rules`, { headers: getHeaders() });
        if (res.ok) {
          const data = await res.json();
          set({ rules: data });
        }
      } catch (err) {
        console.error("Fetch Rules Error:", err);
      }
    },

    fetchSchedule: async () => {
      try {
        const res = await fetch(`${API_BASE}/api/schedule`, { headers: getHeaders() });
        if (res.ok) {
          const data = await res.json();
          set({ schedules: data });
        }
      } catch (err) {
        console.error("Fetch Schedule Error:", err);
      }
    },

    openProject: async (path) => {
      try {
        const res = await fetch(`${API_BASE}/api/projects/open`, {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({ path })
        });
        if (res.ok) {
          const data = await res.json();
          set({ activeProject: data.active_project });
          await get().fetchProjects();
        }
      } catch (err) {
        console.error("Open Project Error:", err);
      }
    },

    updateTaskStatus: async (taskId, newStatus) => {
      // Optimistic update locally
      const originalTasks = get().tasks;
      set({
        tasks: originalTasks.map(t => t.id === taskId ? { ...t, status: newStatus } : t)
      });

      try {
        const res = await fetch(`${API_BASE}/api/tasks/batch-update`, {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify([{ task_id: taskId, status: newStatus }])
        });
        if (!res.ok) {
          // Rollback on fail
          set({ tasks: originalTasks });
        } else {
          get().addToast('Task status updated', 'success');
        }
      } catch (err) {
        console.error("Update Task Status Error:", err);
        set({ tasks: originalTasks });
      }
    },

    addRule: async (rule) => {
      try {
        const res = await fetch(`${API_BASE}/api/rules`, {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify(rule)
        });
        if (res.ok) {
          await get().fetchRules();
          get().addToast('Rule added', 'success');
        }
      } catch (err) {
        console.error("Add Rule Error:", err);
      }
    },

    removeRule: async (ruleId) => {
      try {
        const res = await fetch(`${API_BASE}/api/rules/${ruleId}`, {
          method: 'DELETE',
          headers: getHeaders()
        });
        if (res.ok) {
          await get().fetchRules();
          get().addToast('Rule removed', 'info');
        }
      } catch (err) {
        console.error("Remove Rule Error:", err);
      }
    },

    addScheduleCron: async (jobId, command, cron) => {
      try {
        const res = await fetch(`${API_BASE}/api/schedule/cron`, {
          method: 'POST',
          headers: getHeaders(),
          body: JSON.stringify({ job_id: jobId, command, cron_expression: cron })
        });
        if (res.ok) {
          await get().fetchSchedule();
          get().addToast('Cron job scheduled', 'success');
        }
      } catch (err) {
        console.error("Add Cron Schedule Error:", err);
      }
    },

    removeScheduleJob: async (jobId) => {
      try {
        const res = await fetch(`${API_BASE}/api/schedule/${jobId}`, {
          method: 'DELETE',
          headers: getHeaders()
        });
        if (res.ok) {
          await get().fetchSchedule();
          get().addToast('Schedule removed', 'info');
        }
      } catch (err) {
        console.error("Remove Schedule Job Error:", err);
      }
    },

    addMessage: (msg) => {
      const fullMsg: ChatMessage = {
        ...msg,
        id: Math.random().toString(36).substring(7),
        timestamp: new Date().toLocaleTimeString()
      };
      set(state => ({ messages: [...state.messages, fullMsg] }));
    },

    appendToLastMessage: (text) => {
      set(state => {
        const msgs = [...state.messages];
        if (msgs.length > 0) {
          const last = { ...msgs[msgs.length - 1] };
          last.text = (last.text || '') + text;
          msgs[msgs.length - 1] = last;
        }
        return { messages: msgs };
      });
    },

    clearMessages: () => set({ messages: [] }),

    updateMessage: (id, updates) => {
      set(state => ({
        messages: state.messages.map(m => m.id === id ? { ...m, ...updates } : m)
      }));
    },

    addToast: (message, type = 'info') => {
      const id = Math.random().toString(36).substring(7);
      set(state => ({
        toasts: [...state.toasts.slice(-2), { id, message, type }]
      }));
    },
    removeToast: (id) => {
      set(state => ({
        toasts: state.toasts.filter(t => t.id !== id)
      }));
    },

    setConnectionStatus: (status) => set({ connectionStatus: status }),
    setAudioConnectionStatus: (status) => set({ audioConnectionStatus: status }),
    setOrbState: (state) => set({ orbState: state }),
    setVoiceInputActive: (active) => set({ voiceInputActive: active }),
    setAmplitude: (amplitude) => set({ amplitude })
  };
});

function logger_log(msg: string) {
  console.log(`[Store] ${msg}`);
}
