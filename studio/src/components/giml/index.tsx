import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileCode, MessageCircle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import React, { ReactElement } from 'react';
import { useChatStore } from "@/stores/chatStore";

// Define types for GIML elements

// First, add these interfaces after the existing ones
interface GimlElement extends ReactElement {
  type: string;
  props: {
    id?: string;
    file?: string;
    description?: string;
    value?: string;  // Added value property
    children?: React.ReactNode;
  };
}


interface CodeDiffProps {
  children: GimlElement[];
  file: string;
}

const CodeDiff = ({ children, file }: CodeDiffProps) => {
  const original = children.find(child => 
    child.type === 'original'
  )?.props?.children?.toString() || '';

  const updated = children.find(child => 
    child.type === 'updated'
  )?.props?.children?.toString() || '';

  return (
    <Card className="my-1.5">
      <CardContent className="p-2">
        <div className="flex items-start gap-2">
          <FileCode className="w-4 h-4 mt-1 text-blue-500" />
          <div className="flex-1">
            <p className="text-[12px] font-medium text-gray-700">{file}</p>
            <div className="mt-2 space-y-3 flex-1">
              <div>
                <p className="text-[11px] font-medium text-red-600 mb-1">Original:</p>
                <pre className="bg-gray-50 p-2 rounded text-[11px] text-gray-950 overflow-x-auto">
                  <div>{original}</div>
                </pre>
              </div>
              <div>
                <p className="text-[11px] font-medium text-green-600 mb-1">Updated:</p>
                <pre className="bg-gray-50 p-2 rounded text-[11px] text-gray-950 overflow-x-auto">
                  {updated}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

interface SelectProps {
  children: GimlElement[];
  isLastMessage?: boolean;
  onSelect?: (id: string, value: string) => void;
}

interface SelectItem {
  description?: string;
  text: string;
}

const Select = ({ children, isLastMessage = false, onSelect }: SelectProps) => {
  const sendResponse = useChatStore(state => state.sendResponse);


  const labelElement = children.find(child => 
    child.type === 'label'
  ) as GimlElement;

  const selectElement = children.find(child => 
    child.type === 'select'
  ) as GimlElement;

  if (!labelElement || !selectElement) return null;

  const labelText = labelElement.props.children?.toString() || '';
  const selectId = selectElement.props.id || '';
  const items = (selectElement.props.children as GimlElement[]).map((item): SelectItem => ({
    description: item.props.description,
    text: item.props.children?.toString() || ''
  }));

  return (
    <Card className={"my-1.5" + (isLastMessage ? " bg-gray-50" : "")} data-active={isLastMessage}>
      <CardContent className="p-2">
        <div className="flex items-start gap-2">
          <MessageCircle className="w-4 h-4 mt-1 text-blue-500" />
          <div className="flex-1">
            <p className="text-[12px] font-medium text-gray-700">{labelText}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {items.map((item, index) => {
                const button = (
                  <Button
                  key={index}
                  variant="outline"
                  className={"px-3 h-7 min-w-[60px] text-[11px] " + 
                    (!isLastMessage ? "opacity-50 cursor-not-allowed" : "cursor-pointer")}
                  onClick={() => isLastMessage && sendResponse(selectId, item.text)}
                  disabled={!isLastMessage}
                >
                  <div className="font-medium">{item.text}</div>
                </Button>
        
                );

                if (item.description) {
                  return (
                    <TooltipProvider key={index}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          {button}
                        </TooltipTrigger>
                        <TooltipContent>
                          <p className="text-sm">{item.description}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  );
                }

                return button;
              })}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// The rest of your code remains the same
interface ResponseProps {
  children: GimlElement[];
}

interface ResponseItem {
  id: string;
  value: string;
}

const Response = ({ children }: ResponseProps) => {
  const responses = children.find(child => 
    child.type === 'responses'
  ) as GimlElement;

  if (!responses) return null;

  const responseItems = (responses.props.children as GimlElement[]).map((item): ResponseItem => ({
    id: item.props.id || '',
    value: item.props.value || ''
  }));

  return (
    <Card className="my-1.5">
      <CardContent className="p-2">
        <div className="flex items-start gap-2">
          <MessageCircle className="w-4 h-4 mt-1 text-green-500" />
          <div className="flex-1">
            <p className="text-[12px] font-medium text-gray-700 mb-2">Response</p>
            <div className="space-y-2">
              {responseItems.map((item, index) => {
                let displayValue = item.value;
                try {
                  // Try to parse JSON if it's a JSON string
                  const parsedValue = JSON.parse(item.value);
                  displayValue = JSON.stringify(parsedValue, null, 2);
                } catch {
                  // If not JSON, use as is
                  displayValue = item.value;
                }

                return (
                  <div key={index} className="bg-gray-50 rounded p-1">
                    <div className="text-[11px] text-gray-500 mb-1">ID: {item.id}</div>
                    <pre className="text-[11px] text-gray-950 bg-gray-50 overflow-x-auto p-0">
                      {displayValue}
                    </pre>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Then modify parseGiml to include response handling
export const parseGiml = (content: React.ReactNode[], onSelect?: (id: string, value: string) => void, isLastMessage?: boolean) => {
  if (!Array.isArray(content)) return content;

  const firstElement = content[0] as GimlElement;
  if (!firstElement || typeof firstElement !== 'object') return content;

  // Check for responses element
  if (content.some(child => (child as GimlElement).type === 'responses')) {
    return (
      <Response
        children={content as GimlElement[]}
      />
    );
  }

  // Check for select element
  if (content.some(child => (child as GimlElement).type === 'select')) {
    return (
      <Select
        children={content as GimlElement[]}
        onSelect={onSelect}
        isLastMessage={isLastMessage}
      />
    );
  }

  // Check for code element
  if (firstElement.props?.file) {
    return (
      <CodeDiff
        children={firstElement.props.children as GimlElement[]}
        file={firstElement.props.file}
      />
    );
  }

  return content;
};