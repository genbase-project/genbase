
import { Network, PlugZap, Plug, Plus, ChevronDown, Box, MoreVertical, Search, Download, Upload, Folder } from 'lucide-react';
import { useEffect, useState, useMemo, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { toast } from '@/hooks/use-toast';
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
import { Textarea } from '@/components/ui/textarea';
import { DEFAULT_PROJECT_ID } from '@/lib/tree';
import { Module } from '@/components/TreeView';



// Define ProvideType enum
enum ProvideType {
    WORKSPACE = "workspace",
    TOOL = "tool",
}


export interface ModuleProvide {
  provider_id: string;
  receiver_id: string;
  resource_type: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface ProvideRelationshipCardProps {
    module?: Module;
    provide: ModuleProvide;
    onUpdate?: (description: string) => Promise<boolean>;
    onDelete?: () => Promise<boolean>;
    isProvider?: boolean;
  }
  
 export const ProvideRelationshipCard: React.FC<ProvideRelationshipCardProps> = ({
    module,
    provide,
    onUpdate,
    onDelete,
    isProvider = true
  }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [description, setDescription] = useState(provide.description || "");
    const [isLoading, setIsLoading] = useState(false);
  
    const resourceTypeIcon = provide.resource_type === ProvideType.WORKSPACE ? 
      <Folder className="h-4 w-4" /> : 
      <PlugZap className="h-4 w-4" />;
  
    const handleUpdateDescription = async () => {
      setIsLoading(true);
      try {
        if (onUpdate) {
          const success = await onUpdate(description);
          if (success) {
            setIsEditing(false);
          }
        }
      } finally {
        setIsLoading(false);
      }
    };
  
    const handleDelete = async () => {
      setIsLoading(true);
      try {
        if (onDelete) {
          await onDelete();
        }
      } finally {
        setIsLoading(false);
      }
    };
  
    return (
      <Card className="mb-2">
        <CardHeader className="p-4 pb-2">
          <div className="flex justify-between items-start">
            <div className="flex items-center space-x-2">
              {resourceTypeIcon}
              <CardTitle className="text-sm">
                {provide.resource_type.toUpperCase()}
                {module && (
                  <span className="font-normal text-gray-500">
                    {isProvider ? " to " : " from "}
                    <span className="font-medium text-gray-700">
                      {module.module_name || module.path}
                    </span>
                  </span>
                )}
              </CardTitle>
            </div>
            <div className="flex space-x-1">
              {isProvider && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={() => setIsEditing(!isEditing)}
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>Edit or remove</p>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          {isEditing ? (
            <div className="space-y-2">
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe this resource provision..."
                className="h-20 text-sm"
              />
              <div className="flex justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsEditing(false)}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
                <div className="space-x-2">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleDelete}
                    disabled={isLoading}
                  >
                    Remove
                  </Button>
                  <Button
                    variant="default"
                    size="sm"
                    onClick={handleUpdateDescription}
                    disabled={isLoading}
                  >
                    Save
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-600">
              {provide.description || "No description provided."}
            </p>
          )}
        </CardContent>
      </Card>
    );
  };
  
 export interface AddProvideDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    availableModules: Module[];
    onAddProvide: (receiverId: string, resourceType: ProvideType, description: string) => Promise<any>;
  }
  
  export const AddProvideDialog: React.FC<AddProvideDialogProps> = ({
    open,
    onOpenChange,
    availableModules,
    onAddProvide
  }) => {
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedModule, setSelectedModule] = useState<Module | null>(null);
    const [selectedType, setSelectedType] = useState<ProvideType | null>(null);
    const [description, setDescription] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
  
    const filteredModules = useMemo(() => {
      return availableModules.filter(module => 
        module.module_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        module.path.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }, [availableModules, searchTerm]);
  
    const handleSelectModule = (module: Module) => {
      setSelectedModule(module);
    };
  
    const handleSubmit = async () => {
      if (!selectedModule || !selectedType) return;
      
      setIsSubmitting(true);
      try {
        await onAddProvide(selectedModule.module_id, selectedType, description);
        onOpenChange(false);
        resetForm();
      } finally {
        setIsSubmitting(false);
      }
    };
  
    const resetForm = () => {
      setSelectedModule(null);
      setSelectedType(null);
      setDescription("");
      setSearchTerm("");
    };
  
    return (
      <Dialog open={open} onOpenChange={(value) => {
        if (!value) resetForm();
        onOpenChange(value);
      }}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Provide Resource to Module</DialogTitle>
            <DialogDescription>
              Select a resource type and a module to provide it to
            </DialogDescription>
          </DialogHeader>
          
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Resource Type</Label>
              <div className="grid grid-cols-2 gap-4">
                <Card 
                  className={cn(
                    "cursor-pointer transition-colors",
                    selectedType === ProvideType.WORKSPACE && "border-primary"
                  )}
                  onClick={() => setSelectedType(ProvideType.WORKSPACE)}
                >
                  <CardHeader className="p-4 space-y-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Checkbox
                        checked={selectedType === ProvideType.WORKSPACE}
                        onCheckedChange={(checked) => {
                          setSelectedType(checked ? ProvideType.WORKSPACE : null);
                        }}
                      />
                      <Box className="h-4 w-4" />
                      WORKSPACE
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Provide workspace access to the target module
                    </CardDescription>
                  </CardHeader>
                </Card>
                
                <Card 
                  className={cn(
                    "cursor-pointer transition-colors",
                    selectedType === ProvideType.TOOL && "border-primary"
                  )}
                  onClick={() => setSelectedType(ProvideType.TOOL)}
                >
                  <CardHeader className="p-4 space-y-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Checkbox
                        checked={selectedType === ProvideType.TOOL}
                        onCheckedChange={(checked) => {
                          setSelectedType(checked ? ProvideType.TOOL : null);
                        }}
                      />
                      <PlugZap className="h-4 w-4" />
                      TOOL
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Provide tool capabilities to the target module
                    </CardDescription>
                  </CardHeader>
                </Card>
              </div>
            </div>
  
            <div className="space-y-2">
              <Label>Description (Optional)</Label>
              <Textarea
                placeholder="Describe why you're providing this resource..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="h-20"
              />
            </div>
  
            <Separator />
  
            <div className="space-y-2">
              <Label>Target Module</Label>
              <Input
                type="text"
                placeholder="Search modules..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full"
              />
              <ScrollArea className="h-[200px] rounded-md border">
                <div className="p-2 space-y-2">
                  {filteredModules.map(module => (
                    <Card
                      key={module.module_id}
                      className={cn(
                        "cursor-pointer transition-colors",
                        "hover:bg-accent hover:text-accent-foreground",
                        selectedModule?.module_id === module.module_id ? "border-2 border-primary border-neutral-800" : "border"
                      )}
                      onClick={() => handleSelectModule(module)}
                    >
                      <CardHeader className="p-3 space-y-1">
                        <div className="flex justify-between items-start">
                          <div className="space-y-1">
                            <CardTitle className="text-sm">
                              {module.module_name || module.kit_id}
                            </CardTitle>
                            <CardDescription className="text-xs">
                              {module.path}
                            </CardDescription>
                          </div>
                          <Badge variant="outline" className="text-xs">
                            v{module.version}
                          </Badge>
                        </div>
                      </CardHeader>
                    </Card>
                  ))}
                  {filteredModules.length === 0 && (
                    <div className="text-center py-4 text-sm text-muted-foreground">
                      No modules found
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>
          </div>
  
          <div className="flex justify-end space-x-2">
            <Button 
              variant="outline" 
              onClick={() => {
                resetForm();
                onOpenChange(false);
              }}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button 
              disabled={!selectedModule || !selectedType || isSubmitting}
              onClick={handleSubmit}
            >
              Provide Resource
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  };