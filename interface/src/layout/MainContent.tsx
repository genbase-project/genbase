import React, { useState, useEffect, useRef } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { Tree, NodeRendererProps } from 'react-arborist';
import CodeEditor from '../components/CodeEditor';
import { ChevronRight, ChevronDown, Box, RefreshCw, Code, Eye, Package, Expand, Minimize, Network } from 'lucide-react';
import RightSidebar from './RightSidebar';
import { Module } from '../components/TreeView';
import ReactMarkdown from 'react-markdown';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Info, AlertTriangle } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { ENGINE_BASE_URL } from '@/config';

interface TreeItem {
  id: string;
  name: string;
  children?: TreeItem[];
  isFolder?: boolean;
  content?: string;
  description?: string;
}

interface ApiResponse {
  path: string;
  name: string;
  content: string;
  description: string;
}

const RESOURCE_TYPES = ['documentation', 'specification', 'workspace', 'manifests'];

const buildTreeFromPaths = (items: ApiResponse[]): TreeItem[] => {
  const root: { [key: string]: TreeItem } = {};

  items.forEach(item => {
    const parts = item.path.split('/');
    let currentLevel = root;

    parts.forEach((part, index) => {
      const isLast = index === parts.length - 1;
      const id = parts.slice(0, index + 1).join('/');

      if (!currentLevel[id]) {
        currentLevel[id] = {
          id,
          name: part,
          isFolder: !isLast,
          children: isLast ? undefined : [],
          content: isLast ? item.content : undefined,
          description: isLast ? item.description : undefined
        };

        const parentId = parts.slice(0, index).join('/');
        if (index > 0 && root[parentId]) {
          root[parentId].children?.push(currentLevel[id]);
        }
      }

      currentLevel = currentLevel[id].children ? root : {};
    });
  });

  return Object.values(root).filter(item => !item.id.includes('/'));
};

const ContentViewer = ({ 
  content, 
  isMarkdown, 
  onChange,
  viewMode = 'code'
}: { 
  content: string; 
  isMarkdown: boolean; 
  onChange: (value: string) => void;
  viewMode: 'preview' | 'code';
  isExpanded?: boolean;
}) => {
  if (!isMarkdown) {
    return (
      <CodeEditor 
        value={content}
        onChange={onChange}
      />
    );
  }

  return viewMode === 'preview' ? (

    <div className=" flex flex-col overflow-auto">
         <ScrollArea className="flex-1 overflow-x-hidden">
      <div className="prose max-w-none p-4 ">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
      </ScrollArea>
    </div>
  ) : (
    <CodeEditor 
      value={content}
      onChange={onChange}
    />
  );
};

const MainContent = ({selectedModule}:{selectedModule: Module | null}) => {
  const [resourceStateCache, setResourceStateCache] = useState<{ 
    [moduleId: string]: { 
      type: string, 
      selectedNodeId: string | null 
    } 
  }>({});
  
  const [selectedResourceType, setSelectedResourceType] = useState<string>(RESOURCE_TYPES[0]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [treeData, setTreeData] = useState<TreeItem[]>([]);
  const [resourceData, setResourceData] = useState<ApiResponse[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('code');
const [isExpanded, setIsExpanded] = useState(false);
  const [showRelations, setShowRelations] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  const deleteInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (selectedModule?.module_id) {
      const cachedState = resourceStateCache[selectedModule.module_id];
      if (cachedState) {
        setSelectedResourceType(cachedState.type);
        setSelectedNodeId(cachedState.selectedNodeId);
      } else {
        setSelectedResourceType(RESOURCE_TYPES[0]);
        setSelectedNodeId(null);
      }
    }
  }, [selectedModule?.module_id]);

  useEffect(() => {
    if (selectedModule?.module_id) {
      setResourceStateCache(prev => ({
        ...prev,
        [selectedModule.module_id]: {
          type: selectedResourceType,
          selectedNodeId
        }
      }));
    }
  }, [selectedModule?.module_id, selectedResourceType, selectedNodeId]);

  const fetchResources = async () => {
    if (!selectedModule) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(
        `${ENGINE_BASE_URL}/resource/${selectedModule.module_id}/${selectedResourceType}`
      );
      const data: ApiResponse[] = await response.json();
      setResourceData(data);
      const tree = buildTreeFromPaths(data);
      setTreeData(tree);
    } catch (error) {
      console.error('Error fetching resources:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchResources();
  }, [selectedModule, selectedResourceType]);

  const handleGenerateManifest = async () => {
    if (!selectedModule) return;
    
    try {
      await fetch(
        `${ENGINE_BASE_URL}/resource/${selectedModule.module_id}/manifest`,
        { method: 'GET' }
      );
      await fetchResources();  // Refresh to get the newly generated manifest
    } catch (error) {
      console.error('Error generating manifest:', error);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchResources();
    setIsRefreshing(false);
  };

  const Node = React.forwardRef<HTMLDivElement, NodeRendererProps<TreeItem>>((props, ref) => {
    const { node, style } = props;
    const isSelected = node.id === selectedNodeId;
    
    const handleNodeClick = () => {
      if (node.isInternal) {
        node.toggle();
      }
      if (!node.data.isFolder) {
        setSelectedNodeId(node.id);
      }
    };
    
    return (
      <div 
        ref={ref}
        style={style}
        className={`flex items-center py-0.5 px-1 hover:bg-gray-100 ${
          isSelected ? 'bg-blue-50 hover:bg-blue-100' : ''
        }`}
        onClick={handleNodeClick}
      >
        <div className="flex items-center gap-1">
          {node.data.isFolder ? (
            <>
              {node.isOpen ? 
                <ChevronDown className="h-3 w-3 text-gray-400" /> : 
                <ChevronRight className="h-3 w-3 text-gray-400" />
              }
            </>
          ) : (
            <>
              <span className="w-3" />
              <Box className="h-3 w-3 text-gray-400" />
            </>
          )}
          <span className="text-sm">{node.data.name}</span>
          {isSelected && isLoading && (
            <RefreshCw className="h-3 w-3 text-gray-400 animate-spin ml-1" />
          )}
        </div>
      </div>
    );
  });

  Node.displayName = 'Node';

  const handleContentChange = (newValue: string) => {
    if (selectedNodeId) {
      setResourceData(prev => 
        prev.map(item => 
          item.path === selectedNodeId 
            ? { ...item, content: newValue }
            : item
        )
      );
    }
  };

  const isMarkdownFile = (path: string) => path.toLowerCase().endsWith('.md');

  if (!selectedModule) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <Package className="w-12 h-12 text-gray-400 mb-2 mx-auto" strokeWidth={1.5} />
            
            <h2 className="text-xl font-semibold text-gray-700 mb-2">No Module Selected</h2>
            <p className="text-gray-500">Select a module from the sidebar to explore its contents</p>
          
          </div>
        </div>
      </div>
    );
  }

  const containerClass = isExpanded && selectedNodeId 
    ? "fixed inset-4 bg-white rounded-lg shadow-2xl z-50 flex flex-col"
    : "h-full flex flex-col";

  return (
    <div className={containerClass}>
      {/* Header section */}
      <div className="flex h-12 items-center px-4 border-b justify-between">
        <div className="flex items-center space-x-6">
          <div className="flex items-center gap-3">
            <div className="font-medium text-base">
              {selectedModule.module_name}
            </div>
            <div className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
              v{selectedModule.version}
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <button className="p-1.5 hover:bg-gray-100 rounded-full">
                  <Info className="h-4 w-4 text-gray-600" />
                </button>
              </DialogTrigger>
              <DialogContent className="max-w-4xl max-h-[80vh]">
                <DialogHeader>
                  <DialogTitle>
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{selectedModule.module_name}</span>
                      <span className="text-sm bg-blue-50 text-blue-600 px-2 py-0.5 rounded-full">
                        v{selectedModule.version}
                      </span>
                    </div>
                  </DialogTitle>
                </DialogHeader>
                <Tabs defaultValue="module" className="mt-4">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="module">Module Info</TabsTrigger>
                    <TabsTrigger value="kit">Kit Info</TabsTrigger>
                    <TabsTrigger value="env">Environment</TabsTrigger>
                    <TabsTrigger value="destroy" className="text-destructive">Destroy</TabsTrigger>
                  </TabsList>
                  <ScrollArea className="h-[500px] mt-4">
                  <div className="px-2">
                  <TabsContent value="module">
                  <div className="bg-gray-50 rounded-lg p-4 grid gap-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                      <span className="font-medium text-gray-500">Version</span>
                      <span className="col-span-3">{selectedModule.version}</span>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <span className="font-medium text-gray-500">Owner</span>
                      <span className="col-span-3">{selectedModule.owner}</span>
                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                      <span className="font-medium text-gray-500">Created</span>
                      <span className="col-span-3">{new Date(selectedModule.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  </TabsContent>
                  <TabsContent value="kit">
                    <div className="space-y-4">
                      <div className="bg-gray-50 rounded-lg p-4 grid gap-4">
                        <div className="grid grid-cols-4 items-center gap-4">
                          <span className="font-medium text-gray-500">Kit ID</span>
                          <span className="col-span-3">{selectedModule.kit_id}</span>
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                          <span className="font-medium text-gray-500">Repository</span>
                          <span className="col-span-3">{selectedModule.repo_name}</span>
                        </div>
                        <div className="grid grid-cols-4 items-center gap-4">
                          <span className="font-medium text-gray-500">Path</span>
                          <span className="col-span-3 font-mono text-sm">{selectedModule.path}</span>
                        </div>
                      </div>
                    </div>
                  </TabsContent>

                  <TabsContent value="env" className="space-y-4">
                    {Object.entries(selectedModule.env_vars).length > 0 ? (
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="font-mono text-sm grid gap-2">
                          {Object.entries(selectedModule.env_vars).map(([key, value]) => (
                            <div key={key} className="grid grid-cols-[200px_1fr] gap-2 items-baseline">
                              <span className="text-gray-500">{key}:</span>
                              <span>{value}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-4 text-gray-500">
                        No environment variables configured
                      </div>
                    )}
                  
                  </TabsContent>
                  <TabsContent value="destroy" className="space-y-4">
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                      <h3 className="text-lg font-semibold text-red-600 mb-2">Danger Zone</h3>
                      <p className="text-sm text-gray-600 mb-4">
                        Force deleting a module is a destructive action that cannot be undone.
                      </p>
                      <Button
                        variant="destructive"
                        onClick={() => setShowDeleteDialog(true)}
                        className="w-full"
                      >
                        Force Delete Module
                      </Button>
                    </div>
                  </TabsContent>
                  </div>
                  </ScrollArea>
                </Tabs>
              </DialogContent>
            </Dialog>

            <AlertDialog 
              open={showDeleteDialog} 
              onOpenChange={setShowDeleteDialog}
              
            >
              <AlertDialogContent  className='bg-white'>
                <AlertDialogHeader>
                  <AlertDialogTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-destructive" />
                    Force Delete Module
                  </AlertDialogTitle>
                  <AlertDialogDescription className="space-y-3">
                    <p className="font-semibold text-destructive">Warning: This action cannot be undone!</p>
                    <ul className="list-disc pl-4 space-y-1 text-sm">
                      <li>Module will be completely deleted from the system</li>
                      <li>All running agents will be terminated immediately</li>
                      <li>All workspace files will be permanently deleted</li>
                      <li>This action may affect system stability if module is critical</li>
                    </ul>
                    <p className="text-sm mt-4">
                      To confirm deletion, type "delete {selectedModule?.module_name}" below:
                    </p>
                    <Input
                      ref={deleteInputRef}
                      value={deleteConfirmText}
                      onChange={(e) => setDeleteConfirmText(e.target.value)}
                      className="mt-2"
                      placeholder={`delete ${selectedModule?.module_name}`}
                    />
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel onClick={() => {
                    setDeleteConfirmText('');
                    setShowDeleteDialog(false);
                  }}>
                    Cancel
                  </AlertDialogCancel>
                  <AlertDialogAction
                    disabled={deleteConfirmText !== `delete ${selectedModule?.module_name}`}
                    onClick={async () => {
                      if (!selectedModule) return;
                      
                      try {
                        await fetch(
                          `${ENGINE_BASE_URL}/module/${selectedModule.module_id}`,
                          { method: 'DELETE' }
                        );
                        
                        

                        window.location.reload();

                      } catch (error) {
                        console.error('Error deleting module:', error);
                      }
                 
                    }}
                    className="bg-destructive hover:bg-destructive/90 bg-red-600"
                  >
                    Delete Module
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
          <Select
            value={selectedResourceType}
            onValueChange={(value) => setSelectedResourceType(value)}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {RESOURCE_TYPES.map((type) => (
                <SelectItem key={type} value={type}>
                  {type}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-center gap-2">
        
          {selectedNodeId && (
            <div className="flex space-x-1">
              {isMarkdownFile(selectedNodeId) && (
                <>
                  <Button
                    size="sm"
                    variant={viewMode === 'preview' ? 'secondary' : 'outline'}
                    onClick={() => setViewMode('preview')}
                    className="flex items-center gap-2 rounded-full border-0 shadow-none"
                  >
                    <Eye className="h-3 w-3" />
                  </Button>
                  <Button
                    size="sm"
                    variant={viewMode === 'code' ? 'secondary' : 'outline'}
                    onClick={() => setViewMode('code')}
                    className="flex items-center gap-2 rounded-full border-0 shadow-none"
                  >
                    <Code className="h-4 w-4" />
                  </Button>
                </>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={() => setIsExpanded(!isExpanded)}
                className="flex items-center gap-2 rounded-full border-0 shadow-none"
              >
                {isExpanded ? (
                  <Minimize className="h-3 w-3" />
                ) : (
                  <Expand className="h-3 w-3" />
                )}
              </Button>
            </div>
          )}
          <div className="flex items-center gap-2">
            {selectedResourceType === 'manifests' && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateManifest}
                className="flex items-center gap-2"
              >
                Generate
              </Button>
            )}
            <button
              onClick={handleRefresh}
              className="p-2 hover:bg-slate-100 rounded-full"
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-4 w-4 text-gray-600 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
            <Button
            size="sm"
            variant={showRelations ? "secondary" : "outline"}
            onClick={() => setShowRelations(!showRelations)}
            className="flex items-center gap-2"
          >
            <Network className="h-4 w-4" />
            Relations
          </Button>
          </div>
        </div>
      </div>

      {/* Main content section */}
      <div className="flex-1">
        <div className="h-full border rounded">
          <ResizablePanelGroup direction="horizontal" className="h-full">
            <ResizablePanel defaultSize={20} minSize={15}>
              <div className="h-full border-r">
                <Tree<TreeItem>
                  data={treeData}
                  width="100%"
                  height={800}
                  indent={16}
                  rowHeight={24}
                  overscanCount={1}
                >
                  {Node}
                </Tree>
              </div>
            </ResizablePanel>
            <ResizableHandle withHandle />
            <ResizablePanel>
              <div className="h-full">
                {selectedNodeId ? (
                  isLoading ? (
                    <div className="p-4">
                      <div className="animate-pulse flex space-x-4">
                        <div className="flex-1 space-y-4 py-1">
                          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                          <div className="space-y-2">
                            <div className="h-4 bg-gray-200 rounded"></div>
                            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <ContentViewer 
                      key={`${selectedNodeId}-${viewMode}`}
                      content={resourceData.find(item => item.path === selectedNodeId)?.content || '// No content available'}
                      isMarkdown={isMarkdownFile(selectedNodeId)}
                      onChange={handleContentChange}
                      viewMode={viewMode}
                      isExpanded={isExpanded}
                    />
                  )
                ) : (
                  <div className="p-4 text-gray-500">
                    Select a file to view its content
                  </div>
                )}
              </div>
            </ResizablePanel>
            {showRelations && (
              <>
                <ResizableHandle withHandle />
                <ResizablePanel defaultSize={30} minSize={10}>
                  <RightSidebar selectedModule={selectedModule} />
                </ResizablePanel>
              </>
            )}
          </ResizablePanelGroup>
        </div>
      </div>
    </div>
  );
};

export default MainContent;
