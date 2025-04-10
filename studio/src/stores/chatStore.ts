// stores/chatStore.ts
import { create } from 'zustand';
import { Message } from '@/components/ChatContainer'; // Adjust path if needed
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config'; // Adjust path if needed

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  currentModuleId: string | null;
  currentProfile: string | null;
  currentSession: string | null;
  setCurrentContext: (moduleId: string, profile: string, sessionId: string) => void;
  sendResponse: (id: string, value: string) => Promise<void>; // Functionality needs review
  sendMessage: (text: string) => Promise<void>;
  refreshChat: () => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,
  currentModuleId: null,
  currentProfile: null,
  currentSession: null,

  setCurrentContext: (moduleId, profile, sessionId) => {
    set({
      currentModuleId: moduleId,
      currentProfile: profile,
      currentSession: sessionId,
      messages: [], // Clear messages on context change
      error: null,
      isLoading: false,
    });
    get().refreshChat(); // Fetch history for the new context
  },

  sendMessage: async (text: string) => {
    const { currentModuleId, currentProfile, currentSession } = get();
    if (!currentModuleId || !currentProfile || !currentSession) {
      set({ error: 'Chat context not fully set.', isLoading: false });
      console.error("sendMessage failed: context incomplete", { currentModuleId, currentProfile, currentSession });
      return;
    }

    set({ isLoading: true, error: null });
    try {
      const url = new URL(`${ENGINE_BASE_URL}/chat/${currentModuleId}/execute`);
      const response = await fetchWithAuth(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: currentProfile,
          input: text,
          session_id: currentSession
        })
      });

      if (!response.ok) {
        let errorDetail = `Request failed with status ${response.status}`;
        try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch {}
        throw new Error(errorDetail);
      }

      // Refresh needed to get agent response & state updates
      await get().refreshChat();

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      set({ error: errorMessage });
      console.error('Error sending message:', error);
    } finally {
      set({ isLoading: false });
    }
  },


  sendResponse: async (id: string, value: string) => {
    console.warn("sendResponse functionality requires redesign for the current agent interaction model.");
    const { currentModuleId, currentProfile, currentSession } = get();
    if (!currentModuleId || !currentProfile || !currentSession) {
      set({ error: 'Chat context not fully set.', isLoading: false });
      console.error("sendResponse failed: context incomplete");
      return;
    }

    set({ isLoading: true, error: null });
    try {
      // The actual format depends entirely on how the backend agent is designed to receive this.
      const inputPayload = `User input for ${id}: ${value}`;

      const url = new URL(`${ENGINE_BASE_URL}/chat/${currentModuleId}/execute`);
      const result = await fetchWithAuth(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: currentProfile,
          input: inputPayload,
          session_id: currentSession
        })
      });

      if (!result.ok) {
        let errorDetail = `Request failed with status ${result.status}`;
        try { const errorData = await result.json(); errorDetail = errorData.detail || errorDetail; } catch {}
        throw new Error(errorDetail);
      }

      await get().refreshChat();

    } catch (error) {
       const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
       set({ error: errorMessage });
       console.error('Error sending response:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  refreshChat: async () => {
    const { currentModuleId, currentProfile, currentSession } = get();
    if (!currentModuleId || !currentProfile || !currentSession) {
      // console.log("Skipping refresh: context not fully set.");
      return; // Don't attempt refresh if context isn't ready
    }

    set({ isLoading: true, error: null });
    try {
      const url = new URL(`${ENGINE_BASE_URL}/chat/${currentModuleId}/profile/${currentProfile}/history`);
      url.searchParams.append('session_id', currentSession);

      const response = await fetchWithAuth(url.toString());
      if (!response.ok) {
          let errorDetail = `Request failed with status ${response.status}`;
          try { const errorData = await response.json(); errorDetail = errorData.detail || errorDetail; } catch {}
          throw new Error(errorDetail);
      }

      const data = await response.json();
      const history = Array.isArray(data?.history) ? data.history : [];
      set({ messages: history, error: null });

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh chat';
      set({ error: errorMessage, messages: [] }); // Clear messages on refresh error
      console.error('Error refreshing chat:', error);
    } finally {
        set({ isLoading: false });
    }
  }
}));