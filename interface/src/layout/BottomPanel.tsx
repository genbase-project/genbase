import { useState, useEffect, useRef } from 'react';
import { useChatPromptStore } from '../stores/chatPromptStore';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Bot, FileText, WorkflowIcon, PackageCheck, GitBranchPlus, Settings, Boxes, Bot as AgentIcon, Expand, Minimize, Check } from 'lucide-react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChatContainer } from '../components/Chat';
import type { Message } from '../components/Chat';
import type { Module } from '../components/TreeView';
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip';
import { ENGINE_BASE_URL } from '@/config';

interface Workflow {
  workflow_type: string;
  agent_type: string;
  base_instructions: string;
  prerequisites: string[];
  metadata: {
    instructions: string;
    actions: any[];
    requirements: string[];
  };
  default_actions: any[];
  is_completed: boolean;
  allow_multiple?: boolean;
}

interface HistoryResponse {
  history: Message[];
  section: string;
  module_id: string;
}

interface BottomPanelProps {
  selectedModule: Module | null;
}

interface Session {
  session_id: string;
  last_message: string;
  last_updated: string;
  is_default: boolean;
}

const BottomPanel = ({ selectedModule }: BottomPanelProps) => {
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [localInputValue, setLocalInputValue] = useState('');
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [currentSection, setCurrentSection] = useState<string>('maintain');
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [completionTime, setCompletionTime] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

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
      }, 3000); // Hide after 3 seconds
    }

    return () => {
      if (timeout) {
        clearTimeout(timeout);
      }
    };
  }, [completionTime]);

  const fetchSessions = async () => {
    if (!selectedModule?.module_id || !currentSection) return;

    try {
      const response = await fetch(
        `${ENGINE_BASE_URL}/workflow/sessions?module_id=${selectedModule.module_id}&workflow=${currentSection}`
      );
      if (response.ok) {
        const data: Session[] = await response.json();
        setSessions(data);
        // If no current session or current session not found, use first available
        if (!currentSession || !data.find(s => s.session_id === currentSession)) {
          setCurrentSession(data[0]?.session_id || null);
        }
      }
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  };

  const fetchWorkflows = async () => {
    if (!selectedModule?.module_id) return;

    try {
      const response = await fetch(
        `${ENGINE_BASE_URL}/workflow/workflows?module_id=${selectedModule.module_id}`
      );
      const data: Workflow[] = await response.json();
      setWorkflows(data);
      
      // Set first workflow as default if none selected
      if (data.length > 0 && !currentSection) {
        setCurrentSection(data[0].workflow_type);
      }
    } catch (error) {
      console.error('Error fetching workflows:', error);
    }
  };

  const fetchHistory = async () => {
    if (!selectedModule?.module_id || !currentSession) return;

    try {
      const url = new URL(`${ENGINE_BASE_URL}/chat/${selectedModule.module_id}/workflow/${currentSection}/history`);
      if (currentSession) {
        url.searchParams.append('session_id', currentSession);
      }
      const response = await fetch(url.toString());
      const data: HistoryResponse = await response.json();
      setMessages(data.history || []);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  useEffect(() => {
    fetchWorkflows();
  }, [selectedModule?.module_id]);

  useEffect(() => {
    if (currentSection) {
      fetchSessions();
    }
  }, [currentSection, selectedModule?.module_id]);

  useEffect(() => {
    if (currentSection) {
      fetchHistory();
    }
  }, [currentSection, selectedModule?.module_id, currentSession]);

  const { inputValue: storeInputValue, setInputValue: setStoreInputValue } = useChatPromptStore();
  
  const handleTextInput = (text: string) => {
    setStoreInputValue(text);
  };

  const handleSend = async (value?: string) => {
    const textToSend = value || storeInputValue;
    if (!textToSend.trim() || !selectedModule?.module_id) return;

    setIsLoading(true);
    if (!value) {
      setStoreInputValue('');
    }
    setError(null);
    try {
      const url = new URL(`${ENGINE_BASE_URL}/chat/${selectedModule.module_id}/execute`);
      const response = await fetch(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section: currentSection,
          input: textToSend,
          session_id: currentSession  || "00000000-0000-0000-0000-000000000000"
        })
      });
      
      if (response.ok) {
        setStoreInputValue('');
        await fetchHistory();
      } else {
        const errorData = await response.json();
        // Handle FastAPI validation error format
        if (errorData.detail && Array.isArray(errorData.detail)) {
          setError(errorData.detail.map((err: { msg: any; }) => err.msg).join(', '));
        } else {
          setError(typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : errorData.detail || 'Failed to send message');
        }
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred while sending message';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Show a message when no module is selected
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
    <div className={`${isFullscreen ? 'fixed inset-4 bg-white shadow-2xl rounded-lg z-50' : 'h-full'} flex overflow-hidden`}>
      <div className={`flex-1 flex flex-col ${isFullscreen ? 'border rounded-l-lg' : 'border-t'} min-w-0`}>
        <ChatContainer 
          messages={messages}
          onSend={(text) => {
            console.log(text);
            if (!isLoading) {
              handleSend(text);
            }
          }}
        />
        
        <div className="p-4 border-t shrink-0">
          <div className="max-w-3xl mx-auto flex gap-2">
            <div className="flex-1">
                <Textarea
                  ref={textareaRef}
                  value={storeInputValue}
                  onChange={(e) => {
                    setStoreInputValue(e.target.value);
                    // Not needed here since useEffect will handle it, but adding for immediate response
                    adjustTextareaHeight();
                  }}
                onKeyDown={(e: React.KeyboardEvent) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    if (!isLoading) {
                      handleSend();
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
              onClick={() => handleSend()}
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

      <div className={`${isFullscreen ? 'w-96' : 'w-80'} border-l ${isFullscreen ? 'rounded-r-lg' : ''} overflow-auto bg-white`}>
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-gray-600">WORKFLOWS</p>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={() => setIsFullscreen(!isFullscreen)}
            >
              {isFullscreen ? (
                <Minimize className="h-3 w-3" />
              ) : (
                <Expand className="h-3 w-3" />
              )}
            </Button>
          </div>
          <div className="space-y-4">
            <Select defaultValue={currentSection} value={currentSection} onValueChange={setCurrentSection}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select workflow" />
              </SelectTrigger>
              <SelectContent>
                {workflows.map((workflow) => (
                  <SelectItem key={workflow.workflow_type} value={workflow.workflow_type}>
                    {workflow.workflow_type}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Keep existing workflow cards but only show selected one */}
            {workflows.filter(workflow => workflow.workflow_type === currentSection).map((workflow) => (
              <Card 
                key={workflow.workflow_type}
                className={`cursor-pointer transition-colors hover:bg-gray-50 ${
                  currentSection === workflow.workflow_type ? 'bg-gray-50 ring-1 ring-gray-200' : ''
                }`}
                onClick={() => setCurrentSection(workflow.workflow_type)}
              >
                <CardContent className="p-2">
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <span className="font-medium text-xs capitalize">{workflow.workflow_type}</span>
                        {workflow.is_completed && (
                          <TooltipProvider>
                            <Tooltip delayDuration={0}>
                              <TooltipTrigger>
                                <Check className="h-3 w-3 text-green-500" />
                              </TooltipTrigger>
                              <TooltipContent>
                                <p>Workflow completed</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </div>
                      <Badge variant="secondary" className="text-[10px] flex items-center gap-1 py-0 h-4">
                        <AgentIcon className="h-2.5 w-2.5" />
                        {workflow.agent_type}
                      </Badge>
                    </div>
                    
                    {workflow.prerequisites.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {workflow.prerequisites.map(prereq => (
                          <Badge key={prereq} variant="outline" className="text-[10px] flex items-center gap-1 py-0 h-4">
                            <GitBranchPlus className="h-2.5 w-2.5" />
                            {prereq}
                          </Badge>
                        ))}
                      </div>
                    )}
                      <div className="pt-1">
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="ghost" size="sm" className="text-[10px] text-gray-500 hover:text-gray-700 h-5 px-2 w-full justify-start">
                          View Details →
                        </Button>
                      </DialogTrigger>
                        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
                          <DialogHeader>
                          <DialogTitle className="flex items-center gap-3">
                            <span className="capitalize">{workflow.workflow_type}</span>
                            {workflow.is_completed && (
                              <Badge variant="default" className="bg-green-100 text-green-700 hover:bg-green-100">
                                Completed
                              </Badge>
                            )}
                            <Badge variant="secondary" className="flex items-center gap-1">
                              <AgentIcon className="h-3 w-3" />
                              {workflow.agent_type}
                            </Badge>
                          </DialogTitle>
                        </DialogHeader>
                        <Tabs defaultValue="instructions" className="flex-1 overflow-hidden">
                          <TabsList className="w-full justify-start mb-4">
                            <TabsTrigger value="instructions" className="flex items-center gap-2">
                              <FileText className="h-3 w-3" />
                              <span>Instructions</span>
                              {(workflow.base_instructions || workflow.metadata.instructions) && (
                                <div className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                              )}
                            </TabsTrigger>
                            <TabsTrigger value="actions" className="flex items-center gap-2">
                              <WorkflowIcon className="h-3 w-3" />
                              <span>Actions</span>
                              {(workflow.metadata.actions.length > 0 || workflow.default_actions.length > 0) && (
                                <Badge variant="secondary" className="ml-1">
                                  {workflow.metadata.actions.length + workflow.default_actions.length}
                                </Badge>
                              )}
                            </TabsTrigger>
                            <TabsTrigger value="requirements" className="flex items-center gap-2">
                              <PackageCheck className="h-3 w-3" />
                              <span>Requirements</span>
                              {workflow.metadata.requirements.length > 0 && (
                                <Badge variant="secondary" className="ml-1">
                                  {workflow.metadata.requirements.length}
                                </Badge>
                              )}
                            </TabsTrigger>
                          </TabsList>
                          <div className="overflow-y-auto pr-6">
                            <TabsContent value="instructions" className="m-0">
                              <div className="space-y-4 pb-4">
                                {workflow.base_instructions && (
                                  <div className="rounded-lg border bg-card text-card-foreground">
                                  <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                                    <FileText className="h-3 w-3 text-gray-600" />
                                    <h3 className="text-sm font-medium">Base Instructions</h3>
                                    </div>
                                    <div className="p-4 text-sm text-gray-600 leading-relaxed">
                                      {workflow.base_instructions}
                                    </div>
                                  </div>
                                )}
                                {workflow.metadata.instructions && (
                                  <div className="rounded-lg border bg-card text-card-foreground">
                                  <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                                    <FileText className="h-3 w-3 text-gray-600" />
                                    <h3 className="text-sm font-medium">Specific Instructions</h3>
                                    </div>
                                    <div className="p-4 text-sm text-gray-600 leading-relaxed">
                                      {workflow.metadata.instructions}
                                    </div>
                                  </div>
                                )}
                              </div>
                            </TabsContent>
                            <TabsContent value="actions" className="m-0">
                              <div className="space-y-4 pb-4">
                                {workflow.metadata.actions.length > 0 && (
                                  <div className="rounded-lg border bg-card text-card-foreground">
                                    <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                                      <div className="flex items-center gap-2">
                                        <Boxes className="h-3 w-3 text-gray-600" />
                                        <h3 className="text-sm font-medium">Custom Actions</h3>
                                      </div>
                                      <Badge variant="default" className="bg-blue-100 text-blue-700 hover:bg-blue-100">
                                        {workflow.metadata.actions.length}
                                      </Badge>
                                    </div>
                                    <div className="divide-y">
                                      {workflow.metadata.actions.map((action, idx) => (
                                        <div key={`metadata-${idx}`} className="p-4">
                                          <p className="text-sm font-medium text-blue-600">{action.name}</p>
                                          {action.description && (
                                            <p className="mt-1 text-sm text-gray-600">{action.description}</p>
                                          )}
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                )}
                                {workflow.default_actions.length > 0 && (
                                  <div className="rounded-lg border bg-card text-card-foreground">
                                    <div className="border-b bg-gray-50 px-4 py-3 flex items-center gap-2">
                                      <div className="flex items-center gap-2">
                                        <Settings className="h-3 w-3 text-gray-600" />
                                        <h3 className="text-sm font-medium">System Actions</h3>
                                      </div>
                                      <Badge variant="default" className="bg-purple-100 text-purple-700 hover:bg-purple-100">
                                        {workflow.default_actions.length}
                                      </Badge>
                                    </div>
                                    <div className="divide-y">
                                      {workflow.default_actions.map((action, idx) => (
                                        <div key={`default-${idx}`} className="p-4">
                                          <p className="text-sm font-medium text-purple-600">{action.name}</p>
                                          {action.description && (
                                            <p className="mt-1 text-sm text-gray-600">{action.description}</p>
                                          )}
                                        </div>
                                      ))}
                                    </div>
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
                                      {workflow.metadata.requirements.length}
                                    </Badge>
                                  </div>
                                  <div className="p-4">
                                    {workflow.metadata.requirements.length > 0 ? (
                                      <div className="flex flex-wrap gap-2">
                                        {workflow.metadata.requirements.map((req, idx) => (
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
                      </Dialog>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
        
            </div>

            {sessions.length > 0 && (
              <div className="mt-6">
                <p className="text-xs font-medium text-gray-600 mb-1">SESSIONS</p>
                    {/* New Session button below workflow card */}
            {workflows.find(w => w.workflow_type === currentSection)?.allow_multiple && (
              <Button
                variant="outline"
                size="sm"
                className="w-full my-2 text-xs"
                onClick={async () => {
                  try {
                    const response = await fetch(
                      `${ENGINE_BASE_URL}/workflow/session/create?module_id=${selectedModule?.module_id}&workflow=${currentSection}`,
                      { method: 'POST' }
                    );
                    if (response.ok) {
                      const data = await response.json();
                      setCurrentSession(data.session_id);
                      await fetchSessions(); // Refresh sessions list
                    }
                  } catch (error) {
                    console.error('Error creating session:', error);
                  }
                }}
              >
                New Session +
              </Button>
            )}
                <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
                  {sessions.map((session) => (
                    <Card
                      key={session.session_id}
                      className={`cursor-pointer transition-colors hover:bg-gray-50 ${
                        currentSession === session.session_id ? 'bg-gray-50 ring-1 ring-gray-200' : ''
                      }`}
                      onClick={() => setCurrentSession(session.session_id)}
                    >
                      <CardContent className="p-2">
                <div className="space-y-1.5">
                          <div className="flex items-center justify-between">
                            <Badge
                              variant={session.is_default ? "secondary" : "outline"}
                              className="text-[10px]"
                            >
                              {session.is_default ? "Default Session" : new Date(session.last_updated).toLocaleString()}
                            </Badge>
                          </div>
                          <p className="text-xs text-gray-600 truncate">{session.last_message}</p>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
  );


};

export default BottomPanel;
