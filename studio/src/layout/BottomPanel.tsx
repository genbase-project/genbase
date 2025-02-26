import { useState, useEffect, useRef } from 'react';
import { useChatPromptStore } from '../stores/chatPromptStore';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { 
  Send, 
  Bot, 
  FileText, 
  WorkflowIcon, 
  PackageCheck, 
  Settings, 
  Boxes, 
  Bot as AgentIcon, 
  Expand, 
  Minimize, 
  Check, 
  MessageSquare,
  ChevronDown,
  Plus,
  ChevronRight,
  ChevronLeft,
  X,
  BadgeInfo
} from 'lucide-react';
import { ChatContainer } from '../components/Chat';
import type { Module } from '../components/TreeView';
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  Tooltip, 
  TooltipContent, 
  TooltipTrigger, 
  TooltipProvider 
} from '@/components/ui/tooltip';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
import { useChatStore } from '@/stores/chatStore';
// Add before the BottomPanel component function
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString();
};

const truncateText = (text: string, maxLength: number = 30) => {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};
interface Workflow {
  workflow_type: string;
  agent_type: string;
  base_instructions: string;
  metadata: {
    instructions: string;
    actions: Array<{
      action?: {
        path: string;
        name: string;
        description: string;
        full_file_path?: string;
        function_name?: string;
      };
    }>;
    requirements: string[];
  };
  default_actions: any[];
  kit_config?: {
    agent: string;
    instruction: string;
    actions: Array<{
      path: string;
      name: string;
      description: string;
    }>;
    allow_multiple: boolean;
  };
  allow_multiple?: boolean;
}


interface Session {

session_id: string;

last_message: string;

last_updated: string;

is_default: boolean;

}
interface BottomPanelProps {
  selectedModule: Module | null;
  onMaximize: (isMaximized: boolean) => void;
  isMaximized: boolean;
}

// Then in your component:
const BottomPanel = ({ selectedModule, onMaximize, isMaximized }: BottomPanelProps) => {

  const [expansionState, setExpansionState] = useState<'default' | 'maximized' | 'fullscreen'>('default');

const [localInputValue, setLocalInputValue] = useState('');

const [workflows, setWorkflows] = useState<Workflow[]>([]);

const [currentWorkflow, setCurrentWorkflow] = useState<string>('maintain');

const [currentSession, setCurrentSession] = useState<string | null>(null);

const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);

const [sessions, setSessions] = useState<Session[]>([]);

const [error, setError] = useState<string | null>(null);

const [elapsedTime, setElapsedTime] = useState<number>(0);

const [completionTime, setCompletionTime] = useState<string | null>(null);
const [isWorkflowDetailsOpen, setIsWorkflowDetailsOpen] = useState(false);
const [isFullscreen, setIsFullscreen] = useState(false);


// Replace any references to tabsContainerRef with:
const tabsRef = useRef<HTMLDivElement>(null);

// Replace the scrollLeft and scrollRight functions with these:
const scrollLeft = () => {
  if (tabsRef.current) {
    tabsRef.current.scrollBy({ left: -100, behavior: 'smooth' });
  }
};

const scrollRight = () => {
  if (tabsRef.current) {
    tabsRef.current.scrollBy({ left: 100, behavior: 'smooth' });
  }
};

const textareaRef = useRef<HTMLTextAreaElement>(null);

const {

messages,

isLoading,

setCurrentContext,

refreshChat,

sendMessage

} = useChatStore();

useEffect(() => {

if (selectedModule?.module_id && currentWorkflow && currentSession && !pendingSessionId) {

setCurrentContext(

selectedModule.module_id,

currentWorkflow,

currentSession

);

refreshChat();

}

}, [selectedModule?.module_id, currentWorkflow, currentSession, pendingSessionId]);

const adjustTextareaHeight = () => {

const textarea = textareaRef.current;

if (textarea) {

textarea.style.height = 'auto';

textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;

}

};

useEffect(() => {

adjustTextareaHeight();

}, [localInputValue]);

// Update elapsed time while loading

useEffect(() => {

let interval: NodeJS.Timeout;

if (isLoading) {

interval = setInterval(() => {

setElapsedTime(prev => prev + 0.1);

}, 100);

} else if (!completionTime) {

const finalTime = elapsedTime;

setCompletionTime(`Completed in ${finalTime.toFixed(1)}s`);

setElapsedTime(0);

}

return () => {

if (interval) {

clearInterval(interval);

}

};

}, [isLoading]);

useEffect(() => {

let timeout: NodeJS.Timeout;

if (completionTime) {

timeout = setTimeout(() => {

setCompletionTime(null);

setElapsedTime(0);

}, 3000);

}

return () => {

if (timeout) {

clearTimeout(timeout);

}

};

}, [completionTime]);

const fetchSessions = async () => {

if (!selectedModule?.module_id || !currentWorkflow) return;

try {

const response = await fetchWithAuth(

`${ENGINE_BASE_URL}/workflow/sessions?module_id=${selectedModule.module_id}&workflow=${currentWorkflow}`

);

if (response.ok) {

const data: Session[] = await response.json();

setSessions(data);

if (!currentSession || !data.find(s => s.session_id === currentSession)) {

const defaultSession = data.find(s => s.is_default);

setCurrentSession(defaultSession?.session_id || data[0]?.session_id || null);

}

}

} catch (error) {

console.error('Error fetching sessions:', error);

}

};

// Update the fetchWorkflows function and its useEffect

const fetchWorkflows = async () => {
  if (!selectedModule?.module_id) return;
  
  try {
    const response = await fetchWithAuth(
      `${ENGINE_BASE_URL}/workflow/workflows?module_id=${selectedModule.module_id}`
    );
    
    const data: Workflow[] = await response.json();
    setWorkflows(data);
    
    // Automatically select the first workflow if none is selected
    if (data.length > 0) {
      // Only set if currentWorkflow is empty or not in the list of available workflows
      const workflowExists = data.some(w => w.workflow_type === currentWorkflow);
      if (!currentWorkflow || !workflowExists) {
        setCurrentWorkflow(data[0].workflow_type);
      }
    }
  } catch (error) {
    console.error('Error fetching workflows:', error);
  }
};

useEffect(() => {
  // Reset workflow when module changes to ensure proper selection
  setCurrentWorkflow('');
  fetchWorkflows();
}, [selectedModule?.module_id]);


useEffect(() => {

if (currentWorkflow) {

fetchSessions();

}

}, [currentWorkflow, selectedModule?.module_id]);

const { inputValue: storeInputValue, setInputValue: setStoreInputValue } = useChatPromptStore();

const handleSend = async (text: string) => {

if (!text.trim()) return;


if (pendingSessionId) {

try {

const response = await fetchWithAuth(

`${ENGINE_BASE_URL}/workflow/session/create?module_id=${selectedModule?.module_id}&workflow=${currentWorkflow}`,

{ method: 'POST' }

);

if (response.ok) {

const data = await response.json();

setCurrentSession(data.session_id);

setPendingSessionId(null);

await fetchSessions();

}

} catch (error) {

console.error('Error creating session:', error);

return;

}

}

await sendMessage(text);

};

  // Get current workflow details
  const currentWorkflowData = workflows.find(w => w.workflow_type === currentWorkflow);
  
  // Get current session details
  const currentSessionData = sessions.find(s => s.session_id === currentSession);


  const toggleExpansion = () => {
    if (expansionState === 'default') {
      setExpansionState('maximized');
      onMaximize?.(true); // Tell parent to maximize the panel
    } 
    else if (expansionState === 'maximized') {
      setExpansionState('fullscreen');
      onMaximize?.(false); // Tell parent to restore original size
    }
    else {
      setExpansionState('default');
      onMaximize?.(false); // Tell parent to restore original size
    }
  };


  if (!selectedModule) {
    return (
      <div className="h-full flex flex-col items-center justify-center space-y-4 text-gray-500">
        <Bot className="w-12 h-12 text-gray-400 mb-2" strokeWidth={1.5} />
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-700 mb-1">No Module Selected</h3>
          <p className="text-sm text-gray-500">Select a module from the sidebar to begin</p>
        </div>
      </div>
    );
  }

  return (
<div className={`${isFullscreen ? 'fixed inset-4 bg-white shadow-2xl rounded-lg z-50' : 'h-full'} flex flex-col overflow-hidden`}>

      {/* Improved Top Bar with Workflow Selector and Session Tabs */}
      <div className={`border-b bg-gray-50 ${isFullscreen ? 'rounded-t-lg' : ''} flex flex-col`}>

        {/* Workflow Selector Row */}
        <div className="px-4 py-2 flex items-center gap-2 border-b">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Dialog open={isWorkflowDetailsOpen} onOpenChange={setIsWorkflowDetailsOpen}>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        className="flex items-center gap-2 h-8 bg-white shadow-sm hover:bg-gray-50"
                      >
                        <AgentIcon className="h-3.5 w-3.5 text-blue-500" />
                        <span className="capitalize font-medium truncate">
                          {currentWorkflow}
                        </span>
                        <ChevronDown className="h-3.5 w-3.5 opacity-70" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-[180px]">
                      {workflows.map((workflow) => (
                        <DropdownMenuItem 
                          key={workflow.workflow_type}
                          className="flex items-center justify-between gap-2 capitalize"
                          onClick={() => setCurrentWorkflow(workflow.workflow_type)}
                        >
                          <span className="truncate">{workflow.workflow_type}</span>
                  
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>

                  {currentWorkflowData && (
                    <DialogTrigger asChild>
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="ml-1 h-8 w-8 p-0" 
                        title="View workflow details"
                      >
                        <BadgeInfo className="h-3.5 w-3.5 text-gray-500" />
                      </Button>
                    </DialogTrigger>
                  )}

{currentWorkflowData && (
  <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
    <DialogHeader>
      <DialogTitle className="flex items-center gap-3">
        <span className="capitalize">{currentWorkflowData.workflow_type}</span>
        {currentWorkflowData.agent_type && (
          <Badge variant="secondary" className="flex items-center gap-1">
            <AgentIcon className="h-3 w-3" />
            {currentWorkflowData.agent_type}
          </Badge>
        )}
        {currentWorkflowData.kit_config?.agent && !currentWorkflowData.agent_type && (
          <Badge variant="secondary" className="flex items-center gap-1">
            <AgentIcon className="h-3 w-3" />
            {currentWorkflowData.kit_config.agent}
          </Badge>
        )}
      </DialogTitle>
    </DialogHeader>
    <Tabs defaultValue="instructions" className="flex-1 overflow-hidden">
      <TabsList className="w-full justify-start mb-4">
        <TabsTrigger value="instructions" className="flex items-center gap-2">
          <FileText className="h-3 w-3" />
          <span>Instructions</span>
          {(currentWorkflowData.base_instructions || currentWorkflowData.metadata.instructions) && (
            <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
          )}
        </TabsTrigger>
        <TabsTrigger value="actions" className="flex items-center gap-2">
          <WorkflowIcon className="h-3 w-3" />
          <span>Actions</span>
          {(currentWorkflowData.metadata.actions.length > 0 || currentWorkflowData.default_actions.length > 0) && (
            <Badge variant="secondary" className="ml-1">
              {currentWorkflowData.metadata.actions.length + currentWorkflowData.default_actions.length}
            </Badge>
          )}
        </TabsTrigger>
        <TabsTrigger value="requirements" className="flex items-center gap-2">
          <PackageCheck className="h-3 w-3" />
          <span>Requirements</span>
          {currentWorkflowData.metadata.requirements.length > 0 && (
            <Badge variant="secondary" className="ml-1">
              {currentWorkflowData.metadata.requirements.length}
            </Badge>
          )}
        </TabsTrigger>
      </TabsList>
      <div className="overflow-y-auto pr-6">
        <TabsContent value="instructions" className="m-0">
          <div className="space-y-4 pb-4">
            {currentWorkflowData.base_instructions && (
              <div className="rounded-lg border bg-card text-card-foreground">
                <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                  <FileText className="h-3 w-3 text-gray-600" />
                  <h3 className="text-sm font-medium">Base Instructions</h3>
                </div>
                <div className="p-4 text-sm text-gray-600 leading-relaxed">
                  {currentWorkflowData.base_instructions}
                </div>
              </div>
            )}
            {currentWorkflowData.metadata.instructions && (
              <div className="rounded-lg border bg-card text-card-foreground">
                <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                  <FileText className="h-3 w-3 text-gray-600" />
                  <h3 className="text-sm font-medium">Specific Instructions</h3>
                </div>
                <div className="p-4 text-sm text-gray-600 leading-relaxed">
                  {currentWorkflowData.metadata.instructions}
                </div>
              </div>
            )}
            {!currentWorkflowData.base_instructions && !currentWorkflowData.metadata.instructions && (
              <div className="p-4 text-sm text-gray-500 text-center">
                No instructions provided for this workflow.
              </div>
            )}
          </div>
        </TabsContent>
        <TabsContent value="actions" className="m-0">
          <div className="space-y-4 pb-4">
            {currentWorkflowData.metadata.actions.length > 0 && (
              <div className="rounded-lg border bg-card text-card-foreground">
                <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                  <div className="flex items-center gap-2">
                    <Boxes className="h-3 w-3 text-gray-600" />
                    <h3 className="text-sm font-medium">Custom Actions</h3>
                  </div>
                  <Badge variant="default" className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                    {currentWorkflowData.metadata.actions.length}
                  </Badge>
                </div>
                <div className="divide-y">
                  {currentWorkflowData.metadata.actions.map((actionItem, idx) => {
                    const action = actionItem.action! || {};
                    return (
                      <div key={`metadata-${idx}`} className="p-4">
                        <p className="text-sm font-medium text-blue-600">
                          {action!.name! || "Unnamed Action"}
                        </p>
                        {(action.description) && (
                          <p className="mt-1 text-sm text-gray-600">
                            {action.description}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {currentWorkflowData.default_actions.length > 0 && (
              <div className="rounded-lg border bg-card text-card-foreground">
                <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                  <div className="flex items-center gap-2">
                    <Settings className="h-3 w-3 text-gray-600" />
                    <h3 className="text-sm font-medium">System Actions</h3>
                  </div>
                  <Badge variant="default" className="bg-purple-100 text-purple-700 hover:bg-purple-100">
                    {currentWorkflowData.default_actions.length}
                  </Badge>
                </div>
                <div className="divide-y">
                  {currentWorkflowData.default_actions.map((action, idx) => (
                    <div key={`default-${idx}`} className="p-4">
                      <p className="text-sm font-medium text-purple-600">{action.name || "Unnamed Action"}</p>
                      {action.description && (
                        <p className="mt-1 text-sm text-gray-600">{action.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
            {currentWorkflowData.metadata.actions.length === 0 && currentWorkflowData.default_actions.length === 0 && (
              <div className="p-4 text-sm text-gray-500 text-center">
                No actions available for this workflow.
              </div>
            )}
          </div>
        </TabsContent>
        <TabsContent value="requirements" className="m-0">
          <div className="space-y-4 pb-4">
            <div className="rounded-lg border bg-card text-card-foreground">
              <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                <div className="flex items-center gap-2">
                  <PackageCheck className="h-3 w-3 text-gray-600" />
                  <h3 className="text-sm font-medium">Requirements</h3>
                </div>
                <Badge variant="default" className="bg-gray-100 text-gray-700 hover:bg-gray-100">
                  {currentWorkflowData.metadata.requirements.length}
                </Badge>
              </div>
              <div className="p-4">
                {currentWorkflowData.metadata.requirements.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {currentWorkflowData.metadata.requirements.map((req, idx) => (
                      <Badge key={idx} variant="outline" className="flex items-center gap-1.5 px-3 py-1">
                        <PackageCheck className="h-3 w-3" />
                        {req}
                      </Badge>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500">No requirements specified</p>
                )}
              </div>
            </div>
          </div>
        </TabsContent>
      </div>
    </Tabs>
  </DialogContent>
)}

                </Dialog>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p>Select workflow</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          
          <div className="flex-1"></div>
          

  <Button
    variant="ghost"
    size="sm"
    className="h-8 w-8 p-0"
    onClick={() => {
      if (!isMaximized && !isFullscreen) {
        // If in normal mode, maximize
        onMaximize(true);
        console.log('Maximize');
      } else if (isMaximized && !isFullscreen) {
        // If maximized but not fullscreen, go fullscreen
        setIsFullscreen(true);
        onMaximize(false); // Restore panel size when going fullscreen
        console.log('Fullscreen');
      } else {
        // If fullscreen, go back to normal
        setIsFullscreen(false);
        onMaximize(false);
        console.log('Normal');
      }
    }}
    title={
      !isMaximized && !isFullscreen 
        ? "Maximize height" 
        : isMaximized && !isFullscreen 
          ? "Enter fullscreen" 
          : "Exit fullscreen"
    }
  >
    {isFullscreen ? (
      <Minimize className="h-4 w-4" />
    ) : (
      <Expand className="h-4 w-4" />
    )}
  </Button>


        </div>
        
        {/* Chrome-like Session Tabs */}
        <div className="relative flex items-center">
          {/* Left scroll button */}
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-8 w-8 p-0 flex-shrink-0 rounded-none border-r"
            onClick={scrollLeft}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          
          {/* Scrollable tabs container */}
          <div 
            ref={tabsRef}
            className="flex-1 overflow-x-auto scrollbar-hide flex items-center"
            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          >
            {/* New Session Tab */}
            {currentWorkflowData?.allow_multiple && (
              <Button
                variant={pendingSessionId ? "secondary" : "ghost"}
                size="sm"
                className={`h-9 rounded-none border-r px-3 flex items-center gap-1.5 ${
                  pendingSessionId ? 'bg-blue-50 text-blue-700 border-b-2 border-b-blue-500' : 'hover:bg-gray-100'
                }`}
                onClick={() => {
                  setPendingSessionId('pending');
                  setCurrentSession(null);
                }}
              >
                <Plus className="h-3.5 w-3.5" />
                <span className="text-xs font-medium">New Session</span>
              </Button>
            )}
            
            {/* Session tabs */}
            {sessions.map((session) => {
              const isActive = currentSession === session.session_id;
              return (
                <div 
                  key={session.session_id}
                  className={`flex items-center h-9 px-3 border-r cursor-pointer group ${
                    isActive 
                      ? 'bg-white border-b-2 border-b-blue-500' 
                      : 'hover:bg-gray-100'
                  }`}
                  onClick={() => {
                    setPendingSessionId(null);
                    setCurrentSession(session.session_id);
                  }}
                >
                  <div className="flex items-center gap-2 max-w-xs">
                    <MessageSquare className="h-3 w-3 text-gray-500 flex-shrink-0" />
                    <div className="flex flex-col">
                      <span className="text-xs font-medium truncate">
                        {session.is_default ? "Default Session" : formatDate(session.last_updated)}
                      </span>
                      <span className="text-xs text-gray-500 truncate">
                        {truncateText(session.last_message, 20)}
                      </span>
                    </div>
                  </div>
                  {/* Close button - shows on hover */}
                  {!session.is_default && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-5 w-5 p-0 ml-2 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation();
                        // Handle closing session (add this functionality)
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
          
          {/* Right scroll button */}
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-8 w-8 p-0 flex-shrink-0 rounded-none border-l"
            onClick={scrollRight}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {pendingSessionId ? (
          <div className="flex-1 h-full flex flex-col items-center justify-center space-y-4 text-gray-500">
            <MessageSquare className="w-12 h-12 text-gray-400 mb-2" strokeWidth={1.5} />
            <div className="text-center">
              <h3 className="text-lg font-medium text-gray-700 mb-1">New Conversation</h3>
              <p className="text-sm text-gray-500">Type a message to start the conversation</p>
            </div>
          </div>
        ) : (
          <div className="h-full overflow-y-auto" id="chat-scroll-container">

          <ChatContainer messages={messages} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t shrink-0">
        <div className="max-w-3xl mx-auto flex gap-2">
          <div className="flex-1">
            <Textarea
              ref={textareaRef}
              value={storeInputValue}
              onChange={(e) => {
                setStoreInputValue(e.target.value);
                adjustTextareaHeight();
              }}
              onKeyDown={(e: React.KeyboardEvent) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  if (!isLoading) {
                    handleSend(storeInputValue);
                    setStoreInputValue('');
                  }
                }
              }}
              placeholder="Send a message... (Shift+Enter for new line)"
              disabled={isLoading}
              className={`w-full resize-none min-h-[40px] max-h-[200px] ${error ? 'border-red-500' : ''}`}
              rows={1}
              style={{
                height: 'auto',
                overflow: 'hidden'
              }}
            />
            {error ? (
              <div className="mt-1 text-sm text-red-600">{error}</div>
            ) : completionTime && (
              <div className="mt-1 text-xs text-gray-600">{completionTime}</div>
            )}
          </div>
          <Button
            onClick={() => {
              handleSend(storeInputValue);
              setStoreInputValue('');
            }}
            disabled={isLoading}
            variant="secondary"
          >
            {isLoading ? (
              <div className="flex items-center gap-2">
                <div className="w-4 h-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                <span className="text-xs text-gray-600 w-10">{elapsedTime.toFixed(1)}s</span>
              </div>
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default BottomPanel;