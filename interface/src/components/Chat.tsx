import { useRef, useEffect } from 'react';
import { Terminal, ChevronRight, CheckCircle, XCircle, CurlyBraces, MessageCircle } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";
import Markdown from 'markdown-to-jsx';
import ReactJson from 'react-json-view';
import { Button } from "@/components/ui/button";
import CodeDiffViewer from './CodeDiffViewer';
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import React from 'react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { useChatPromptStore } from '../stores/chatPromptStore';

// Custom components for XML parts
const Question: React.FC<React.PropsWithChildren<{}>> = ({ children }) => {
  return <p className="text-[12px] font-medium text-gray-700">{children}</p>;
};

const Options: React.FC<React.PropsWithChildren<{}>> = ({ children }) => {
  return <div className="mt-2 flex flex-wrap gap-1.5">{children}</div>;
};

interface OptionProps {
  description?: string;
  onClick?: () => void;
  children: React.ReactNode;
  disabled?: boolean;
}

const Option: React.FC<OptionProps> = ({ 
  children, 
  description,
  onClick,
  disabled = false
}) => {
  const button = (
    <Button
      variant="outline"
      className={"px-3 h-7 min-w-[60px] text-[11px] " + (disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer")}
      onClick={onClick}
      disabled={disabled}
    >
      <div className="font-medium">{children}</div>
    </Button>
  );

  if (description) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            {button}
          </TooltipTrigger>
          <TooltipContent>
            <p className="text-sm">{description}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return button;
};

interface UserPromptComponentProps {
  children: React.ReactNode;
  onSelect?: (text: string) => void;
  onTextInput?: (text: string) => void;
  isLastMessage?: boolean;
}

const UserPromptComponent: React.FC<UserPromptComponentProps> = ({
  children,
  onSelect,
  isLastMessage = false
}) => {

  return (
    <Card className={"my-1.5" + (isLastMessage ? " bg-gray-50" : "")} data-active={isLastMessage}>
      <CardContent className="p-2">
        <div className="flex items-start gap-2">
          <MessageCircle className="w-4 h-4 mt-1 text-blue-500" />
          <div className="flex-1">
            {React.Children.map(children, child => {
              if (React.isValidElement<OptionProps>(child) && child.type === Option) {
              
                return React.cloneElement(child, {
                  onClick: () => onSelect?.(child.props.children as string),
                  disabled: !isLastMessage
                });
              }
              return child;
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

interface ToolCall {
  id: string;
  name: string;
  arguments: string;
}

interface ChatContainerProps {
  messages: Message[];
  onSend?: (text: string) => void;
  onTextInput?: (text: string) => void;
}

interface ToolResult {
  action: string;
  result: any;
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
}

// Keep existing ToolCall component
const ToolCall = ({ toolCall }: { toolCall: ToolCall }) => {
  const args = (() => {
    try {
      if (typeof toolCall.arguments === 'string') {
        return JSON.parse(toolCall.arguments);
      }
      return toolCall.arguments || {};
    } catch (e) {
      console.error('Failed to parse tool call arguments:', e);
      return {};
    }
  })();
  
  return (
    <Card className="mt-1.5">
      <CardContent className="p-2">
        <div className="flex items-center gap-1.5 text-blue-600">
          <Terminal className="w-3 h-3" />
          <span className="text-xs font-medium">{toolCall.name}</span>
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

// Keep existing ToolResult component
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

const groupMessages = (messages: Message[]): Message[][] => {
  const groups: Message[][] = [];
  let currentGroup: Message[] = [];

  messages.forEach((message, index) => {
    if (message.role === 'system' && message.tool_results) {
      if (currentGroup.length > 0) {
        groups.push(currentGroup);
        currentGroup = [];
      }
      groups.push([message]);
    } else if (message.tool_calls || (index > 0 && messages[index - 1].tool_calls)) {
      currentGroup.push(message);
    } else {
      if (currentGroup.length > 0) {
        groups.push(currentGroup);
        currentGroup = [];
      }
      currentGroup = [message];
    }
  });

  if (currentGroup.length > 0) {
    groups.push(currentGroup);
  }

  return groups;
};

const hasEditXml = (content: string) => {
  return content.includes('<edit_file') && content.includes('<original>') && content.includes('<updated>');
};

const ChatContainer = ({ messages, onSend }: ChatContainerProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messageGroups = groupMessages(messages);
  const { setActivePromptIndex } = useChatPromptStore();

  // Update active prompt index whenever messages change
  useEffect(() => {
    let lastIndex = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'assistant' && messages[i].content.includes('<user_prompt')) {
        lastIndex = i;
        break;
      }
    }
    setActivePromptIndex(lastIndex);
  }, [messages, setActivePromptIndex]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const markdownComponents = {
    pre: ({ children, ...props }: React.ComponentPropsWithoutRef<'pre'>) => (
      <pre className="p-2 rounded-md" {...props}>{children}</pre>
    ),
    code: ({ children, ...props }: React.ComponentPropsWithoutRef<'code'>) => (
      <code className="bg-slate-50 px-1 rounded" {...props}>{children}</code>
    ),
    user_prompt: {
      component: ({ children }: { children: React.ReactNode }) => {
        const { activePromptIndex } = useChatPromptStore();
        const isLast = activePromptIndex === -1;
        
        return (
          <UserPromptComponent
            onSelect={onSend}
            isLastMessage={isLast}
          >
            {children}
          </UserPromptComponent>
        );
      }
    },
    question: {
      component: Question
    },
    options: {
      component: Options
    },
    option: {
      component: Option
    }
  };

  return (
    <ScrollArea className="flex-1 overflow-x-hidden">
      <div className="max-w-full divide-y">
        {messageGroups.map((group, groupIndex) => (
          <div key={groupIndex} className="py-1.5 first:pt-1 last:pb-1 px-2">
            {group.map((message, messageIndex) => {
              if (message.role === 'user' && 
                  group.some(m => m.role === 'system' && m.tool_results)) {
                return null;
              }
            

              return (
                <div
                  key={messageIndex}
                  className={`${messageIndex > 0 ? 'mt-2' : ''} ${
                    message.role === 'assistant' ? 'bg-white' : ''
                  } py-1`}
                >
                  {message.role !== 'system' && (
                    <div className="text-[11px] text-gray-500 mb-0.5 px-2">
                      {message.role === 'assistant' ? 'Agent' : 'User'}
                    </div>
                  )}
                  
                  <div className="text-[12px] px-2 prose prose-sm max-w-none prose-pre:bg-transparent prose-pre:text-gray-700 prose-code:text-gray-700">
                    {message.content !== 'Executing tool calls...' && (
                      hasEditXml(message.content) ? (
                        <div className="rounded-lg">
                          <CodeDiffViewer content={message.content} />
                        </div>
                      ) : (
                        <Markdown
                          options={{
                            overrides: markdownComponents
                          }}
                        >
                          {message.content}
                        </Markdown>
                      )
                    )}
                    
                    {message.tool_calls?.map((toolCall, idx) => (
                      <ToolCall key={idx} toolCall={toolCall} />
                    ))}
                    
                    {message.tool_results?.map((result, idx) => (
                      <div key={idx}>
                        <ToolResult result={result} />
                        {result.result?.message && (
                          <div className="mt-2">
                            <Markdown
                              options={{
                                overrides: markdownComponents
                              }}
                            >
                              {result.result.message}
                            </Markdown>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
        <div ref={scrollRef} />
      </div>
    </ScrollArea>
  );
};

export type { Message, ToolCall, ToolResult };
export { ChatContainer };
