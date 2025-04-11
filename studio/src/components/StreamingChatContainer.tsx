// components/StreamingChatContainer.tsx
import React, { useRef, useEffect, useState, useCallback } from 'react';
// Import the library's EventSource, NOT the native one
import { EventSource } from 'eventsource';
import { Terminal, ChevronRight, CheckCircle, XCircle, CurlyBraces, AlertCircle, MessageSquare } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Alert, AlertDescription } from "@/components/ui/alert";
import Markdown from 'markdown-to-jsx';
import { ENGINE_BASE_URL } from '@/config';

// Import renderers from the consolidated elements file
import { MermaidRenderer, SandboxedHtmlRenderer } from './elements'; // Adjust path if needed

// --- Types ---
interface Function {
  name: string;
  arguments: string;
}

interface ToolCall {
  id: string;
  type?: string;
  function: Function;
}

interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string | null;
  tool_calls?: ToolCall[];
  name?: string; // For role='tool', the function name
  tool_call_id?: string; // For role='tool'
}

interface StreamingChatContainerProps {
  moduleId: string | null;
  profile: string | null;
  sessionId: string | null;
  onMessagesUpdate?: (messages: Message[]) => void;
}

// Custom event type for server-sent events from the library
interface SSEMessageEvent extends Event {
    data: string;
}

interface SSEErrorEvent extends Event {
    message?: string;
    status?: number;
}


// --- Tool Call Display Component ---
const ToolCallDisplay = ({ toolCall }: { toolCall: ToolCall }) => {
  const args = (() => {
    try {
      if (typeof toolCall.function.arguments === 'string') {
        return JSON.parse(toolCall.function.arguments);
      }
      if (typeof toolCall.function.arguments === 'object' && toolCall.function.arguments !== null) {
        return toolCall.function.arguments;
      }
      return { error: "Invalid arguments format", raw: toolCall.function.arguments };
    } catch (e) {
      console.error('Failed to parse tool call arguments:', toolCall.function.arguments, e);
      return { error: "Failed to parse JSON arguments", raw: toolCall.function.arguments };
    }
  })();

  return (
    <Card className="mt-1.5 mb-1.5 shadow-sm border border-gray-200">
      <CardContent className="p-2">
        <div className="flex items-center gap-1.5 text-blue-600 mb-1">
          <Terminal className="w-3.5 h-3.5" />
          <span className="text-xs font-semibold">{toolCall.function.name}</span>
        </div>
        <Collapsible>
          <CollapsibleTrigger className="group flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mt-1 w-full text-left">
            <ChevronRight className="w-3 h-3 transition-transform duration-200 group-data-[state=open]:rotate-90" />
            Arguments
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-1 overflow-hidden">
            <div className="p-1.5 bg-gray-50/80 rounded-sm max-w-full text-[11px]">
              <JsonView data={args} shouldExpandNode={allExpanded} style={defaultStyles} />
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
};

// --- Tool Result Display Component ---
const ToolResultDisplay = ({ message }: { message: Message }) => {
  const resultData = (() => {
    if (!message.content) return { info: "No result content." };
    if (typeof message.content === 'string') {
      try {
        // Be more robust: check if it looks like JSON before parsing
        const trimmedContent = message.content.trim();
        if ((trimmedContent.startsWith('{') && trimmedContent.endsWith('}')) || (trimmedContent.startsWith('[') && trimmedContent.endsWith(']'))) {
           return JSON.parse(trimmedContent);
        }
        // If not JSON-like, return as text
        return { result_text: message.content };
      } catch (e) {
        // If parsing fails even after check, return raw with error
        return { raw_result: message.content, parse_error: "Content looked like JSON but failed to parse" };
      }
    }
    // If content is already an object (less likely from backend SSE string data, but possible)
    return message.content;
  })();

  // Check if the parsed/original data indicates an error
  const isError = typeof resultData === 'object' && resultData !== null && ('error' in resultData || 'parse_error' in resultData);

  return (
    <Card className={`mt-1.5 mb-1.5 shadow-sm ${isError ? 'bg-red-50/50 border-red-200' : 'bg-green-50/50 border-green-200'}`}>
      <CardContent className="p-2">
        <div className="flex items-center gap-1.5 mb-1">
           {isError ? ( <XCircle className="w-3.5 h-3.5 text-red-600" /> )
             : ( <CheckCircle className="w-3.5 h-3.5 text-green-600" /> )}
          <span className="text-xs font-semibold">
            Result from: {message.name || 'Unknown Tool'}
            {isError && <span className="text-red-600 ml-1">(Error)</span>}
          </span>
        </div>
        <Collapsible>
          <CollapsibleTrigger className="group flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mt-1 w-full text-left">
             <CurlyBraces className="w-3 h-3" />
            Details
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-1 overflow-hidden">
             <div className="p-1.5 bg-gray-50/80 rounded-sm max-w-full text-[11px]">
                <JsonView data={resultData} shouldExpandNode={allExpanded} style={defaultStyles} />
             </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
};


// --- Main StreamingChatContainer Component ---
const StreamingChatContainer = ({ moduleId, profile, sessionId, onMessagesUpdate }: StreamingChatContainerProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const stableOnMessagesUpdate = useCallback((newMessages: Message[]) => {
      if (onMessagesUpdate) {
          onMessagesUpdate(newMessages);
      }
  }, [onMessagesUpdate]);


  useEffect(() => {
    if (eventSourceRef.current) {
      console.log("SSE Cleanup: Closing previous connection.");
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setMessages([]);
    stableOnMessagesUpdate([]);
    setError(null);
    setConnectionStatus('disconnected');


    if (!moduleId || !profile || !sessionId) {
      setError("SSE Error: Missing module, profile, or session ID.");
      return;
    }

    const connect = () => {
        console.log(`SSE Connect: Attempting connection for module=${moduleId}, profile=${profile}, session=${sessionId}`);
        setConnectionStatus('connecting');
        setError(null);

        const token = localStorage.getItem('auth_token');
        if (!token) {
            setError("SSE Error: Authentication token not found.");
            setConnectionStatus('disconnected');
            return;
        }

        const url = new URL(`${ENGINE_BASE_URL}/chat/${moduleId}/profile/${profile}/stream`);
        url.searchParams.append('session_id', sessionId);

        try {
            const es = new EventSource(url.toString(), {
                fetch: (input, init) => {
                    return fetch(input, {
                        ...init,
                        headers: {
                            ...init?.headers,
                            'Authorization': `Bearer ${token}`,
                            'Accept': 'text/event-stream',
                        },
                        cache: 'no-store',
                    });
                },
            });

            eventSourceRef.current = es;

            es.onopen = () => {
                console.log('SSE Status: Connection opened successfully.');
                setConnectionStatus('connected');
                setError(null);
            };

            es.onerror = (event: Event) => {
                const errEvent = event as SSEErrorEvent;
                console.error('SSE Status: Connection error.', errEvent);
                let errorMessage = 'SSE connection error occurred.';
                if (errEvent.message) {
                     errorMessage = `SSE Error: ${errEvent.message}`;
                } else if (errEvent.status) {
                     errorMessage = `SSE HTTP Error Status: ${errEvent.status}`;
                     if (errEvent.status === 401) {
                         errorMessage = "SSE Unauthorized (401). Token might be invalid or expired.";
                     }
                } else if (!navigator.onLine) {
                     errorMessage = "Network connection lost.";
                }

                setError(errorMessage);
                setConnectionStatus('disconnected');
                // Close might be necessary if the library doesn't automatically stop on critical errors
                es.close();
                eventSourceRef.current = null;
            };

            es.addEventListener('initial', (event: Event) => {
                const msgEvent = event as SSEMessageEvent;
                // console.log("SSE Data: Received 'initial' event");
                try {
                    const data = JSON.parse(msgEvent.data);
                    if (data.history && Array.isArray(data.history)) {
                        setMessages(data.history);
                        stableOnMessagesUpdate(data.history);
                    } else {
                        console.warn("SSE Data: 'initial' event received, but history data is missing or invalid.", data);
                    }
                } catch (e) {
                    console.error('SSE Data: Error parsing initial history:', e, msgEvent.data);
                    setError("Failed to parse initial chat history.");
                }
            });

            es.addEventListener('message', (event: Event) => {
                 const msgEvent = event as SSEMessageEvent;
                // console.log("SSE Data: Received 'message' event");
                try {
                    const data = JSON.parse(msgEvent.data);
                    if (data.message) {
                        setMessages(prev => {
                            const newMessages = [...prev, data.message];
                            stableOnMessagesUpdate(newMessages);
                            return newMessages;
                        });
                    } else {
                        console.warn("SSE Data: 'message' event received, but message data is missing.", data);
                    }
                } catch (e) {
                    console.error('SSE Data: Error parsing message:', e, msgEvent.data);
                    // Avoid setting a general error for a single bad message if possible
                }
            });

             es.addEventListener('error', (event: Event) => { // Catches events named 'error' from server data
                const msgEvent = event as SSEMessageEvent;
                console.log("SSE Data: Received 'error' event (payload)");
                 if (msgEvent.data) {
                     try {
                         const data = JSON.parse(msgEvent.data);
                         setError(`Server Error: ${data.error}` || 'Received unknown server error');
                         // Consider if connection should close on server error
                         // es.close();
                         // setConnectionStatus('disconnected');
                     } catch (e) {
                         setError('Received non-JSON server error event data.');
                     }
                 } else {
                      setError('Received server error event with no data.');
                 }
             });

            es.addEventListener('heartbeat', (event: Event) => {
                const msgEvent = event as SSEMessageEvent;
                // console.log("SSE Status: Heartbeat received:", msgEvent.data);
                 if (connectionStatus !== 'connected') {
                     setConnectionStatus('connected');
                 }
                 if (error && error.startsWith("SSE connection error")) { // Clear connection errors on heartbeat
                    setError(null);
                 }
            });

        } catch (err) {
            console.error("SSE Setup: Failed to create EventSource instance:", err);
            setError(err instanceof Error ? err.message : "Failed to initialize SSE connection");
            setConnectionStatus('disconnected');
        }
    };

    connect();

    return () => {
      if (eventSourceRef.current) {
        console.log("SSE Cleanup: Closing connection.");
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [moduleId, profile, sessionId, stableOnMessagesUpdate]);


  useEffect(() => {
     if (scrollRef.current) {
       const scrollContainer = document.getElementById('chat-scroll-container');
       if (scrollContainer) {
          const isNearBottom = scrollContainer.scrollHeight - scrollContainer.scrollTop - scrollContainer.clientHeight < 150;
          if (isNearBottom) {
             scrollContainer.scrollTo({ top: scrollContainer.scrollHeight, behavior: 'smooth' });
          }
       } else {
          scrollRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
       }
     }
   }, [messages]);


  const markdownOverrides = {
    element: {
      component: ({ node, ...props }: { node: any, children: React.ReactNode, format?: string, [key: string]: any }) => {
        const format = props.format?.toLowerCase();

        const getTextContent = (children: React.ReactNode): string => {
          return React.Children.toArray(children).map((child) => {
            if (typeof child === 'string') return child;
            if (React.isValidElement(child) && child.props.children) {
              return getTextContent(child.props.children);
            }
            return '';
          }).join('');
        };

        const innerContent = getTextContent(props.children);

        if (format === 'html') {
          return <SandboxedHtmlRenderer htmlContent={innerContent} />;
        } else if (format === 'mermaid') {
          return <MermaidRenderer chart={innerContent} />;
        } else {
          // Only render warning if format attribute exists but is unsupported
          if (props.format !== undefined) {
             return (
                <div className="my-1.5 p-2 bg-yellow-50 border border-dashed border-yellow-300 rounded">
                <p className="text-xs text-yellow-700 mb-1 font-medium">Unsupported element format: "{format || 'none'}"</p>
                <pre className="text-xs bg-white p-1 rounded overflow-x-auto">
                    {innerContent || '<empty element>'}
                </pre>
                </div>
            );
          }
          // If no format, render the children directly (default behavior)
          return <>{props.children}</>;
        }
      },
      // Allow format attribute on the custom 'element' tag
      allowedAttributes: ['format'],
    },
     // Add styling overrides for standard markdown elements if needed
     p: { props: { className: 'text-sm' } },
     li: { props: { className: 'text-sm' } },
     pre: { props: { className: 'text-xs' } },
     code: { props: { className: 'text-xs' } },
  };

  const isConnecting = connectionStatus === 'connecting';
  const isDisconnected = connectionStatus === 'disconnected';

  return (
    // **** ADDED h-full HERE ****
    <ScrollArea className="h-full overflow-x-hidden bg-gray-50" id="chat-scroll-container">
      {error && (
        <Alert variant="destructive" className="m-4 sticky top-0 z-10">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-xs">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {isConnecting && (
        <div className="flex justify-center items-center py-2 px-4 text-sm text-blue-600 sticky top-0 z-10 bg-blue-50 border-b border-blue-100">
            <span className="w-3 h-3 rounded-full bg-blue-500 animate-pulse inline-block mr-2"></span>
            Loading
        </div>
      )}
      {isDisconnected && !isConnecting && !error && messages.length > 0 && (
         <div className="flex justify-center items-center py-2 px-4 text-sm text-yellow-700 sticky top-0 z-10 bg-yellow-50 border-b border-yellow-100">
            <AlertCircle className="h-4 w-4 mr-2" />
             Connection closed. Attempting to reconnect...
         </div>
      )}


      <div className="p-4 space-y-4">
        {messages.length === 0 && !error && !isConnecting && (
          <div className="flex flex-col items-center justify-center pt-10 text-gray-500">
            <MessageSquare className="w-12 h-12 mb-3 text-gray-400" strokeWidth={1}/>
            {moduleId && profile && sessionId ?
              "No messages in this session yet." :
              "Select module, profile, and session to start."}
          </div>
        )}

        {messages.map((message, index) => {
          if (message.role === 'system') return null;

          if (message.role === 'tool') {
            // Ensure unique key using tool_call_id if available
            return <ToolResultDisplay key={`tool-result-${message.tool_call_id || index}`} message={message} />;
          }

          // Render user or assistant message
          return (
            <div
              key={`message-${index}`} // Consider using a more stable ID if available from backend
              className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                 className={`max-w-[85%] md:max-w-[75%] px-3 py-1.5 rounded-lg shadow-sm ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-800 border border-gray-200'
                  }`}
              >
                 {/* Render message content using Markdown */}
                 {message.content && (
                    <div className="prose prose-sm max-w-none text-inherit prose-p:my-1 prose-headings:my-1.5 prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5 prose-pre:my-1.5 prose-blockquote:my-1.5">
                       <Markdown options={{ overrides: markdownOverrides, forceWrapper: true }}>
                          {message.content}
                       </Markdown>
                    </div>
                 )}

                 {/* Render tool calls for assistant messages */}
                 {message.role === 'assistant' && message.tool_calls?.map((toolCall) => (
                    <ToolCallDisplay key={toolCall.id} toolCall={toolCall} />
                 ))}
              </div>
            </div>
          );
        })}
        {/* Invisible element to target for scrolling */}
        <div ref={scrollRef} style={{ height: '1px' }} />
      </div>
    </ScrollArea>
  );
};

export type { Message, ToolCall };
export { StreamingChatContainer };