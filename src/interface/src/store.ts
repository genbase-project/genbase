import { create } from 'zustand';
import { RuntimeModule } from './components/TreeView';

interface RuntimeModuleState {
  selectedModuleId: string | null;
  selectedModule: RuntimeModule | null;
  setSelectedModule: (module: RuntimeModule | null) => void;
}

export const useRuntimeModuleStore = create<RuntimeModuleState>((set) => ({
  selectedModuleId: null,
  selectedModule: null,
  setSelectedModule: (module) => {
    console.log('Setting selected module:', module);
    set({ 
      selectedModuleId: module?.id || null,
      selectedModule: module 
    })},
}));