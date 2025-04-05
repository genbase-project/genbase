// components/ChatContainer.tsx
import React, { useRef, useEffect } from 'react';
import { Terminal, ChevronRight, CheckCircle, XCircle, CurlyBraces } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";
import { JsonView, allExpanded, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';
import { Card, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import Markdown from 'markdown-to-jsx';

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

interface ChatContainerProps {
  messages: Message[];
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
        if ((message.content.startsWith('{') && message.content.endsWith('}')) || (message.content.startsWith('[') && message.content.endsWith(']'))) {
           return JSON.parse(message.content);
        }
        return { result_text: message.content };
      } catch (e) {
        return { raw_result: message.content, parse_error: "Content is not valid JSON" };
      }
    }
    return message.content;
  })();

  const isError = typeof resultData === 'object' && resultData !== null && ('error' in resultData);

  return (
    <Card className={`mt-1.5 mb-1.5 shadow-sm ${isError ? 'bg-red-50/50 border-red-200' : 'bg-green-50/50 border-green-200'}`}>
      <CardContent className="p-2">
        <div className="flex items-center gap-1.5 mb-1">
           {isError ? ( <XCircle className="w-3.5 h-3.5 text-red-600" /> )
             : ( <CheckCircle className="w-3.5 h-3.5 text-green-600" /> )}
          <span className="text-xs font-semibold">
            Result from: {message.name || 'Unknown Tool'}
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


// --- Main ChatContainer Component ---
const ChatContainer = ({ messages }: ChatContainerProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
       scrollRef.current.scrollIntoView({ behavior: 'auto', block: 'end' });
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
          return (
            <div className="my-1.5 p-2 bg-yellow-50 border border-dashed border-yellow-300 rounded">
              <p className="text-xs text-yellow-700 mb-1 font-medium">Unsupported element format: "{format || 'none'}"</p>
              <pre className="text-xs bg-white p-1 rounded overflow-x-auto">
                {innerContent || '<empty element>'}
              </pre>
            </div>
          );
        }
      },
      allowedAttributes: ['format'],
    },
    // Add overrides for standard Markdown tags here if needed for styling
  };

  return (
    <ScrollArea className="flex-1 overflow-x-hidden bg-gray-50">
      <div className="p-4 space-y-4">
        {messages.map((message, index) => {
          if (message.role === 'system') return null;

          if (message.role === 'tool') {
            return <ToolResultDisplay key={`tool-result-${index}-${message.tool_call_id}`} message={message} />;
          }

          return (
            <div
              key={`message-${index}`}
              className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                 className={`max-w-[85%] md:max-w-[75%] px-3 py-2 rounded-lg shadow-sm ${
                    message.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white text-gray-800 border border-gray-200'
                  }`}
              >
                 {message.content && (
                    <div className="prose prose-sm max-w-none text-inherit prose-p:my-1 prose-headings:my-1.5 prose-pre:my-1.5">
                       <Markdown options={{ overrides: markdownOverrides, forceWrapper: true }}>
                          {message.content}
                       </Markdown>
                    </div>
                 )}

                 {message.role === 'assistant' && message.tool_calls?.map((toolCall) => (
                    <ToolCallDisplay key={toolCall.id} toolCall={toolCall} />
                 ))}
              </div>
            </div>
          );
        })}
        <div ref={scrollRef} style={{ height: '1px' }} /> {/* Scroll target */}
      </div>
    </ScrollArea>
  );
};

export type { Message, ToolCall };
export { ChatContainer };