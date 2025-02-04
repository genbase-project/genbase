import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Bot } from 'lucide-react';
import { ChatContainer } from '../components/Chat';
import type { Message } from '../components/Chat';
import type { Module } from '../components/TreeView';
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const sections = ['initialize', 'maintain',  'edit',  'remove',] as const;
type Section = typeof sections[number];

interface HistoryResponse {
  history: Message[];
  section: string;
  module_id: string;
}

interface BottomPanelProps {
  selectedModule: Module | null;
}

const BottomPanel = ({ selectedModule }: BottomPanelProps) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [currentSection, setCurrentSection] = useState<Section>('maintain');
  const [isLoading, setIsLoading] = useState(false);

  const fetchHistory = async () => {
    if (!selectedModule?.module_id) return;

    try {
      const response = await fetch(
        `http://localhost:8000/chat/${selectedModule.module_id}/workflow/${currentSection}/history`
      );
      const data: HistoryResponse = await response.json();
      setMessages(data.history || []);
    } catch (error) {
      console.error('Error fetching history:', error);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [currentSection, selectedModule?.module_id]);

  const handleSend = async () => {
    if (!inputValue.trim() || !selectedModule?.module_id) return;

    setIsLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/chat/${selectedModule.module_id}/execute`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            section: currentSection,
            input: inputValue
          })
        }
      );
      
      if (response.ok) {
        setInputValue('');
        await fetchHistory();
      }
    } catch (error) {
      console.error('Error sending message:', error);
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
    <div className="h-full flex overflow-hidden">
      <div className="flex-1 flex flex-col border-t min-w-0">
        <ChatContainer messages={messages} />
        
        <div className="p-4 border-t shrink-0">
          <div className="max-w-3xl mx-auto flex gap-2">
            <Input
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={(e: React.KeyboardEvent) => e.key === 'Enter' && !isLoading && handleSend()}
              placeholder="Send a message..."
              disabled={isLoading}
              className="flex-1"
            />
            <Button 
              onClick={handleSend}
              disabled={isLoading}
              variant="secondary"
            >
              {isLoading ? (
                <div className="w-4 h-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </div>

      <div className="w-48 border-l">
        <Tabs 
          defaultValue="maintain" 
          className="w-full"
          onValueChange={(value) => setCurrentSection(value as Section)}
        >
          <div className="p-4">
            <p className="text-xs font-medium text-gray-600 mb-2">WORKFLOWS</p>
            <TabsList className="flex flex-col h-auto bg-transparent gap-1">
              {['initialize', 'maintain', 'edit', 'remove'].map((section) => (
                <TabsTrigger
                  key={section}
                  value={section}
                  className="w-full justify-start data-[state=active]:bg-gray-100"
                >
                  {section}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
        </Tabs>
      </div>
    </div>
  );


};

export default BottomPanel;
