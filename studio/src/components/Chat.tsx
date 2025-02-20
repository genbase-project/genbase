import { useRef, useEffect } from 'react';
import { Terminal, ChevronRight, CheckCircle, XCircle, CurlyBraces } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";
import Markdown from 'markdown-to-jsx';
import ReactJson from 'react-json-view';
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { useChatPromptStore } from '../stores/chatPromptStore';
import { parseGiml } from './giml';
import React from 'react';

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
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string | null;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  name?: string;
  tool_call_id?: string;
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

// Message Header Component
const MessageHeader = ({ role, name }: { role: string; name?: string }) => {
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

// Custom code rendering functions
const renderCode = (content: string, language?: string) => {
  return (
    <div className="relative my-2">
      {language && (
        <div className="absolute right-2 top-2 text-xs text-gray-500">
          {language.replace('language-', '')}
        </div>
      )}
      <pre className="bg-gray-50 p-4 rounded-md overflow-x-auto">
        <code className={language ? `language-${language}` : ''}>
          {content}
        </code>
      </pre>
    </div>
  );
};

const processMarkdownContent = (content: string) => {
  return content
    .replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<codeblock language="${lang || ''}">${code}</codeblock>`;
    })
    .replace(/```\n([\s\S]*?)```/g, (match, code) => {
      return `<codeblock>${code}</codeblock>`;
    });
};

// Main ChatContainer Component
const ChatContainer = ({ messages }: ChatContainerProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { setActivePromptIndex } = useChatPromptStore();

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

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const renderCode = (content: React.ReactNode): string => {
    if (typeof content === 'string') {
      return content;
    }
    if (Array.isArray(content)) {
      return content.map(item => renderCode(item)).join('');
    }
    if (content === null || content === undefined) {
      return '';
    }
    if (React.isValidElement(content)) {
      const props = content.props as { children?: React.ReactNode };
      return renderCode(props.children || '');
    }
    return JSON.stringify(content, null, 2);
  };
  
  const processMarkdownContent = (content: string): string => {
    // First, escape any existing HTML-like tags that aren't our special tags
    const escapedContent = content.replace(
      /(<(?!\/?(?:giml|codeblock|code|original|updated|select|label|responses))[^>]+>)/g,
      '&lt;$1'
    );
  
    // Then process code blocks
    return escapedContent
      // Handle code blocks with language
      .replace(
        /```(\w+)?\n([\s\S]*?)```/g,
        (_, lang, code) => `<codeblock language="${lang || ''}">${code.trim()}</codeblock>`
      )
      // Handle code blocks without language
      .replace(
        /```\n?([\s\S]*?)```/g,
        (_, code) => `<codeblock>${code.trim()}</codeblock>`
      );
  };
  
  const safeStringifyReactElement = (element: React.ReactElement): string => {
    const { type, props } = element;
    
    // Extract the tag name if it's a string type
    const tagName = typeof type === 'string' ? type : 'component';
    
    // Start building the string representation
    let result = `<${tagName}`;
    
    // Add props (excluding children)
    Object.entries(props).forEach(([key, value]) => {
      if (key !== 'children') {
        result += ` ${key}="${value}"`;
      }
    });
    
    result += '>';
    
    // Handle children
    if (props.children) {
      if (typeof props.children === 'string') {
        result += props.children;
      } else if (Array.isArray(props.children)) {
        result += props.children
          .map((child: any) => {
            if (typeof child === 'string') return child;
            if (React.isValidElement(child)) {
              return safeStringifyReactElement(child);
            }
            return '';
          })
          .join('');
      } else if (React.isValidElement(props.children)) {
        result += safeStringifyReactElement(props.children);
      }
    }
    
    // Close the tag
    result += `</${tagName}>`;
    
    return result;
  };

  const markdownComponents = {
    giml: {
      component: ({ children }: any) => {
        const { activePromptIndex } = useChatPromptStore();
        const isLastMessage = activePromptIndex !== -1;
        
        // Debug log
        console.log('GIML children:', children);
        
        // Return a fragment containing all parsed elements
        const parsedElements = parseGiml(React.Children.toArray(children), isLastMessage);
        return <>{parsedElements}</>;
      }
    }
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
              {message.content && (
           <Markdown 
           options={{ 
             overrides: markdownComponents,
             forceBlock: true,
             forceWrapper: true,
           }}
         >
           {message.content}
         </Markdown>
         
              )}
              
              {message.tool_calls?.map((toolCall, idx) => (
                <ToolCall key={idx} toolCall={toolCall} />
              ))}
              
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