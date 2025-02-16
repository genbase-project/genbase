// stores/chatStore.ts
import { create } from 'zustand';
import { Message } from '@/components/Chat';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;  // Added error state
  currentModuleId: string | null;
  currentWorkflow: string | null;
  currentSession: string | null;
  setCurrentContext: (moduleId: string, workflow: string, sessionId: string) => void;
  sendResponse: (id: string, value: string) => Promise<void>;
  sendMessage: (text: string) => Promise<void>;  // New function
  refreshChat: () => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,
  currentModuleId: null,
  currentWorkflow: null,
  currentSession: null,

  setCurrentContext: (moduleId, workflow, sessionId) => {
    set({ currentModuleId: moduleId, currentWorkflow: workflow, currentSession: sessionId });
  },

  sendMessage: async (text: string) => {
    const { currentModuleId, currentWorkflow, currentSession } = get();
    if (!currentModuleId || !currentWorkflow) {
      set({ error: 'No active context' });
      return;
    }

    set({ isLoading: true, error: null });
    try {
      const url = new URL(`${ENGINE_BASE_URL}/chat/${currentModuleId}/execute`);
      const response = await fetchWithAuth(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section: currentWorkflow,
          input: text,
          session_id: currentSession
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to send message');
      }

      // Refresh chat after sending message
      await get().refreshChat();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      set({ error: errorMessage });
      console.error('Error sending message:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  sendResponse: async (id: string, value: string) => {
    const { currentModuleId, currentWorkflow, currentSession } = get();
    if (!currentModuleId || !currentWorkflow) {
      set({ error: 'No active context' });
      return;
    }

    set({ isLoading: true, error: null });
    try {
      const response = `<giml><responses><response id="${id}" value="${value}"/></responses></giml>`;
      
      const url = new URL(`${ENGINE_BASE_URL}/chat/${currentModuleId}/execute`);
      const result = await fetchWithAuth(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section: currentWorkflow,
          input: response,
          session_id: currentSession
        })
      });

      if (!result.ok) {
        const errorData = await result.json();
        throw new Error(errorData.detail || 'Failed to send response');
      }

      // Refresh chat after sending response
      await get().refreshChat();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send response';
      set({ error: errorMessage });
      console.error('Error sending response:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  refreshChat: async () => {
    const { currentModuleId, currentWorkflow, currentSession } = get();
    if (!currentModuleId || !currentWorkflow || !currentSession) {
      set({ error: 'No active context' });
      return;
    }

    try {
      const url = new URL(`${ENGINE_BASE_URL}/chat/${currentModuleId}/workflow/${currentWorkflow}/history`);
      url.searchParams.append('session_id', currentSession);
      
      const response = await fetchWithAuth(url.toString());
      if (!response.ok) {
        throw new Error('Failed to fetch chat history');
      }

      const data = await response.json();
      set({ messages: data.history || [] });
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh chat';
      set({ error: errorMessage });
      console.error('Error refreshing chat:', error);
    }
  }
}));