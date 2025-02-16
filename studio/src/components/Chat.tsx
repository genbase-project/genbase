import { useRef, useEffect } from 'react';
import { Terminal, ChevronRight, CheckCircle, XCircle, CurlyBraces } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";
import Markdown from 'markdown-to-jsx';
import ReactJson from 'react-json-view';
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useChatPromptStore } from '../stores/chatPromptStore';
import { parseGiml } from './giml';

// Types
interface Function {
  name: string;
  arguments: string;
}

interface ToolCall {
  id: string;
  type?: string;
  function: Function;
}

interface ToolResult {
  action: string;
  result: any;
}

interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool';  // Added 'tool'
  content: string | null;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  name?: string;  // Added optional name property
  tool_call_id?: string;  // Might also be useful for tool messages
}


interface ChatContainerProps {
  messages: Message[];
  onSend?: (text: string) => void;
}

// Tool Call Component
const ToolCall = ({ toolCall }: { toolCall: ToolCall }) => {
  const args = (() => {
    try {
      return JSON.parse(toolCall.function.arguments);
    } catch (e) {
      console.error('Failed to parse tool call arguments:', e);
      return {};
    }
  })();
  



  return (
    <Card className="mt-1.5">
      <CardContent className="p-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-blue-600">
            <Terminal className="w-3 h-3" />
            <span className="text-xs font-medium">{toolCall.function.name}</span>
          </div>
          <div className="text-[10px] text-gray-500">ID: {toolCall.id}</div>
        </div>
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-blue-600/70 hover:text-blue-600 mt-1.5">
            <ChevronRight className="w-3 h-3" />
            Arguments
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-1 p-1.5 bg-slate-50 rounded-sm max-w-full">
              <ReactJson
                src={args}
                theme="bright:inverted"
                name={false}
                displayDataTypes={false}
                enableClipboard={false}
                style={{
                  fontSize: '0.75rem',
                  fontFamily: 'monospace',
                  backgroundColor: 'transparent',
                  color: '#374151'
                }}
                iconStyle="circle"
                displayObjectSize={false}
                quotesOnKeys={false}
                indentWidth={6}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
};

// Tool Result Component
const ToolResult = ({ result }: { result: ToolResult }) => {
  const resultData = (() => {
    if (typeof result.result === 'string') {
      try {
        return JSON.parse(result.result);
      } catch (e) {
        return { value: result.result };
      }
    }
    return result.result || {};
  })();
  
  const isSuccess = resultData?.status === 'success';
  const hasStatus = typeof resultData?.status === 'string';
  
  return (
    <Card className={`mt-1.5 ${
      hasStatus 
        ? isSuccess 
          ? 'bg-green-50/50' 
          : 'bg-red-50/50'
        : 'bg-blue-50/50'
    }`}>
      <CardContent className="p-2">
        <div className="flex items-center gap-1.5">
          {hasStatus ? (
            isSuccess ? (
              <CheckCircle className="w-3 h-3 text-green-600" />
            ) : (
              <XCircle className="w-3 h-3 text-red-600" />
            )
          ) : (
            <Terminal className="w-3 h-3 text-blue-600" />
          )}
          <span className="text-xs font-medium">
            {result.action}
          </span>
        </div>

        {result.result?.message && (
          <p className="text-xs mt-1.5 text-gray-600">
            {result.result.message}
          </p>
        )}
        
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-gray-500/70 hover:text-gray-500 mt-1.5">
            <CurlyBraces className="w-3 h-3" />
            Details
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-1 p-1.5 bg-slate-50 rounded-sm max-w-full">
              <ReactJson
                src={resultData}
                theme="bright:inverted"
                name={false}
                displayDataTypes={false}
                enableClipboard={false}
                style={{
                  fontSize: '0.75rem',
                  fontFamily: 'monospace',
                  backgroundColor: 'transparent',
                  color: '#374151'
                }}
                iconStyle="circle"
                displayObjectSize={false}
                quotesOnKeys={false}
                indentWidth={6}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
};

// Main ChatContainer Component
const ChatContainer = ({ messages }: ChatContainerProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { setActivePromptIndex } = useChatPromptStore();


  // Update active prompt index whenever messages change
  useEffect(() => {
    let lastIndex = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant' && messages[i].content?.includes('<giml>')) {
        lastIndex = i;
        break;
      }
    }
    setActivePromptIndex(lastIndex);
  }, [messages, setActivePromptIndex]);

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Markdown components configuration
  const markdownComponents = {
    pre: ({ children, ...props }: React.ComponentPropsWithoutRef<'pre'>) => (
      <pre className="p-2 rounded-md" {...props}>{children}</pre>
    ),
    code: ({ children, ...props }: React.ComponentPropsWithoutRef<'code'>) => (
      <code className="bg-slate-50 px-1 rounded" {...props}>{children}</code>
    )
  };



  const MessageHeader = ({ role, name }: { role: string, name?: string }) => {
    if (role === 'tool') {
      return (
        <div className="flex items-center gap-1.5 text-[11px] text-gray-500 mb-0.5 px-2">
          <Terminal className="w-3 h-3" />
          <span>Tool Response: {name}</span>
        </div>
      );
    }
  
    return (
      <div className="text-[11px] text-gray-500 mb-0.5 px-2">
        {role === 'assistant' ? 'Agent' : 'User'}
      </div>
    );
  };
  
  




  return (
    <ScrollArea className="flex-1 overflow-x-hidden">
      <div className="max-w-full">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`py-1.5 px-2 ${
              message.role === 'assistant' ? 'bg-white' : ''
            }`}
          >
            {message.role !== 'system' && (
              <MessageHeader role={message.role} name={message.name} />
            )}
            
            <div className="text-[12px] px-2 prose prose-sm max-w-none">
              {/* Tool calls */}
              {message.tool_calls?.map((toolCall, idx) => (
                <ToolCall key={idx} toolCall={toolCall} />
              ))}
              
              {/* Tool results */}
              {message.role === 'tool' ? (
                <Card className="mt-1.5 bg-gray-50/50">
                  <CardContent className="p-2">
                    <div className="flex items-start gap-2">
                      <Terminal className="w-3 h-3 mt-1 text-gray-600" />
                      <div className="flex-1">
                        {(() => {
                          try {
                            const content = JSON.parse(message.content || '');
                            return (
                              <ReactJson
                                src={content}
                                theme="bright:inverted"
                                name={false}
                                displayDataTypes={false}
                                enableClipboard={false}
                                style={{
                                  fontSize: '0.75rem',
                                  backgroundColor: 'transparent',
                                  color: '#374151'
                                }}
                                iconStyle="circle"
                                displayObjectSize={false}
                                quotesOnKeys={false}
                                indentWidth={6}
                              />
                            );
                          } catch {
                            return (
                              <div className="text-gray-600">
                                {message.content}
                              </div>
                            );
                          }
                        })()}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ) : (
                // Regular content
                message.content !== null &&  (
                  <Markdown
                    options={{
                      overrides: {
                        ...markdownComponents,
                        giml: {
                          component: ({ children }) => {
                            const { activePromptIndex } = useChatPromptStore();
                            const isLast = index === activePromptIndex;
                            return parseGiml(children,()=>{}, isLast);
                          }
                        }
                      }
                    }}
                  >
                    {message.content}
                  </Markdown>
                )
              )}
              
              {/* Tool results from system messages */}
              {message.tool_results?.map((result, idx) => (
                <ToolResult key={idx} result={result} />
              ))}
            </div>
          </div>
        ))}
        <div ref={scrollRef} />
      </div>
    </ScrollArea>
  );
  
};

export type { Message, ToolCall, ToolResult };
export { ChatContainer };