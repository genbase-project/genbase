import { create } from 'zustand';
import { Module } from '../components/TreeView';

interface ModuleState {
  selectedModuleId: string | null;
  selectedModule: Module | null;
  setSelectedModule: (module: Module | null) => void;
}

export const useModuleStore = create<ModuleState>((set) => ({
  selectedModuleId: null,
  selectedModule: null,
  setSelectedModule: (module) => {
    console.log('Setting selected module:', module);
    set({ 
      selectedModuleId: module?.module_id || null,
      selectedModule: module 
    })},
}));