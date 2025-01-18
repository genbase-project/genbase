import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { RefreshCw, ThumbsUp, ThumbsDown, Copy, ChevronLeft, ChevronRight, Pencil } from 'lucide-react';
import Markdown from 'markdown-to-jsx';

// Custom code block component for syntax highlighting
const CodeBlock = ({ children, className }: any) => {
  const language = className ? className.replace('lang-', '') : '';
  
  return (
    <pre className="bg-background-secondary rounded-md p-4 overflow-x-auto">
      <code className={`language-${language} text-sm font-mono`}>
        {children}
      </code>
    </pre>
  );
};

// Custom paragraph component to handle spacing
const Paragraph = ({ children }: any) => (
  <p className="my-2">{children}</p>
);

// Custom inline code component
const InlineCode = ({ children }: any) => (
  <code className="bg-background-secondary px-1.5 py-0.5 rounded text-sm">{children}</code>
);

// Markdown options
const markdownOptions = {
  overrides: {
    code: CodeBlock,
    p: Paragraph,
    inlineCode: InlineCode,
    h1: { props: { className: 'text-2xl font-bold mt-4 mb-2' } },
    h2: { props: { className: 'text-xl font-bold mt-3 mb-2' } },
    h3: { props: { className: 'text-lg font-bold mt-3 mb-2' } },
    a: { props: { className: 'text-blue-400 hover:text-blue-300' } },
    ul: { props: { className: 'list-disc pl-6 my-2' } },
    ol: { props: { className: 'list-decimal pl-6 my-2' } },
    li: { props: { className: 'my-1' } },
    blockquote: { props: { className: 'border-l-4 border-gray-500 pl-4 my-2 italic' } },
    hr: { props: { className: 'my-4 border-gray-700' } },
  }
};

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  variations: {
    text: string;
    childMessages: Message[];  // Each variation can have its own chain of responses
  }[];
  currentVariation: number;
}

const BottomPanel = ({selectedModule}: any) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [editingMessageId, setEditingMessageId] = useState<string | null>(null);

  // Helper to generate assistant response
  const createAssistantResponse = (userMessage: string) => ({
    id: crypto.randomUUID(),
    role: 'assistant',
    content: `Response to: ${userMessage}`,
    variations: [{
      text: `Response to: ${userMessage}`,
      childMessages: []
    }],
    currentVariation: 0
  });

  const getVisibleMessages = () => {
    let result: Message[] = [];
    let currentChain = messages;
    
    while (currentChain.length > 0) {
      const msg = currentChain[0];
      result.push(msg);
      
      // Move to the child messages of the current variation
      currentChain = msg.variations[msg.currentVariation].childMessages;
    }
    
    return result;
  };

  const handleSend = (content: string, editingId: string | null = null) => {
    if (!content.trim()) return;

    const newUserMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      variations: [{
        text: content,
        childMessages: []
      }],
      currentVariation: 0
    };

    const newAssistantMessage = createAssistantResponse(content);

    if (editingId) {
      // Find the message and its parent chain
      setMessages(prev => {
        const updateMessageChain = (msgs: Message[]): any[] => {
          return msgs.map(msg => {
            if (msg.id === editingId) {
              // Add new variation to the edited message
              const newVariations = [...msg.variations, {
                text: content,
                childMessages: [newAssistantMessage]
              }];
              return {
                ...msg,
                variations: newVariations,
                currentVariation: newVariations.length - 1
              };
            }
            
            // Recursively update child messages
            const updatedVariations = msg.variations.map(v => ({
              ...v,
              childMessages: updateMessageChain(v.childMessages)
            }));
            return { ...msg, variations: updatedVariations };
          });
        };
        
        return updateMessageChain(prev);
      });
    } else {
      // Add to the current visible chain
      const visibleMsgs = getVisibleMessages();
      if (visibleMsgs.length === 0) {
        setMessages([newUserMessage]);
        // Add assistant response to the first variation
        newUserMessage.variations[0].childMessages = [newAssistantMessage as Message];
      } else {
        const lastMsg = visibleMsgs[visibleMsgs.length - 1];
        lastMsg.variations[lastMsg.currentVariation].childMessages = [
          newUserMessage
        ];
        newUserMessage.variations[0].childMessages = [newAssistantMessage as Message];
      }
    }

    setInputValue('');
    setEditingMessageId(null);
  };

  const navigateVariation = (messageId: string, direction: 'prev' | 'next') => {
    setMessages(prev => {
      const updateMessageChain = (msgs: Message[]): Message[] => {
        return msgs.map(msg => {
          if (msg.id === messageId) {
            const newIndex = direction === 'prev'
              ? Math.max(0, msg.currentVariation - 1)
              : Math.min(msg.variations.length - 1, msg.currentVariation + 1);
            
            return {
              ...msg,
              currentVariation: newIndex,
              content: msg.variations[newIndex].text
            };
          }
          
          const updatedVariations = msg.variations.map(v => ({
            ...v,
            childMessages: updateMessageChain(v.childMessages)
          }));
          return { ...msg, variations: updatedVariations };
        });
      };
      
      return updateMessageChain(prev);
    });
  };

  const regenerateResponse = (messageId: string) => {
    setMessages(prev => {
      const updateMessageChain = (msgs: Message[]): Message[] => {
        return msgs.map(msg => {
          if (msg.id === messageId && msg.role === 'assistant') {
            const newVariation = {
              text: `Regenerated response ${Date.now()}`,
              childMessages: []
            };
            const newVariations = [...msg.variations, newVariation];
            
            return {
              ...msg,
              content: newVariation.text,
              variations: newVariations,
              currentVariation: newVariations.length - 1
            };
          }
          
          const updatedVariations = msg.variations.map(v => ({
            ...v,
            childMessages: updateMessageChain(v.childMessages)
          }));
          return { ...msg, variations: updatedVariations };
        });
      };
      
      return updateMessageChain(prev);
    });
  };

  const visibleMessages = getVisibleMessages();

  return (
    <div className="h-full flex flex-col border-t text-black">
      <ScrollArea className="flex-1 px-4 py-4">
        {visibleMessages.map((message) => (
          <div
            key={message.id}
            className={`group mb-6 ${
              message.role === 'assistant' ? 'bg-slate-50' : ''
            } rounded-lg`}
          >
            <div className="p-4">
              <div className="text-sm">
                <Markdown options={markdownOptions}>
                  {message.variations[message.currentVariation].text}
                </Markdown>
              </div>
            </div>

            <div className="flex items-center gap-2 px-4 pb-2 opacity-0 group-hover:opacity-100 transition-opacity">
              {message.variations.length > 1 && (
                <div className="flex items-center gap-2 mr-4">
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => navigateVariation(message.id, 'prev')}
                    disabled={message.currentVariation === 0}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-xs ">
                    {message.currentVariation + 1} / {message.variations.length}
                  </span>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => navigateVariation(message.id, 'next')}
                    disabled={message.currentVariation === message.variations.length - 1}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              )}
              
              {message.role === 'assistant' ? (
                <>
                  <Button variant="ghost" size="sm">
                    <ThumbsUp className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm">
                    <ThumbsDown className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm">
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => regenerateResponse(message.id)}
                  >
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                </>
              ) : (
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => {
                    setEditingMessageId(message.id);
                    setInputValue(message.variations[message.currentVariation].text);
                  }}
                >
                  <Pencil className="w-4 h-4" />
                </Button>
              )}
            </div>
          </div>
        ))}
      </ScrollArea>
      
      <div className="p-4 border-t">
        <div className="max-w-3xl mx-auto flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend(inputValue, editingMessageId)}
            placeholder={editingMessageId ? "Edit your message..." : "Send a message..."}
            className="flex-1"
          />
          <Button 
            onClick={() => handleSend(inputValue, editingMessageId)}
            variant="secondary"
          >
            {editingMessageId ? 'Update' : 'Send'}
          </Button>
        </div>
      </div>
    </div>
  );
};

export default BottomPanel;
