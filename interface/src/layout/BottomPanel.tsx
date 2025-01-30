import { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send } from 'lucide-react';
import { ChatContainer } from '../components/Chat';
import type { Message } from '../components/Chat';
import type { Module } from '../components/TreeView';

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
        `http://localhost:8000/agent/${selectedModule.module_id}/sections/${currentSection}/history`
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
        `http://localhost:8000/agent/${selectedModule.module_id}/execute`,
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
      <div className="h-full flex items-center justify-center text-gray-500">
        Please select a module to view the chat
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col border-t">
        <ChatContainer messages={messages} />
        
        <div className="p-4 border-t">
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
                <div className="w-6 h-6 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Section selector */}
      <div className="w-48 border-l bg-gray-50 p-4">
        <div className="flex items-center gap-0 mb-2 text-xs font-medium text-gray-600">
          <span>WORKFLOWS</span>
        </div>
        <div className="space-y-2 font-regular">
          {sections.map((section) => (
            <Button
              key={section}
              variant={currentSection === section ? "secondary" : "ghost"}
              className="w-full justify-start"
              onClick={() => setCurrentSection(section)}
            >
              {section}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default BottomPanel;