// BottomPanel.tsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { useChatPromptStore } from '@/stores/chatPromptStore';
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Send,
  Bot,
  BotMessageSquare,
  PackageCheck,
  Boxes,
  Bot as AgentIcon,
  Expand,
  Minimize,
  MessageSquare,
  ChevronDown,
  Plus,
  ChevronRight,
  ChevronLeft,
  BadgeInfo,
  Loader2,
  AlertCircle,
  ArrowUp // Use ArrowUp icon like Grok? Or keep Send
} from 'lucide-react';
import { StreamingChatContainer, Message } from '@/components/StreamingChatContainer';
import type { Module } from '@/components/TreeView';
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider
} from "@/components/ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { ENGINE_BASE_URL, fetchWithAuth } from '@/config';
import type { KitInstruction } from '@/app/registry/RegistryPage';
import { Alert, AlertDescription } from "@/components/ui/alert";

// --- Interfaces (Profile, Session) ---
interface Profile {
  profile_type: string;
  agent_type: string;
  metadata: {
    instructions?: Array<KitInstruction>;
    tools: Array<{
      tool?: {
        path: string;
        name: string;
        description: string;
        full_file_path?: string;
        function_name?: string;
      };
    }>;
    requirements: string[];
  };
  kit_config?: {
    agent: string;
    instruction: string;
    tools: Array<{
      path: string;
      name: string;
      description: string;
    }>;
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

// --- Helper Functions ---
const formatDate = (dateString: string) => {
  if (!dateString || isNaN(new Date(dateString).getTime())) {
    return "Invalid Date";
  }
  return new Date(dateString).toLocaleString();
};

const truncateText = (text: string, maxLength: number = 30) => {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
};


// --- Component ---
const BottomPanel = ({ selectedModule, onMaximize, isMaximized }: BottomPanelProps) => {
  // UI State
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isProfileDetailsOpen, setIsProfileDetailsOpen] = useState(false);

  // Data State
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [currentProfile, setCurrentProfile] = useState<string>('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [pendingSessionId, setPendingSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // References
  const tabsRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Zustand store for input value
  const { inputValue: storeInputValue, setInputValue: setStoreInputValue } = useChatPromptStore();

  // Scrolling functions for tabs
  const scrollLeft = () => {
    tabsRef.current?.scrollBy({ left: -100, behavior: 'smooth' });
  };

  const scrollRight = () => {
    tabsRef.current?.scrollBy({ left: 100, behavior: 'smooth' });
  };

  // Adjust textarea height dynamically
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const scrollHeight = textarea.scrollHeight;
      // Ensure minimum height matches initial rows prop if needed, e.g., 40px for rows={1}
      const minHeight = 40;
      textarea.style.height = `${Math.max(minHeight, Math.min(scrollHeight, 200))}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [storeInputValue]);

  // Fetch profiles when module changes
  useEffect(() => {
    setCurrentProfile('');
    setSessions([]);
    setCurrentSession(null);
    setPendingSessionId(null);
    setChatMessages([]);
    setError(null);

    if (selectedModule?.module_id) {
      fetchProfiles();
    } else {
        setProfiles([]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedModule?.module_id]);

  // Fetch sessions when profile changes (and module exists)
  useEffect(() => {
    setSessions([]);
    setCurrentSession(null);
    setPendingSessionId(null);
    setChatMessages([]);

    if (currentProfile && selectedModule?.module_id) {
      fetchSessions();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProfile, selectedModule?.module_id]);


  const fetchProfiles = async () => {
    if (!selectedModule?.module_id) return;
    try {
      setError(null);
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/profile/profiles?module_id=${selectedModule.module_id}`
      );
      const data: Profile[] = await response.json();
      setProfiles(data);

      if (data.length > 0 && !currentProfile) {
          setCurrentProfile(data[0].profile_type);
      } else if (data.length === 0) {
          setCurrentProfile('');
      }
    } catch (error) {
      console.error('Error fetching profiles:', error);
      setError(`Failed to load profiles: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setProfiles([]);
      setCurrentProfile('');
    }
  };

  const fetchSessions = async () => {
    if (!selectedModule?.module_id || !currentProfile) return;
    try {
      setError(null);
      const response = await fetchWithAuth(
        `${ENGINE_BASE_URL}/profile/sessions?module_id=${selectedModule.module_id}&profile=${currentProfile}`
      );

      const data: Session[] = await response.json();
      setSessions(data);

      const defaultSession = data.find(s => s.is_default);
      const firstSession = data[0];
      const sessionToSelect = defaultSession || firstSession;

      if (sessionToSelect) {
          setCurrentSession(sessionToSelect.session_id);
          setPendingSessionId(null);
      } else {
          const profileData = profiles.find(p => p.profile_type === currentProfile);
          if (profileData?.allow_multiple) {
              setPendingSessionId('pending');
              setCurrentSession(null);
          } else {
              setCurrentSession(null);
              setPendingSessionId(null);
          }
      }

    } catch (error) {
      console.error('Error fetching sessions:', error);
      setError(`Failed to load sessions: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setSessions([]);
      setCurrentSession(null);
      setPendingSessionId(null);
    }
  };

  const createNewSession = async (): Promise<string | null> => {
     if (!selectedModule?.module_id || !currentProfile) {
         setError("Cannot create session: Module or profile not selected.");
         return null;
     }
     setIsLoading(true);
     setError(null);
     try {
         const response = await fetchWithAuth(
             `${ENGINE_BASE_URL}/profile/session/create?module_id=${selectedModule.module_id}&profile=${currentProfile}`,
             { method: 'POST' }
         );
         const data = await response.json();
         await fetchSessions();
         if (!currentSession && data.session_id) {
            setCurrentSession(data.session_id);
            setPendingSessionId(null);
         }
         return data.session_id;
     } catch (error) {
         console.error('Error creating session:', error);
         setError(`Could not create new session: ${error instanceof Error ? error.message : 'Unknown error'}`);
         setPendingSessionId('pending');
         return null;
     } finally {
         setIsLoading(false);
     }
  };


  const handleSend = async (text: string) => {
    const trimmedText = text.trim();
    if (!trimmedText) return;
    if (!selectedModule?.module_id || !currentProfile) {
      setError("Cannot send message: Module or profile not selected.");
      return;
    }

    setError(null);
    setIsLoading(true);

    let targetSessionId = currentSession;

    if (pendingSessionId) {
        targetSessionId = await createNewSession();
        if (!targetSessionId) {
            setIsLoading(false);
            return;
        }
    }

    if (!targetSessionId) {
        setError("Cannot send message: No active session.");
        setIsLoading(false);
        return;
    }

    try {
      const url = new URL(`${ENGINE_BASE_URL}/chat/${selectedModule.module_id}/execute`);
      await fetchWithAuth(url.toString(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          profile: currentProfile,
          input: trimmedText,
          session_id: targetSessionId
        })
      });
      setStoreInputValue('');
      // Trigger height adjustment after clearing input
      requestAnimationFrame(() => adjustTextareaHeight());
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An unknown error occurred';
      setError(`Failed to send message: ${errorMessage}`);
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleMessagesUpdate = useCallback((messages: Message[]) => {
    setChatMessages(messages);
  }, [setChatMessages]);

  const currentProfileData = profiles.find(w => w.profile_type === currentProfile);

  const toggleViewMode = () => {
    if (!isMaximized && !isFullscreen) {
      onMaximize(true);
    } else if (isMaximized && !isFullscreen) {
      setIsFullscreen(true);
    } else {
      setIsFullscreen(false);
    }
  };


  // Render Loading or No Module Selected states
  if (!selectedModule) {
    return (
      <div className="h-full flex flex-col items-center justify-center space-y-4 text-gray-500">
        <Bot className="w-12 h-12 text-gray-400 mb-2" strokeWidth={1.5} />
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-700 mb-1">No Module Selected</h3>
          <p className="text-sm text-gray-500">Select a module from the sidebar</p>
        </div>
      </div>
    );
  }

  // Determine if send button should be enabled
  const canSend = !isLoading && !!storeInputValue.trim() && !!currentProfile && (!!currentSession || !!pendingSessionId);

  // Main Render
  return (
    <div className={`${isFullscreen ? 'fixed inset-4 bg-white shadow-2xl rounded-lg z-50' : 'h-full'} flex flex-col overflow-hidden border border-gray-200`}>
      {/* Top Bar */}
      <div className={`border-b bg-gray-50 ${isFullscreen ? 'rounded-t-lg' : ''} flex flex-col shrink-0`}>
        {/* Profile Selector Row */}
        <div className="px-4 py-2 flex items-center gap-2 border-b">
           <TooltipProvider delayDuration={300}>
             <Tooltip>
               <TooltipTrigger asChild>
                 <Dialog open={isProfileDetailsOpen} onOpenChange={setIsProfileDetailsOpen}>
                   <DropdownMenu>
                     <DropdownMenuTrigger asChild>
                       <Button
                         variant="outline"
                         size="sm"
                         className="flex items-center gap-2 h-8 bg-white shadow-sm hover:bg-gray-50"
                         disabled={profiles.length === 0 && !selectedModule}
                       >
                         <AgentIcon className="h-3.5 w-3.5 text-blue-500" />
                         <span className="capitalize font-medium truncate max-w-[120px]">
                           {currentProfile || (profiles.length === 0 ? "Loading..." : "Select Profile")}
                         </span>
                         <ChevronDown className="h-3.5 w-3.5 opacity-70 ml-auto" />
                       </Button>
                     </DropdownMenuTrigger>
                     <DropdownMenuContent align="start" className="w-[180px]">
                       {profiles.length === 0 && <DropdownMenuItem disabled>No profiles found</DropdownMenuItem>}
                       {profiles.map((profile) => (
                         <DropdownMenuItem
                           key={profile.profile_type}
                           className="flex items-center justify-between gap-2 capitalize"
                           onClick={() => setCurrentProfile(profile.profile_type)}
                         >
                           <span className="truncate">{profile.profile_type}</span>
                         </DropdownMenuItem>
                       ))}
                     </DropdownMenuContent>
                   </DropdownMenu>

                   {currentProfileData && (
                     <DialogTrigger asChild>
                       <Button
                         variant="ghost"
                         size="icon"
                         className="ml-1 h-8 w-8 p-0"
                         onClick={() => setIsProfileDetailsOpen(true)}
                         title="View profile details"
                       >
                         <BadgeInfo className="h-4 w-4 text-gray-500" />
                       </Button>
                     </DialogTrigger>
                   )}

                   {/* Profile Details Dialog Content */}
                   {currentProfileData && (
                     <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col p-0">
                       <DialogHeader className="p-6 pb-4 border-b">
                         <DialogTitle className="flex items-center gap-3">
                           <span className="capitalize">{currentProfileData.profile_type} Profile</span>
                            {currentProfileData.agent_type && (
                                <Badge variant="secondary" className="flex items-center gap-1 text-xs">
                                <AgentIcon className="h-3 w-3" />
                                {currentProfileData.agent_type}
                                </Badge>
                            )}
                            {currentProfileData.kit_config?.agent && !currentProfileData.agent_type && (
                                <Badge variant="secondary" className="flex items-center gap-1 text-xs">
                                <AgentIcon className="h-3 w-3" />
                                {currentProfileData.kit_config.agent} (Kit)
                                </Badge>
                            )}
                         </DialogTitle>
                       </DialogHeader>
                        <Tabs defaultValue="tools" className="flex-1 overflow-hidden flex flex-col">
                           <div className="px-6 pt-4">
                             <TabsList className="grid w-full grid-cols-2">
                               <TabsTrigger value="tools" className="text-xs flex items-center justify-center gap-1">
                                    <BotMessageSquare className="h-3.5 w-3.5"/> Tools ({currentProfileData.metadata?.tools?.length ?? 0})
                               </TabsTrigger>
                               <TabsTrigger value="requirements" className="text-xs flex items-center justify-center gap-1">
                                    <PackageCheck className="h-3.5 w-3.5"/> Requirements ({currentProfileData.metadata?.requirements?.length ?? 0})
                                </TabsTrigger>
                             </TabsList>
                           </div>
                           <div className="flex-1 overflow-y-auto p-6 pt-4">
                             <TabsContent value="tools" className="m-0 space-y-3">
                               {(currentProfileData.metadata?.tools ?? []).length > 0 ? (
                                 currentProfileData.metadata.tools.map((toolItem, idx) => {
                                   const tool = toolItem.tool;
                                   if (!tool) return null;
                                   return (
                                     <div key={`tool-${idx}`} className="p-3 border rounded-md bg-gray-50/50">
                                       <p className="text-sm font-medium text-blue-700 flex items-center gap-1.5">
                                          <BotMessageSquare className="h-3.5 w-3.5"/>
                                          {tool.name || "Unnamed Tool"}
                                       </p>
                                       {tool.description && (
                                         <p className="mt-1 text-xs text-gray-600 pl-5">
                                           {tool.description}
                                         </p>
                                       )}
                                     </div>
                                   );
                                 })
                               ) : (
                                 <p className="text-sm text-gray-500 text-center py-6 italic">No tools defined for this profile.</p>
                               )}
                             </TabsContent>
                             <TabsContent value="requirements" className="m-0">
                               { (currentProfileData.metadata?.requirements ?? []).length > 0 ? (
                                 <div className="flex flex-wrap gap-2 pt-2">
                                   {currentProfileData.metadata.requirements.map((req, idx) => (
                                     <Badge key={`req-${idx}`} variant="outline" className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-normal">
                                       <PackageCheck className="h-3.5 w-3.5" />
                                       {req}
                                     </Badge>
                                   ))}
                                 </div>
                               ) : (
                                 <p className="text-sm text-gray-500 text-center py-6 italic">No requirements specified.</p>
                               )}
                             </TabsContent>
                           </div>
                        </Tabs>
                     </DialogContent>
                   )}
                 </Dialog>
               </TooltipTrigger>
               <TooltipContent side="bottom">
                 <p>{currentProfile ? `View/Switch Profile (${currentProfile})` : "Select Profile"}</p>
               </TooltipContent>
             </Tooltip>
           </TooltipProvider>

          <div className="flex-1"></div>

          <TooltipProvider delayDuration={300}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 p-0"
                  onClick={toggleViewMode}
                >
                  {isFullscreen ? <Minimize className="h-4 w-4" /> : <Expand className="h-4 w-4" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                <p>
                  {!isMaximized && !isFullscreen
                    ? "Maximize"
                    : isMaximized && !isFullscreen
                      ? "Fullscreen"
                      : "Exit Fullscreen"}
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        {/* Session Tabs Row */}
        <div className="relative flex items-center border-b bg-white">
          <Button
            variant="ghost"
            size="sm"
            className="h-9 w-8 p-0 flex-shrink-0 rounded-none border-r hover:bg-gray-100 z-10"
            onClick={scrollLeft}
            aria-label="Scroll tabs left"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <div
            ref={tabsRef}
            className="flex-1 overflow-x-auto scrollbar-hide flex items-center h-9"
            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          >
            {currentProfileData?.allow_multiple && (
              <button
                className={`flex-shrink-0 h-full px-3 flex items-center gap-1.5 border-r text-xs font-medium transition-colors ${
                  pendingSessionId
                    ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-500'
                    : 'hover:bg-gray-100 text-gray-600'
                }`}
                onClick={() => {
                  setPendingSessionId('pending');
                  setCurrentSession(null);
                  setChatMessages([]);
                }}
                disabled={!currentProfile}
              >
                <Plus className="h-3.5 w-3.5" />
                New
              </button>
            )}

            {sessions.map((session) => {
              const isActive = !pendingSessionId && currentSession === session.session_id;
              return (
                <button
                  key={session.session_id}
                  className={`flex-shrink-0 h-full px-3 border-r cursor-pointer transition-colors ${
                    isActive
                      ? 'bg-white border-b-2 border-blue-500'
                      : 'hover:bg-gray-100'
                  }`}
                  onClick={() => {
                    setPendingSessionId(null);
                    setCurrentSession(session.session_id);
                  }}
                  title={`Session from ${formatDate(session.last_updated)}\nLast message: ${session.last_message}`}
                >
                  <div className="flex items-center gap-1.5 max-w-xs">
                    <MessageSquare className={`h-3 w-3 flex-shrink-0 ${isActive ? 'text-blue-600' : 'text-gray-400'}`} />
                    <div className="flex flex-col items-start">
                      <span className={`text-xs font-medium truncate ${isActive ? 'text-blue-700' : 'text-gray-700'}`}>
                        {session.is_default ? "Default" : formatDate(session.last_updated)}
                      </span>
                      {session.last_message && (
                         <span className="text-[10px] text-gray-500 truncate mt-[-2px]">
                           {truncateText(session.last_message, 25)}
                         </span>
                       )}
                    </div>
                  </div>
                </button>
              );
            })}
             {sessions.length === 0 && !currentProfileData?.allow_multiple && !pendingSessionId && currentProfile && (
                 <div className="h-full px-3 flex items-center text-xs text-gray-400 italic">
                     No sessions. Send a message to start.
                 </div>
             )}
              {sessions.length === 0 && !currentProfile && (
                 <div className="h-full px-3 flex items-center text-xs text-gray-400 italic">
                     Select a profile to view sessions.
                 </div>
             )}
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="h-9 w-8 p-0 flex-shrink-0 rounded-none border-l hover:bg-gray-100 z-10"
            onClick={scrollRight}
             aria-label="Scroll tabs right"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Main Content Area (Chat) */}
      <div className="flex-1 min-h-0 overflow-hidden bg-gray-50">
        {pendingSessionId ? (
          <div className="h-full flex flex-col items-center justify-center space-y-3 text-gray-500 px-4">
            <MessageSquare className="w-10 h-10 text-gray-400 mb-1" strokeWidth={1.5} />
            <h3 className="text-md font-medium text-gray-700">New Session</h3>
            <p className="text-sm text-gray-500 text-center">Type your first message below to start this conversation.</p>
          </div>
        ) : currentSession ? (
          <StreamingChatContainer
            moduleId={selectedModule?.module_id || null}
            profile={currentProfile}
            sessionId={currentSession}
            onMessagesUpdate={handleMessagesUpdate}
          />
        ) : (
            <div className="h-full flex flex-col items-center justify-center space-y-3 text-gray-500 px-4">
                 <MessageSquare className="w-10 h-10 text-gray-400 mb-1" strokeWidth={1.5} />
                 <h3 className="text-md font-medium text-gray-700">
                    {currentProfile ? "No Session Selected" : "Select Profile and Session"}
                 </h3>
                 <p className="text-sm text-gray-500 text-center">
                    {currentProfile ? "Select a session tab above or start a new one." : "Choose a profile to see available sessions."}
                 </p>
           </div>
        )}
      </div>

      {/* Input Area - Redesigned */}
      <div className="p-4 bg-gray-50 border-0  shrink-0">
         {error && ( // Display general errors
           <Alert variant="destructive" className="mb-3">
             <AlertCircle className="h-4 w-4" />
             <AlertDescription className="text-xs">
               {error}
             </AlertDescription>
           </Alert>
         )}
        {/* Container with relative positioning */}
        <div className="relative w-full  mx-auto">
          <Textarea
            ref={textareaRef}
            value={storeInputValue}
            onChange={(e) => setStoreInputValue(e.target.value)}
            onKeyDown={(e: React.KeyboardEvent) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (canSend) {
                  handleSend(storeInputValue);
                }
              }
            }}
            placeholder={
                !currentProfile ? "Select a profile to begin..." :
                (!currentSession && !pendingSessionId && !currentProfileData?.allow_multiple) ? "Send a message to start the default session..." :
                (!currentSession && !pendingSessionId && currentProfileData?.allow_multiple) ? "Select or start a new session..." :
                 "Send a message..." // Simplified placeholder
            }
            disabled={isLoading || !currentProfile || (!currentSession && !pendingSessionId)}
            className="
              w-full resize-none min-h-[52px] max-h-[200px] text-sm shadow-sm
              border border-gray-300 rounded-lg  /* Outer appearance */
              bg-white /* Use white or gray-50 */
              focus-visible:ring-1 focus-visible:ring-blue-500 focus-visible:border-blue-500 /* Focus style */
              pl-3 pr-14 py-3 /* Padding: left, RIGHT (for button), top/bottom */
              overflow-y-auto /* Ensure scrolling works within textarea */
            "
            rows={1}
            style={{
                // Height is managed by adjustTextareaHeight, but overflow needs to be auto/scroll
            }}
          />
          <Button
            onClick={() => handleSend(storeInputValue)}
            disabled={!canSend || isLoading} // Use combined canSend flag
            size="icon"
            className={`
              absolute bottom-2 right-2 h-8 w-8 rounded-full z-10
              ${canSend ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}
              transition-colors
            `} // Positioned bottom-right, circular, Z-index
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              // Use ArrowUp or Send icon
              <ArrowUp className="h-4 w-4" />
              // <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default BottomPanel;