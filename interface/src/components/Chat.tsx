import { useRef, useEffect } from 'react';
import { Terminal, ChevronRight, CheckCircle, XCircle } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";

// Interfaces remain the same
interface ToolCall {
  id: string;
  name: string;
  arguments: string;
}

interface ChatContainerProps {
  messages: Message[];
}

interface ToolResult {
  step: string;
  result: any;
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
}

interface ToolCallProps {
  toolCall: ToolCall;
}

interface ToolResultProps {
  result: ToolResult;
}

// Compact Tool Call component
const ToolCall: React.FC<ToolCallProps> = ({ toolCall }) => {
  const args = JSON.parse(toolCall.arguments);
  
  return (
    <div className="mt-1 rounded bg-blue-50/50 p-2 border border-blue-100">
      <div className="flex items-center gap-1 text-blue-600 text-sm">
        <Terminal className="w-3 h-3" />
        <span>{toolCall.name}</span>
      </div>
      <details className="mt-1">
        <summary className="flex items-center gap-1 text-xs text-blue-600 cursor-pointer">
          <ChevronRight className="w-3 h-3" />
          Args
        </summary>
        <pre className="mt-1 p-2 bg-white rounded text-xs font-mono overflow-x-auto">
          {JSON.stringify(args, null, 2)}
        </pre>
      </details>
    </div>
  );
};

// Compact Tool Result component
const ToolResult: React.FC<ToolResultProps> = ({ result }) => {
  const isSuccess = result.result?.status === 'success';
  const hasStatus = typeof result.result?.status === 'string';
  
  return (
    <div className={`mt-1 rounded ${
      hasStatus 
        ? isSuccess 
          ? 'bg-green-50/50 border-green-100' 
          : 'bg-red-50/50 border-red-100'
        : 'bg-blue-50/50 border-blue-100'
    } p-2 border`}>
      <div className="flex items-center gap-1 text-sm">
        {hasStatus ? (
          isSuccess ? (
            <CheckCircle className="w-3 h-3 text-green-600" />
          ) : (
            <XCircle className="w-3 h-3 text-red-600" />
          )
        ) : (
          <Terminal className="w-3 h-3 text-blue-600" />
        )}
        <span className={hasStatus 
          ? isSuccess 
            ? 'text-green-700' 
            : 'text-red-700'
          : 'text-blue-700'
        }>
          Result for: {result.step}
        </span>
      </div>

      <div className="mt-1 p-2 bg-white/50 rounded">
        {result.result?.message && (
          <div className="text-xs mb-1">
            {result.result.message}
          </div>
        )}
        
        <details>
          <summary className="flex items-center gap-1 text-xs cursor-pointer mb-1">
            <ChevronRight className="w-3 h-3" />
            Details
          </summary>
          <pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap overflow-x-auto">
            {JSON.stringify(result.result, null, 2)}
          </pre>
        </details>
      </div>
    </div>
  );
};

// Message grouping helper remains the same
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

// Compact Chat Container
const ChatContainer: React.FC<ChatContainerProps> = ({ messages }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messageGroups = groupMessages(messages);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <ScrollArea className="flex-1 px-2 py-2">
      {messageGroups.map((group, groupIndex) => (
        <div key={groupIndex} className="mb-3">
          {group.map((message, messageIndex) => {
            if (message.role === 'user' && 
                group.some(m => m.role === 'system' && m.tool_results)) {
              return null;
            }

            return (
              <div
                key={messageIndex}
                className={`mb-1 ${
                  message.role === 'assistant' ? 'bg-gray-50' : ''
                } rounded p-2`}
              >
                {message.role !== 'system' && (
                  <div className="flex items-center gap-1 mb-1">
                    <span className="text-xs text-gray-500">
                      {message.role === 'assistant' ? 'Assistant' : 'You'}
                    </span>
                  </div>
                )}
                
                <div className="text-sm">
                  {message.content !== 'Executing tool calls...' && message.content}
                  
                  {message.tool_calls?.map((toolCall, idx) => (
                    <ToolCall key={idx} toolCall={toolCall} />
                  ))}
                  
                  {message.tool_results?.map((result, idx) => (
                    <ToolResult key={idx} result={result} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ))}
      <div ref={scrollRef} />
    </ScrollArea>
  );
};

export type { Message, ToolCall, ToolResult };
export { ToolCall as ToolCallComponent, ToolResult as ToolResultComponent, ChatContainer };