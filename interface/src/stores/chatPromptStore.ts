import { create } from 'zustand'

interface ChatPromptState {
  inputValue: string
  activePromptIndex: number
  setInputValue: (value: string) => void
  setActivePromptIndex: (index: number) => void
}

export const useChatPromptStore = create<ChatPromptState>((set) => ({
  inputValue: '',
  activePromptIndex: -1,
  setInputValue: (value) => set({ inputValue: value }),
  setActivePromptIndex: (index) => set({ activePromptIndex: index }),
}))
