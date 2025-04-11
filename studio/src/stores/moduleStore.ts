import { create } from 'zustand';
import { Module } from '../components/TreeView'; // Adjust path

interface ModuleStoreState {
  selectedModuleId: string | null;
  selectedModule: Module | null;
  setSelectedModule: (module: Module | null) => void;
  clearSelectedModule: () => void; // Add this
}

export const useModuleStore = create<ModuleStoreState>((set) => ({
  selectedModuleId: null,
  selectedModule: null,
  setSelectedModule: (module) => set({
    selectedModule: module,
    selectedModuleId: module ? `module-${module.module_id}` : null
  }),
  clearSelectedModule: () => set({ 
    selectedModule: null,
    selectedModuleId: null,
  }),
}));