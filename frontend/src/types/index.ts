export interface IntegrationStatusResponse {
  provider: string;
  is_connected: boolean;
  status_label: string;
}

export interface ChatSessionCreate {
  title?: string;
}

export interface MessageResponse {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  meta_data?: Record<string, any>;
  created_at: string;
}

export interface ChatSessionResponse {
  id: string;
  user_id: string;
  title?: string;
  created_at: string;
  updated_at: string;
  messages: MessageResponse[];
}
