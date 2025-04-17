import React, { useState, useEffect, useRef } from 'react';
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { Tree, NodeRendererProps } from 'react-arborist';
import { ChevronRight, ChevronDown, FileText, Folder, RefreshCw, Code, Eye, Package, Network, Plus, AlertCircle } from 'lucide-react';
import RightSidebar from './provide/RightSidebar';
import { Module } from '../../../components/TreeView';
import FileViewer, { isMarkdownFile } from './FileTypeMapper'; // Import the new FileViewer component





import localforage from 'localforage';


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
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';

// Define interface for file metadata
interface WorkspaceFileMetadata {
  path: string;
  name: string;
  mime_type?: string;
  size: number;
  last_modified: string;
}

interface TreeItem {
  id: string;
  name: string;
  children?: TreeItem[];
  isFolder?: boolean;
  description?: string;
  mime_type?: string; // Add mime_type to TreeItem
}

interface ApiResponse {
  path: string;
  name: string;
  content: string;
  description: string;
}

interface EnvironmentVariable {
  name: string;
  description: string;
  required: boolean;
  default?: string;
}

interface FileContent {
  data: string | ArrayBuffer;
  mimeType: string | null;
  isBinary: boolean;
  fileSize?: number;
}


const RESOURCE_TYPES = ['workspace', 'provide-instructions'];

// Function to build tree structure from flat file paths with mime type
const buildTreeFromFilePaths = (items: WorkspaceFileMetadata[]): TreeItem[] => {
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
          description: isLast ? undefined : undefined,
          mime_type: isLast ? item.mime_type : undefined  // Store mime type in tree item
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

// Function to build tree from API response for provide-instructions
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

// Function to check if content is likely binary
const isContentBinary = (content: string): boolean => {
  // Check for common binary signatures or non-printable characters
  const nonPrintableRegex = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\xFF]/;
  
  // If the string is too long, check just a sample
  const sampleSize = Math.min(1000, content.length);
  const sample = content.substring(0, sampleSize);
  
  return nonPrintableRegex.test(sample);
};

const MainContent = ({selectedModule}:{selectedModule: Module | null}) => {
  const [resourceStateCache, setResourceStateCache] = useState<{ 
    [moduleId: string]: { 
      type: string, 
      selectedNodeId: string | null 
    } 
  }>({});
  
  // Track current tab selection
  const [selectedResourceType, setSelectedResourceType] = useState<string>(RESOURCE_TYPES[0]);
  
  // Track selected file node
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  
  // Store tree structure for UI
  const [treeData, setTreeData] = useState<TreeItem[]>([]);
  
  // Store workspace file metadata
  const [workspaceFiles, setWorkspaceFiles] = useState<WorkspaceFileMetadata[]>([]);
  
  // Store provide-instructions resources
  const [provideInstructionResources, setProvideInstructionResources] = useState<ApiResponse[]>([]);
  
  // Track currently loaded file content (enhanced to handle binary files)
  const [currentFileContent, setCurrentFileContent] = useState<FileContent>({
    data: "",
    mimeType: null,
    isBinary: false
  });
  
  // Loading states
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  
  // UI state
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('code');
  const [showRelations, setShowRelations] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  
  // Environment variable state
  const [envVarName, setEnvVarName] = useState('');
  const [envVarValue, setEnvVarValue] = useState('');
  const [kitEnvironmentVars, setKitEnvironmentVars] = useState<EnvironmentVariable[]>([]);
  const [isAddingEnvVar, setIsAddingEnvVar] = useState(false);
  const [newEnvVarName, setNewEnvVarName] = useState('');
  const [newEnvVarValue, setNewEnvVarValue] = useState('');
  
  const deleteInputRef = useRef<HTMLInputElement>(null);

  const handleEnvVarUpdate = async () => {
    if (!selectedModule || !envVarName || !envVarValue) return;
    
    try {
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/module/${selectedModule.module_id}/env`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            env_var_name: envVarName,
            env_var_value: envVarValue,
          }),
        }
      );
      
      if (response.ok) {
        const updatedModule = await response.json();
        // Update the module with new env vars
        selectedModule.env_vars = updatedModule.env_vars;
  
        setEnvVarName('');
        setEnvVarValue('');
      } else {
        console.error('Failed to update environment variable');
      }
    } catch (error) {
      console.error('Error updating environment variable:', error);
    }
  };

  // Function to add a new environment variable
  const handleAddEnvVar = async () => {
    if (!selectedModule || !newEnvVarName) return;
    
    try {
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/module/${selectedModule.module_id}/env`,
        {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            env_var_name: newEnvVarName,
            env_var_value: newEnvVarValue || '', // Allow empty values
          }),
        }
      );
      
      if (response.ok) {
        const updatedModule = await response.json();
        // Update the module with new env vars
        selectedModule.env_vars = updatedModule.env_vars;
  
        // Reset form
        setNewEnvVarName('');
        setNewEnvVarValue('');
        setIsAddingEnvVar(false);
      } else {
        console.error('Failed to add environment variable');
      }
    } catch (error) {
      console.error('Error adding environment variable:', error);
    }
  };

  // Fetch kit environment variables when a module is selected
  useEffect(() => {
    if (selectedModule?.kit_id && selectedModule?.owner && selectedModule?.version) {
      fetchKitEnvironmentVars(selectedModule.owner, selectedModule.kit_id, selectedModule.version);
    } else {
      setKitEnvironmentVars([]);
    }
  }, [selectedModule?.kit_id, selectedModule?.owner, selectedModule?.version]);

  // Function to fetch kit environment variables definition from kit config
  const fetchKitEnvironmentVars = async (owner: string, kitId: string, version: string) => {
    try {
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/kit/registry/config/${owner}/${kitId}/${version}`
      );
      
      if (response.ok) {
        const kitConfig = await response.json();
        if (kitConfig.environment && Array.isArray(kitConfig.environment)) {
          setKitEnvironmentVars(kitConfig.environment);
        } else {
          setKitEnvironmentVars([]);
        }
      }
    } catch (error) {
      console.error('Error fetching kit environment variables:', error);
      setKitEnvironmentVars([]);
    }
  };

  // Restore cached state when module changes
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

  // Save state to cache when relevant state changes
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






  const getFileCacheKey = (moduleId: string, filePath: string) => {
    return `file_${moduleId}_${filePath}`;
  };
  
  // Generate a unique cache key for a file's metadata
  const getFileMetaCacheKey = (moduleId: string, filePath: string) => {
    return `file_meta_${moduleId}_${filePath}`;
  };
  
  // Add a new state to track background loading
  const [isBackgroundLoading, setIsBackgroundLoading] = useState(false);
  
  // Initial load of workspace paths - shows loading UI
  const fetchWorkspacePaths = async () => {
    if (!selectedModule) return;
    
    setIsLoading(true);
    try {
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/resource/${selectedModule.module_id}/workspace/paths`
      );
      const data: WorkspaceFileMetadata[] = await response.json();
      
      // Store the metadata of each file for caching purposes
      data.forEach(async file => {
        await localforage.setItem(
          getFileMetaCacheKey(selectedModule.module_id, file.path), 
          { lastModified: file.last_modified }
        );
      });
      
      setWorkspaceFiles(data);
      const tree = buildTreeFromFilePaths(data);
      setTreeData(tree);
      
      // Don't clear current file content on initial load
      if (!selectedNodeId) {
        setCurrentFileContent({
          data: "",
          mimeType: null,
          isBinary: false
        });
      }
    } catch (error) {
      console.error('Error fetching workspace paths:', error);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Background refresh of workspace paths - doesn't show loading UI
  const backgroundRefreshWorkspacePaths = async () => {
    if (!selectedModule || isBackgroundLoading) return;
    
    setIsBackgroundLoading(true);
    try {
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/resource/${selectedModule.module_id}/workspace/paths`
      );
      
      if (!response.ok) {
        console.error("Background refresh failed:", response.status);
        return;
      }
      
      const newData: WorkspaceFileMetadata[] = await response.json();
      
      // Compare with existing data to see if anything changed
      const hasChanges = checkForFileChanges(workspaceFiles, newData);
      
      // Store the metadata regardless
      newData.forEach(async file => {
        await localforage.setItem(
          getFileMetaCacheKey(selectedModule.module_id, file.path), 
          { lastModified: file.last_modified }
        );
      });
      
      // Only update state if there are actual changes
      if (hasChanges) {
        console.log("Background refresh detected changes, updating file list");
        
        // Update file list but preserve the current tree expansion state
        setWorkspaceFiles(newData);
        const newTree = buildTreeFromFilePaths(newData);
        setTreeData(newTree);
        
        // If selected file was modified, refresh its content
        const selectedFile = newData.find(f => f.path === selectedNodeId);
        const oldFile = workspaceFiles.find(f => f.path === selectedNodeId);
        
        if (selectedFile && oldFile && selectedFile.last_modified !== oldFile.last_modified) {
          console.log("Selected file was modified, refreshing content");
          fetchFileContentWithCache(selectedNodeId!);
        }
      }
    } catch (error) {
      console.error('Background refresh error:', error);
    } finally {
      setIsBackgroundLoading(false);
    }
  };
  
  // Helper function to check if file metadata changed
  const checkForFileChanges = (oldFiles: WorkspaceFileMetadata[], newFiles: WorkspaceFileMetadata[]): boolean => {
    // Quick check: different number of files
    if (oldFiles.length !== newFiles.length) return true;
    
    // Create maps for faster lookup
    const oldMap = new Map(oldFiles.map(f => [f.path, f]));
    const newMap = new Map(newFiles.map(f => [f.path, f]));
    
    // Check if any files were added or removed
    for (const file of oldFiles) {
      if (!newMap.has(file.path)) return true;
    }
    
    for (const file of newFiles) {
      const oldFile = oldMap.get(file.path);
      if (!oldFile) return true; // New file added
      
      // Check if file was modified
      if (file.last_modified !== oldFile.last_modified ||
          file.size !== oldFile.size) {
        return true;
      }
    }
    
    return false; // No changes detected
  };
  
  // Enhanced function to fetch file content with caching
  const fetchFileContentWithCache = async (filePath: string) => {
    if (!selectedModule) return;
    
    setIsLoadingContent(true);
    try {
      // For workspace files
      if (selectedResourceType === 'workspace') {
        // Check if we have metadata for this file
        const fileMetadata = workspaceFiles.find(f => f.path === filePath);
        const cacheKey = getFileCacheKey(selectedModule.module_id, filePath);
        const metaCacheKey = getFileMetaCacheKey(selectedModule.module_id, filePath);
        
        // Check if we have cached metadata
        const cachedMeta = await localforage.getItem(metaCacheKey) as { lastModified: string } | null;
        const cachedContent = await localforage.getItem(cacheKey) as { 
          data: string | ArrayBuffer,
          mimeType: string | null,
          isBinary: boolean
        } | null;
        
        // If we have both cached content and metadata, and the last_modified hasn't changed, use cached content
        if (
          cachedContent && 
          cachedMeta && 
          fileMetadata && 
          cachedMeta.lastModified === fileMetadata.last_modified
        ) {
          console.log('Using cached file content for', filePath);
          setCurrentFileContent(cachedContent);
          setIsLoadingContent(false);
          return;
        }
        
        // Otherwise fetch fresh content
        const response = await fetchWithAuth(
          `${ENGINE_BASE_URL}/resource/${selectedModule.module_id}/workspace/file?relative_path=${encodeURIComponent(filePath)}`
        );
        
        if (response.ok) {
          // Try to read as text first
          try {
            const textContent = await response.clone().text();
            
            // Check if content is binary
            const likelyBinary = isContentBinary(textContent);
            
            if (likelyBinary) {
              // If it looks binary, get the content as ArrayBuffer
              const blob = await response.blob();
              const reader = new FileReader();
              
              // Wrap the FileReader in a promise
              const arrayBuffer = await new Promise<ArrayBuffer>((resolve) => {
                reader.onload = () => {
                  if (reader.result instanceof ArrayBuffer) {
                    resolve(reader.result);
                  }
                };
                reader.readAsArrayBuffer(blob);
              });
              
              const newContent = {
                data: arrayBuffer,
                mimeType: fileMetadata?.mime_type || response.headers.get('content-type'),
                isBinary: true
              };
              
              // Update the cache
              await localforage.setItem(cacheKey, newContent);
              
              setCurrentFileContent(newContent);
            } else {
              // If it looks like text, use the text content
              const newContent = {
                data: textContent,
                mimeType: fileMetadata?.mime_type || response.headers.get('content-type'),
                isBinary: false
              };
              
              // Update the cache
              await localforage.setItem(cacheKey, newContent);
              
              setCurrentFileContent(newContent);
            }
          } catch (e) {
            // If text extraction fails, it's probably binary
            const blob = await response.blob();
            const arrayBuffer = await blob.arrayBuffer();
            
            const newContent = {
              data: arrayBuffer,
              mimeType: fileMetadata?.mime_type || response.headers.get('content-type'),
              isBinary: true
            };
            
            // Update the cache
            await localforage.setItem(cacheKey, newContent);
            
            setCurrentFileContent(newContent);
          }
        } else {
          console.error('Failed to fetch file content');
          setCurrentFileContent({
            data: "Error: Failed to load file content",
            mimeType: "text/plain",
            isBinary: false
          });
        }
      }
      // For provide-instructions content
      else if (selectedResourceType === 'provide-instructions') {
        const resource = provideInstructionResources.find(res => res.path === filePath);
        if (resource) {
          setCurrentFileContent({
            data: resource.content,
            mimeType: "text/markdown", 
            isBinary: false
          });
        } else {
          setCurrentFileContent({
            data: "File content not found",
            mimeType: "text/plain",
            isBinary: false
          });
        }
      }
    } catch (error) {
      console.error('Error fetching file content:', error);
      setCurrentFileContent({
        data: `Error loading file content: ${error}`,
        mimeType: "text/plain",
        isBinary: false
      });
    } finally {
      setIsLoadingContent(false);
    }
  };
  
  // Add a periodic refresh function that doesn't disrupt the UI
  useEffect(() => {
    if (!selectedModule) return;
    
    // Fetch files initially (visible loading)
    fetchWorkspacePaths();
    
    // Set up periodic background polling (every 30 seconds)
    const intervalId = setInterval(() => {
      if (selectedResourceType === 'workspace') {
        backgroundRefreshWorkspacePaths();
      }
    }, 30000); // 30 seconds
    
    // Clean up interval on unmount or module change
    return () => clearInterval(intervalId);
  }, [selectedModule?.module_id]);












  // Function to fetch provide instruction resources
  const fetchProvideInstructions = async () => {
    if (!selectedModule) return;
    
    setIsLoading(true);
    try {
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/resource/${selectedModule.module_id}/provide-instructions`
      );
      const data: ApiResponse[] = await response.json();
      setProvideInstructionResources(data);
      const tree = buildTreeFromPaths(data);
      setTreeData(tree);
    } catch (error) {
      console.error('Error fetching provide-instructions resources:', error);
    } finally {
      setIsLoading(false);
    }
  };


  
  
  

  useEffect(() => {
    if (selectedResourceType === 'workspace') {
      fetchWorkspacePaths();
    } else if (selectedResourceType === 'provide-instructions') {
      fetchProvideInstructions();
    }
    
    // Clear selected node when changing resource type
    setSelectedNodeId(null);
    setCurrentFileContent({
      data: "",
      mimeType: null,
      isBinary: false
    });
  }, [selectedModule, selectedResourceType]);
  
  

  // Fetch file content when a node is selected
  useEffect(() => {
    if (selectedNodeId) {
      fetchFileContentWithCache(selectedNodeId);
    } else {
      setCurrentFileContent({
        data: "",
        mimeType: null,
        isBinary: false
      });
    }
  }, [selectedNodeId]);
  

  const handleRefresh = async () => {
    setIsRefreshing(true);
    if (selectedResourceType === 'workspace') {
      await fetchWorkspacePaths(); // Use the visible loading version for manual refresh
    } else if (selectedResourceType === 'provide-instructions') {
      await fetchProvideInstructions();
    }
    
    // If a file is selected, refresh its content too
    if (selectedNodeId) {
      await fetchFileContentWithCache(selectedNodeId);
    }
    
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
              <Folder className="h-3 w-3 text-gray-400" />
            </>
          ) : (
            <>
              <span className="w-3" />
              <FileText className="h-3 w-3 text-gray-400" />
            </>
          )}
<div className="flex items-center gap-1.5 flex-1 min-w-0 ">
  {/* Icon component here */}
  <span className="text-sm text-gray-700 truncate  text-ellipsis whitespace-nowrap flex-1">
    {node.data.name}
  </span>
</div>
          {isSelected && isLoadingContent && (
            <RefreshCw className="h-3 w-3 text-gray-400 animate-spin ml-1" />
          )}
        </div>
      </div>
    );
  });

  Node.displayName = 'Node';

  const handleContentChange = (newValue: string) => {
    if (typeof currentFileContent.data === 'string') {
      setCurrentFileContent({
        ...currentFileContent,
        data: newValue
      });
    }
    
    // Update the content in the cache for provide-instructions
    if (selectedResourceType === 'provide-instructions' && selectedNodeId) {
      setProvideInstructionResources(prev => 
        prev.map(item => 
          item.path === selectedNodeId 
            ? { ...item, content: newValue }
            : item
        )
      );
    }
    // For workspace files, we would need to implement a save mechanism
    // that sends updated content back to the server
  };

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

  // Get all environment variables defined in the kit but not yet set
  const getUnsetEnvironmentVars = () => {
    if (!selectedModule || !kitEnvironmentVars.length) return [];
    
    // Get variables that are defined in the kit but not in the module's env_vars
    return kitEnvironmentVars.filter(envVar => 
      !Object.keys(selectedModule.env_vars).includes(envVar.name)
    );
  };

  const unsetEnvVars = getUnsetEnvironmentVars();

  const containerClass = "h-full flex flex-col";

  // Get the selected file's mime type from tree data or workspaceFiles
  const getSelectedFileMimeType = (): string | null => {
    if (!selectedNodeId) return null;
    
    // First check if we have it in the tree data
    const findMimeTypeInTree = (nodes: TreeItem[]): string | null => {
      for (const node of nodes) {
        if (node.id === selectedNodeId && node.mime_type) {
          return node.mime_type;
        }
        if (node.children?.length) {
          const childResult = findMimeTypeInTree(node.children);
          if (childResult) return childResult;
        }
      }
      return null;
    };
    
    const treeNodeMimeType = findMimeTypeInTree(treeData);
    if (treeNodeMimeType) return treeNodeMimeType;
    
    // If not in tree, check workspace files
    const workspaceFile = workspaceFiles.find(f => f.path === selectedNodeId);
    return workspaceFile?.mime_type || null;
  };

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
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-lg font-medium">Environment Variables</h3>
                      <Button 
                        size="sm" 
                        onClick={() => {
                          setIsAddingEnvVar(true);
                          setNewEnvVarName('');
                          setNewEnvVarValue('');
                        }}
                        className="flex items-center gap-2"
                      >
                        <Plus className="h-4 w-4" />
                        Add Variable
                      </Button>
                    </div>
                    
                    {/* Form for adding new environment variable */}
                    {isAddingEnvVar && (
                      <div className="bg-blue-50 rounded-lg p-4 mb-4">
                        <h4 className="font-medium mb-3">Add New Environment Variable</h4>
                        <div className="grid gap-3">
                          <div>
                            <label className="block text-sm font-medium mb-1">Variable Name</label>
                            <Select
                              value={newEnvVarName}
                              onValueChange={setNewEnvVarName}
                            >
                              <SelectTrigger>
                                <SelectValue placeholder="Select or type a variable name" />
                              </SelectTrigger>
                              <SelectContent>
                                {unsetEnvVars.map(envVar => (
                                  <SelectItem key={envVar.name} value={envVar.name}>
                                    {envVar.name} {envVar.required && <span className="text-red-500 ml-1">*</span>}
                                  </SelectItem>
                                ))}
                                <SelectItem value="custom">Custom Variable</SelectItem>
                              </SelectContent>
                            </Select>
                            {newEnvVarName === 'custom' && (
                              <Input
                                value=""
                                onChange={(e) => setNewEnvVarName(e.target.value)}
                                placeholder="Enter variable name"
                                className="mt-2 font-mono"
                              />
                            )}
                          </div>
                          <div>
                            <label className="block text-sm font-medium mb-1">Variable Value</label>
                            <Input
                              value={newEnvVarValue}
                              onChange={(e) => setNewEnvVarValue(e.target.value)}
                              placeholder="e.g. secret_value_123"
                              className="font-mono"
                            />
                          </div>
                          <div className="flex justify-end gap-2 mt-2">
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => setIsAddingEnvVar(false)}
                            >
                              Cancel
                            </Button>
                            <Button 
                              size="sm"
                              onClick={handleAddEnvVar}
                              disabled={!newEnvVarName || newEnvVarName === 'custom' && !newEnvVarValue}
                            >
                              Add Variable
                            </Button>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {/* Existing environment variables */}
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h4 className="font-medium mb-3">Configured Variables</h4>
                      {Object.entries(selectedModule.env_vars).length > 0 ? (
                        <div className="font-mono text-sm grid gap-2">
                          {Object.entries(selectedModule.env_vars).map(([key, value]) => {
                            // Find if this env var is defined in the kit
                            const kitEnvVar = kitEnvironmentVars.find(ev => ev.name === key);
                            
                            return (
                              <div 
                                key={key} 
                                className="group grid grid-cols-[200px_1fr_auto] gap-2 items-baseline hover:bg-gray-100 p-1 rounded"
                              >
                                <div className="flex items-center gap-1">
                                  <span className="text-gray-500">{key}:</span>
                                  {kitEnvVar?.required && (
                                    <TooltipProvider>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <span className="text-red-500">*</span>
                                        </TooltipTrigger>
                                        <TooltipContent>
                                          <p>Required by the kit</p>
                                        </TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  )}
                                </div>
                                {envVarName === key ? (
                                  <div className="flex gap-2 items-baseline">
                                    <Input
                                      size={30}
                                      value={envVarValue}
                                      onChange={(e) => setEnvVarValue(e.target.value)}
                                      className="font-mono h-6 text-sm py-0"
                                    />
                                    <div className="flex gap-1">
                                      <Button 
                                        size="sm" 
                                        variant="outline"
                                        className="h-6 px-2"
                                        onClick={async () => {
                                          await handleEnvVarUpdate();
                                          setEnvVarName('');
                                          setEnvVarValue('');
                                        }}
                                      >
                                        Save
                                      </Button>
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        className="h-6 px-2"
                                        onClick={() => {
                                          setEnvVarName('');
                                          setEnvVarValue('');
                                        }}
                                      >
                                        Cancel
                                      </Button>
                                    </div>
                                  </div>
                                ) : (
                                  <>
                                    <span>{value}</span>
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      className="opacity-0 group-hover:opacity-100 h-6 px-2"
                                      onClick={() => {
                                        setEnvVarName(key);
                                        setEnvVarValue(value);
                                      }}
                                    >
                                      Edit
                                    </Button>
                                  </>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      ) : (
                        <div className="text-center py-2 text-gray-500">
                          No environment variables configured
                        </div>
                      )}
                    </div>
                    
                    {/* Required but unset environment variables */}
                    {unsetEnvVars.length > 0 && (
                      <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
                        <div className="flex items-center gap-2 mb-3">
                          <AlertCircle className="h-5 w-5 text-amber-500" />
                          <h4 className="font-medium">Undefined Variables</h4>
                        </div>
                        <div className="font-mono text-sm grid gap-2">
                          {unsetEnvVars.map(envVar => (
                            <div key={envVar.name} className="group grid grid-cols-[200px_1fr_auto] gap-2 items-baseline hover:bg-amber-100 p-1 rounded">
                              <div className="flex items-center gap-1">
                                <span className="text-gray-600">{envVar.name}:</span>
                                {envVar.required && (
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <span className="text-red-500">*</span>
                                      </TooltipTrigger>
                                      <TooltipContent>
                                        <p>Required by the kit</p>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                )}
                              </div>
                              <span className="text-gray-500 italic">{envVar.default ? `Default: ${envVar.default}` : 'Not set'}</span>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="opacity-0 group-hover:opacity-100 h-6 px-2"
                                onClick={() => {
                                  setIsAddingEnvVar(true);
                                  setNewEnvVarName(envVar.name);
                                  setNewEnvVarValue(envVar.default || '');
                                }}
                              >
                                Set
                              </Button>
                            </div>
                          ))}
                        </div>
                        {unsetEnvVars.some(v => v.required) && (
                          <div className="mt-3 text-sm text-amber-700 flex items-center gap-1">
                            <AlertTriangle className="h-4 w-4" />
                            <span>Some required variables are not set which may cause issues.</span>
                          </div>
                        )}
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
              <AlertDialogContent className='bg-white'>
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
                        await fetchWithAuth(
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
          <Tabs 
            value={selectedResourceType} 
            onValueChange={setSelectedResourceType}
            className="w-auto"
          >
            <TabsList>
              <TabsTrigger value="workspace" className="flex items-center gap-1">
                <Folder className="h-4 w-4" />
                Workspace
              </TabsTrigger>
              <TabsTrigger value="provide-instructions" className="flex items-center gap-1">
                <FileText className="h-4 w-4" />
                Provide Instructions
              </TabsTrigger>
            </TabsList>
          </Tabs>
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
            </div>
          )}
          <div className="flex items-center gap-2">
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
              Provide
            </Button>
          </div>
        </div>
      </div>

      {/* Main content section */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full border rounded">
          <ResizablePanelGroup direction="horizontal" className="h-full">
            <ResizablePanel defaultSize={20} minSize={15}>
              <div className="h-full border-r">
                <ScrollArea className="h-full w-full" scrollHideDelay={0}>
                  {isLoading ? (
                    <div className="p-4">
                      <div className="animate-pulse space-y-2">
                        {[...Array(8)].map((_, i) => (
                          <div key={i} className="h-5 bg-gray-200 rounded"></div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <Tree<TreeItem>
                      data={treeData}
                      width="100%"
                      height={800}
                      indent={16}
                      rowHeight={24}
                      overscanCount={1}
                      openByDefault={false}
                    >
                      {Node}
                    </Tree>
                  )}
                </ScrollArea>
              </div>
            </ResizablePanel>

            <ResizableHandle withHandle />
            <ResizablePanel>
              <div className="h-full overflow-auto">
                {selectedNodeId ? (
                  isLoadingContent ? (
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
                    <FileViewer 
                    key={`${selectedNodeId}-${viewMode}`}
                    content={currentFileContent.data}
                    filePath={selectedNodeId}
                    mimeType={currentFileContent.mimeType || getSelectedFileMimeType() || undefined}
                    viewMode={viewMode}
                    onChange={typeof currentFileContent.data === 'string' ? handleContentChange : undefined}
                    fileSize={currentFileContent.fileSize}
                  />
                  
                  )
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    <div className="text-center p-4">
                      <FileText className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                      <p>Select a file to view its content</p>
                    </div>
                  </div>
                )}
              </div>
            </ResizablePanel>
            {showRelations && (
              <>
                <ResizableHandle withHandle />
                <ResizablePanel defaultSize={30} minSize={10}>
                  <div className="h-full overflow-auto">
                    <RightSidebar selectedModule={selectedModule} />
                  </div>
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