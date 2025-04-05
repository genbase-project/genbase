import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { fetchWithAuth, ENGINE_BASE_URL } from '@/config'; // Adjust path if needed

// Interface matching the API response
export interface Project {
  id: string;
  name: string;
  created_at: string; // Keep as string, can format later if needed
}

interface ProjectState {
  projects: Project[];
  selectedProjectId: string | null;
  isLoading: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  setSelectedProject: (projectId: string | null) => void;
  createProject: (name: string) => Promise<Project | null>;
  addProjectToList: (project: Project) => void; // Helper
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      projects: [],
      selectedProjectId: null,
      isLoading: false,
      error: null,

      fetchProjects: async () => {
        if (get().isLoading) return; // Prevent concurrent fetches
        set({ isLoading: true, error: null });
        try {
          const response = await fetchWithAuth(`${ENGINE_BASE_URL}/project`);
          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: `Failed to fetch projects (${response.status})` }));
            throw new Error(errorData.detail || `Failed to fetch projects (${response.status})`);
          }
          const fetchedProjects: Project[] = await response.json();
          set({ projects: fetchedProjects, isLoading: false });

          // Auto-select logic: if a project was selected, keep it.
          // If not, or if the selected one is gone, select the first one if available.
          const currentSelectedId = get().selectedProjectId;
          const selectedProjectExists = fetchedProjects.some(p => p.id === currentSelectedId);

          if (!currentSelectedId || !selectedProjectExists) {
            if (fetchedProjects.length > 0) {
              get().setSelectedProject(fetchedProjects[0].id);
            } else {
              get().setSelectedProject(null); // No projects available
            }
          } else {
            // Ensure the selected ID is still valid after fetch, might be redundant
            get().setSelectedProject(currentSelectedId);
          }

        } catch (error: any) {
          console.error('Error fetching projects:', error);
          set({
            error: error.message || 'An unknown error occurred while fetching projects.',
            isLoading: false,
            projects: [], // Clear projects on error
            selectedProjectId: null // Clear selection on error
           });
        }
      },

      setSelectedProject: (projectId: string | null) => {
        set({ selectedProjectId: projectId });
        // Note: We trigger module refetching in the ModuleExplorer component
        // based on changes to selectedProjectId
      },

      createProject: async (name: string): Promise<Project | null> => {
        if (!name.trim()) {
          set({ error: "Project name cannot be empty." });
          return null;
        }
        set({ isLoading: true, error: null }); // Indicate loading for creation
        try {
          const response = await fetchWithAuth(`${ENGINE_BASE_URL}/project`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name.trim() }),
          });

          if (!response.ok) {
             const errorData = await response.json().catch(() => ({ detail: `Failed to create project (${response.status})` }));
             throw new Error(errorData.detail || `Failed to create project (${response.status})`);
          }

          const newProject: Project = await response.json();
          get().addProjectToList(newProject); // Add to local state
          get().setSelectedProject(newProject.id); // Auto-select the new project
          set({ isLoading: false });
          return newProject;

        } catch (error: any) {
          console.error('Error creating project:', error);
          set({ error: error.message || 'An unknown error occurred while creating the project.', isLoading: false });
          return null;
        }
      },

      // Helper to update the list without a full refetch after creation
      addProjectToList: (project: Project) => {
         set(state => ({ projects: [...state.projects, project] }));
      },
    }),
    {
      name: 'project-storage', // Unique name for local storage key
      storage: createJSONStorage(() => localStorage), // Use local storage
      partialize: (state) => ({ selectedProjectId: state.selectedProjectId }), // Only persist selectedProjectId
    }
  )
);