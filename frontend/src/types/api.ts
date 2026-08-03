export interface Project {
  id: string;
  name: string;
  path: string;
  description: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string;
  status: 'pending' | 'in_progress' | 'done';
  priority: 'low' | 'medium' | 'high';
}

export interface Rule {
  rule_id: string;
  event_type: string;
  action_type: 'tool_call' | 'trigger_react';
  action_payload: Record<string, any>;
  filter_pattern?: string;
  enabled: boolean;
}

export interface ScheduleJob {
  job_id: string;
  command: string;
  trigger: string;
  next_run_time_local: string;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'klause' | 'system';
  timestamp: string;
  text?: string;
  type?: 'thought' | 'observation' | 'final' | 'prompt' | 'confirmation_request';
  step?: number;
  thought?: string;
  action?: string;
  params?: Record<string, any>;
  observation?: {
    success: boolean;
    result?: string;
    error?: string;
  };
  streaming?: boolean;
  request_id?: string;
  confirmation_status?: 'pending' | 'approved' | 'denied';
}
