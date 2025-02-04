import { useRef, useEffect } from 'react';
import { Terminal, ChevronRight, CheckCircle, XCircle } from 'lucide-react';
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Send } from 'lucide-react';

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
const ToolCall = ({ toolCall }: { toolCall: ToolCall }) => {
  const args = typeof toolCall.arguments === 'string' ? JSON.parse(toolCall.arguments) : toolCall.arguments;
  
  return (
    <Card className="mt-2">
      <CardContent className="p-3">
        <div className="flex items-center gap-2 text-blue-600">
          <Terminal className="w-4 h-4" />
          <span className="font-medium">{toolCall.name}</span>
        </div>
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-sm text-blue-600 mt-2">
            <ChevronRight className="w-4 h-4" />
            Arguments
          </CollapsibleTrigger>
          <CollapsibleContent>
            <pre className="mt-2 p-2 bg-slate-50 rounded text-sm font-mono overflow-x-auto max-w-full">
              <code className="break-all whitespace-pre-wrap">
                {JSON.stringify(args, null, 2)}</code>
            </pre>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
};

// Updated ToolResult component using shadcn components
const ToolResult = ({ result }: { result: ToolResult }) => {
  const isSuccess = result.result?.status === 'success';
  const hasStatus = typeof result.result?.status === 'string';
  
  return (
    <Card className={`mt-2 ${
      hasStatus 
        ? isSuccess 
          ? 'bg-green-50/50' 
          : 'bg-red-50/50'
        : 'bg-blue-50/50'
    }`}>
      <CardContent className="p-3">
        <div className="flex items-center gap-2">
          {hasStatus ? (
            isSuccess ? (
              <CheckCircle className="w-4 h-4 text-green-600" />
            ) : (
              <XCircle className="w-4 h-4 text-red-600" />
            )
          ) : (
            <Terminal className="w-4 h-4 text-blue-600" />
          )}
          <Badge variant={hasStatus ? (isSuccess ? "default" : "destructive") : "secondary"}>
            {result.step}
          </Badge>
        </div>

        {result.result?.message && (
          <p className="text-sm mt-2 text-gray-600">
            {result.result.message}
          </p>
        )}
        
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-sm mt-2">
            <ChevronRight className="w-4 h-4" />
            Details
          </CollapsibleTrigger>
          <CollapsibleContent>
            <pre className="mt-2 p-2 bg-slate-50 rounded text-sm font-mono overflow-x-auto max-w-full">
              <code className="break-all whitespace-pre-wrap">
                {JSON.stringify(result.result, null, 2)}</code>
            </pre>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
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
const ChatContainer = ({ messages }: { messages: Message[] }) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const messageGroups = groupMessages(messages);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  return (
    <ScrollArea className="flex-1 px-4 py-4 overflow-x-hidden">
      <div className="max-w-full">
        {messageGroups.map((group, groupIndex) => (
        <div key={groupIndex} className="mb-6 last:mb-2">
          {group.map((message, messageIndex) => {
            if (message.role === 'user' && 
                group.some(m => m.role === 'system' && m.tool_results)) {
              return null;
            }

            return (
              <Card
                key={messageIndex}
                className={`mb-4 ${
                  message.role === 'assistant' ? 'bg-gray-50' : 'bg-white'
                }`}
              >
                <CardContent className="p-4">
                  {message.role !== 'system' && (
                    <Badge variant="outline" className="mb-2">
                      {message.role === 'assistant' ? 'Assistant' : 'You'}
                    </Badge>
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
                </CardContent>
              </Card>
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
export { ToolCall as ToolCallComponent, ToolResult as ToolResultComponent, ChatContainer };

function isinstance(x: any, str: any) {
  throw new Error('Function not implemented.');
}
