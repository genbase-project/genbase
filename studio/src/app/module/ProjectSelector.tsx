import React, { useState, useEffect } from 'react';
import { useProjectStore, Project } from '@/stores/projectStore'; 
import { useToast } from '@/hooks/use-toast'; 
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectSeparator,
  SelectGroup,
  SelectLabel
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PlusCircle, Loader2, ChevronDown } from "lucide-react"; 

export const ProjectSelector: React.FC = () => {
  const {
    projects,
    selectedProjectId,
    isLoading: isStoreLoading,
    error,
    fetchProjects,
    setSelectedProject,
    createProject,
  } = useProjectStore();

  const { toast } = useToast();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    fetchProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (error) {
      toast({
        title: "Project Error",
        description: error,
        variant: "destructive",
      });
    }
  }, [error, toast]);

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) {
      toast({ title: "Info", description: "Please enter a project name.", variant: "default" });
      return;
    }
    setIsCreating(true);
    const created = await createProject(newProjectName);
    setIsCreating(false);
    if (created) {
      toast({ title: "Success", description: `Project "${created.name}" created.` });
      setIsCreateDialogOpen(false);
      setNewProjectName('');
    }
  };

  const handleSelectChange = (value: string) => {
    if (value === 'create_new') {
      setNewProjectName('');
      setIsCreateDialogOpen(true);
    } else if (value) {
      setSelectedProject(value);
    }
  };

  // Find the selected project name
  const selectedProjectName = isStoreLoading
      ? "Loading Projects..."
      : projects.find(p => p.id === selectedProjectId)?.name ?? "Select a Project";

  return (
    <div className="px-2.5 py-2 border-b border-neutral-200 bg-neutral-50">
      <Select
        value={selectedProjectId ?? ''}
        onValueChange={handleSelectChange}
        disabled={isStoreLoading || isCreating}
      >
        <SelectTrigger
          className="w-full h-8 px-2.5 py-0 text-sm bg-transparent border-neutral-200 rounded 
                    text-neutral-800 font-medium hover:bg-neutral-50
                    focus:outline-none focus:ring-1 focus:ring-neutral-300
                    disabled:opacity-60 disabled:cursor-not-allowed"
          aria-label="Select Project"
        >
          <div className="flex items-center truncate">
            <span className="text-xs font-semibold text-neutral-500 mr-1.5">Project:</span>
            <span className="truncate">{selectedProjectName}</span>
          </div>
          {isStoreLoading ? 
            <Loader2 className="h-3.5 w-3.5 animate-spin opacity-70 ml-1 shrink-0" /> : 
           <div></div>
          }
        </SelectTrigger>

        <SelectContent
          className=" border border-neutral-200 text-neutral-800 shadow-md rounded-md p-1 max-h-60"
          position="popper"
          sideOffset={4}
          align="start"
          alignOffset={-8}
        >
          {isStoreLoading ? (
            <div className="flex items-center justify-center p-3">
              <Loader2 className="h-4 w-4 animate-spin text-neutral-600" />
            </div>
          ) : projects.length > 0 ? (
            <SelectGroup>
              <SelectLabel className="px-2 py-1 text-xs font-semibold text-neutral-500">Projects</SelectLabel>
              {projects.map((project) => (
                <SelectItem
                  key={project.id}
                  value={project.id}
                  className="px-2 py-1 text-sm cursor-pointer rounded-sm focus:bg-neutral-100
                          data-[state=checked]:bg-neutral-100 data-[state=checked]:font-medium
                          hover:bg-neutral-100"
                >
                  {project.name}
                </SelectItem>
              ))}
            </SelectGroup>
          ) : (
            <div className="px-2 py-2 text-center text-xs text-neutral-500">
              No projects found.
            </div>
          )}

          <SelectSeparator className="bg-neutral-200 my-1 h-px" />

          <SelectItem
            value="create_new"
            className="px-2 py-1 text-sm cursor-pointer rounded-sm flex items-center
                    text-neutral-800 hover:bg-neutral-100 focus:bg-neutral-100"
          >
            <PlusCircle className="mr-1.5 h-3.5 w-3.5 text-neutral-600" /> Create New Project...
          </SelectItem>
        </SelectContent>
      </Select>

      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-md bg-white shadow-lg border-neutral-200 text-neutral-800 p-5">
          <DialogHeader className="space-y-1.5 mb-3">
            <DialogTitle className="text-lg font-semibold text-neutral-800">Create New Project</DialogTitle>
            <DialogDescription className="text-sm text-neutral-500">Enter a name for your new project.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="space-y-2">
              <Label htmlFor="new-project-name" className="text-sm font-medium text-neutral-700">Project Name</Label>
              <Input
                id="new-project-name"
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="e.g., My Awesome App"
                className="h-9 bg-white border-neutral-300 text-neutral-800 placeholder:text-neutral-400 focus:ring-1 focus:ring-neutral-400"
                disabled={isCreating}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter className="mt-4 pt-3 border-t border-neutral-200 flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setIsCreateDialogOpen(false)}
              className="h-8 px-3 bg-white text-neutral-700 border-neutral-300 hover:bg-neutral-50"
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button
              onClick={handleCreateProject}
              className="h-8 px-3 bg-neutral-800 text-white hover:bg-neutral-700 disabled:opacity-60"
              disabled={!newProjectName.trim() || isCreating}
            >
              {isCreating ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : null}
              {isCreating ? 'Creating...' : 'Create Project'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};