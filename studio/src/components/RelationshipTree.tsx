import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { Network, Link2, Plus, ChevronDown, Box, MoreVertical, Search } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import React, { useState, useRef, useMemo } from 'react';

import { Module } from './TreeView';
import { Tree, NodeRendererProps } from 'react-arborist';
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
} from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { buildTreeFromModules } from '../lib/tree';
import { cn } from "@/lib/utils";
import { Input } from "./ui/input";
import { Badge } from "./ui/badge";

const RELATIONSHIP_TYPES = [
  { 
    id: 'context', 
    label: 'Context',
    description: 'Modules that provide context or background information',
    icon: Network 
  },
  { 
    id: 'connection', 
    label: 'Connection',
    description: 'Modules that are directly connected or dependent',
    icon: Link2 
  },
] as const;

export type RelationshipType = typeof RELATIONSHIP_TYPES[number]['id'];

export interface ModuleWithRelations extends Module {
  relationTypes: RelationshipType[];
}

export interface RelationshipTreeNode {
  id: string;
  name: string;
  isFolder: boolean;
  children?: RelationshipTreeNode[];
  module?: ModuleWithRelations;
}

interface ExtendedRelationshipTreeNode extends RelationshipTreeNode {
  onRemoveRelation?: (moduleId: string, type: RelationshipType) => void;
}



const RelationshipNode = React.forwardRef<HTMLDivElement, NodeRendererProps<ExtendedRelationshipTreeNode>>(
  ({ node, style }, ref) => {
    const [showActions, setShowActions] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const hideTimeoutRef = useRef<NodeJS.Timeout>();

    const handleMouseEnter = () => {
      if (hideTimeoutRef.current) {
        clearTimeout(hideTimeoutRef.current);
      }
      setShowActions(true);
    };

    const handleMouseLeave = () => {
      if (!isMenuOpen) {
        hideTimeoutRef.current = setTimeout(() => {
          setShowActions(false);
        }, 100);
      }
    };

    return (
      <div 
      ref={ref}
      style={style}
      className={cn(
        "flex items-center py-1 px-2",
        "hover:bg-gray-100 cursor-pointer",
        "rounded-sm group h-7"
      )}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={(_) => {
        if (node.isInternal) {
          node.toggle();
        }
      }}
    >
      <div className="flex items-center gap-1.5 flex-1 justify-between">
        <div className="flex items-center gap-1.5">
          {node.data.isFolder ? (
            <Button 
              variant="ghost" 
              size="icon"
              className="h-4 w-4 p-0 hover:bg-transparent"
              onClick={(e) => {
                e.stopPropagation();
                node.toggle();
              }}
            >
              <ChevronDown className={cn(
                "h-3 w-3 text-muted-foreground transition-transform ml-",
                !node.isOpen && "-rotate-90"
              )} />
            </Button>
          ) : (
            <Box className="h-3 w-3 text-muted-foreground ml-4" />
          )}
          <span className="text-sm truncate">{node.data.name}</span>
          {!node.data.isFolder && node.data.module?.relationTypes.map(type => {
            const relationConfig = RELATIONSHIP_TYPES.find(r => r.id === type);
            if (!relationConfig) return null;
            const Icon = relationConfig.icon;
            return (
              <TooltipProvider key={type}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <Icon className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{relationConfig.label} Relationship</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            );
          })}
        </div>
        {(showActions || isMenuOpen) && node.data.module && !node.data.isFolder && (
          <DropdownMenu 
            modal={false}
            open={isMenuOpen}
            onOpenChange={setIsMenuOpen}
          >
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 p-0"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
              >
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[200px]">
              <DropdownMenuLabel>Options</DropdownMenuLabel>
              {node.data.module.relationTypes.map(type => {
                const relationConfig = RELATIONSHIP_TYPES.find(r => r.id === type);
                if (!relationConfig) return null;
                const Icon = relationConfig.icon;
                return (
                  <DropdownMenuItem
                    key={type}
                    onSelect={() => {
                      if (node.data.onRemoveRelation) {
                        node.data.onRemoveRelation(node.data.module!.module_id, type);
                      }
                      setIsMenuOpen(false);
                    }}
                    className="text-destructive"
                  >
                    <Icon className="h-4 w-4 mr-2" />
                    Remove {relationConfig.label}
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
    );
  }
);

RelationshipNode.displayName = 'RelationshipNode';

interface RelationshipTreeProps {
  modules: ModuleWithRelations[];
  isLoading?: boolean;
  onAddRelation?: (targetModule: Module, types: RelationshipType[]) => void;
  availableModules?: Module[];
  onRemoveRelation?: (moduleId: string, type: RelationshipType) => void;
  currentModuleId?: string;
}

export const RelationshipTree: React.FC<RelationshipTreeProps> = ({
  modules,
  isLoading = false,
  onAddRelation,
  availableModules = [],
  onRemoveRelation,
  currentModuleId
}) => {
  const [selectedTypes, setSelectedTypes] = useState<RelationshipType[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [treeSearchTerm, setTreeSearchTerm] = useState("");

  const baseTreeData = buildTreeFromModules(modules).map(node => ({
    ...node,
    onRemoveRelation,
    isFolder: node.isFolder ?? false,
  })) as ExtendedRelationshipTreeNode[];

  // Helper function to recursively filter tree nodes
  const filterNodes = (nodes: RelationshipTreeNode[], searchText: string): RelationshipTreeNode[] => {
    return nodes.reduce<RelationshipTreeNode[]>((acc, node) => {
      const matchesSearch = node.name.toLowerCase().includes(searchText.toLowerCase());
      
      if (node.children) {
        const filteredChildren = filterNodes(node.children, searchText);
        if (matchesSearch || filteredChildren.length > 0) {
          acc.push({
            ...node,
            children: filteredChildren
          });
        }
      } else if (matchesSearch) {
        acc.push(node);
      }
      
      return acc;
    }, []);
  };

  const treeData = useMemo(() => {
    if (!treeSearchTerm.trim()) return baseTreeData;
    return filterNodes(baseTreeData, treeSearchTerm);
  }, [baseTreeData, treeSearchTerm]);
  
  const filteredModules = availableModules.filter(module => 
    module.module_id !== currentModuleId &&
    (module.module_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
     module.path.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleAddRelation = (module: Module) => {
    if (selectedTypes.length === 0) return;
    onAddRelation?.(module, selectedTypes);
    setSelectedTypes([]);
    setIsDialogOpen(false);
    setSearchTerm("");
  };

  return (
    <Card className="h-full flex flex-col border-none rounded-none ">
      <CardHeader className="px-2 py-1 space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-xs font-medium text-gray-600">RELATIONSHIPS</p>
          {onAddRelation && (
            <Dialog 
              open={isDialogOpen} 
              onOpenChange={(open) => {
                setIsDialogOpen(open);
                if (!open) {
                  setSelectedTypes([]);
                  setSearchTerm("");
                }
              }}
            >
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-6 w-6 p-0">
                  <Plus className="h-4 w-4" />
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-2xl">
                <DialogHeader>
                  <DialogTitle>Add New Relationship</DialogTitle>
                  <DialogDescription>
                    Select relationship types and choose a module to connect with
                  </DialogDescription>
                </DialogHeader>
                
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    {RELATIONSHIP_TYPES.map(({ id, label, description, icon: Icon }) => (
                      <Card 
                        key={id} 
                        className={cn(
                          "cursor-pointer transition-colors",
                          selectedTypes.includes(id) && "border-primary"
                        )}
                        onClick={() => {
                          setSelectedTypes(prev =>
                            prev.includes(id)
                              ? prev.filter(t => t !== id)
                              : [...prev, id]
                          );
                        }}
                      >
                        <CardHeader className="p-4 space-y-2">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Checkbox
                              checked={selectedTypes.includes(id)}
                              onCheckedChange={(checked) => {
                                setSelectedTypes(prev =>
                                  checked
                                    ? [...prev, id]
                                    : prev.filter(t => t !== id)
                                );
                              }}
                            />
                            <Icon className="h-4 w-4" />
                            {label}
                          </CardTitle>
                          <CardDescription className="text-xs">
                            {description}
                          </CardDescription>
                        </CardHeader>
                      </Card>
                    ))}
                  </div>
  
                  <Separator />
  
                  <div className="space-y-2">
                    <Label>Available Modules</Label>
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
                              "hover:bg-accent hover:text-accent-foreground"
                            )}
                            onClick={() => handleAddRelation(module)}
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
              </DialogContent>
            </Dialog>
          )}
        </div>
      </CardHeader>
  
      <div className="px-2 pb-2">
        <div className="flex items-center gap-2 px-2 py-1.5 bg-white/50 border border-gray-200/80 rounded-xl w-full">
          <Search className="w-4 h-4 text-gray-500" />
          <Input
            type="text"
            placeholder="Search relationships..."
            value={treeSearchTerm}
            onChange={(e) => setTreeSearchTerm(e.target.value)}
            className="h-6 text-sm bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 border-none shadow-none w-full placeholder:text-gray-400"
          />
        </div>
      </div>

      <div className="flex-1">
        <ScrollArea className="h-full">
          {isLoading ? (
            <div className="p-4 text-center text-muted-foreground">
              Loading...
            </div>
          ) : modules.length === 0 ? (
            <div className="p-4 text-center text-muted-foreground">
              No relationships found
            </div>
          ) : (
            <Tree<ExtendedRelationshipTreeNode>
              data={treeData}
              width="100%"
              height={800}
              indent={16}
              rowHeight={28}
              overscanCount={5}
            >
              {RelationshipNode}
            </Tree>
          )}
        </ScrollArea>
      </div>
    </Card>
  );
};
