import React from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { FileCode, MessageCircle } from 'lucide-react';
import { useChatStore } from "@/stores/chatStore";

// Types for GIML elements
interface GimlCodeDiff extends React.ReactElement {
  type: 'code_diff';
  props: {
    file: string;
    children: React.ReactNode;
  };
}

interface GimlSelectItem extends React.ReactElement {
  type: 'item';
  props: {
    description?: string;
    children: React.ReactNode;
  };
}

interface GimlSelect extends React.ReactElement {
  type: 'select';
  props: {
    id: string;
    children: GimlSelectItem[];
  };
}

interface GimlLabel extends React.ReactElement {
  type: 'label';
  props: {
    children: React.ReactNode;
  };
}

interface GimlResponse extends React.ReactElement {
  type: 'response';
  props: {
    id: string;
    value: string;
  };
}

interface GimlResponses extends React.ReactElement {
  type: 'responses';
  props: {
    children: GimlResponse[];
  };
}

// Helper function to safely get text content
const getTextContent = (children: React.ReactNode): string => {
  if (typeof children === 'string') return children;
  if (Array.isArray(children)) {
    return children.map(child => getTextContent(child)).join('');
  }
  if (React.isValidElement(children)) {
    return getTextContent(children.props.children || '');
  }
  return '';
};

// Type guards
const isSelectElement = (child: React.ReactNode): child is GimlSelect => {
  return React.isValidElement(child) && child.type === 'select';
};

const isLabelElement = (child: React.ReactNode): child is GimlLabel => {
  return React.isValidElement(child) && child.type === 'label';
};

const isCodeDiffElement = (child: React.ReactNode): child is GimlCodeDiff => {
  return React.isValidElement(child) && 
         typeof child.props.file === 'string' && 
         child.props.file.length > 0;
};

const isResponsesElement = (child: React.ReactNode): child is GimlResponses => {
  return React.isValidElement(child) && child.type === 'responses';
};

// Code diff component
const CodeDiff = ({ children, file }: { children: React.ReactNode; file: string }) => {
  const childArray = React.Children.toArray(children);
  
  const originalText = childArray.find(child =>
    React.isValidElement(child) && child.type === 'original'
  );
  
  const updatedText = childArray.find(child =>
    React.isValidElement(child) && child.type === 'updated'
  );

  return (
    <Card className="my-1.5">
      <CardContent className="p-2">
        <div className="flex items-start gap-2">
          <FileCode className="w-4 h-4 mt-1 text-blue-500" />
          <div className="flex-1">
            <p className="text-[12px] font-medium text-gray-700">{file}</p>
            <div className="mt-2 space-y-3">
              <div>
                <p className="text-[11px] font-medium text-red-600 mb-1">Original:</p>
                <pre className="bg-gray-50 p-2 rounded text-[11px] text-gray-950 overflow-x-auto">
                  {getTextContent(originalText)}
                </pre>
              </div>
              <div>
                <p className="text-[11px] font-medium text-green-600 mb-1">Updated:</p>
                <pre className="bg-gray-50 p-2 rounded text-[11px] text-gray-950 overflow-x-auto">
                  {getTextContent(updatedText)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Select component
interface SelectProps {
  selectId: string;
  items: Array<{
    text: string;
    description?: string;
  }>;
  isLastMessage: boolean;
}

const Select = ({ selectId, items, isLastMessage }: SelectProps) => {
  const sendResponse = useChatStore(state => state.sendResponse);

  if (items.length === 0) {
    console.log('No items found in select');
    return null;
  }

  return (
    <Card className={"my-1.5" + (isLastMessage ? " bg-gray-50" : "")}>
      <CardContent className="p-2">
        <div className="flex items-start gap-2">
          <MessageCircle className="w-4 h-4 mt-1 text-blue-500" />
          <div className="flex-1">
            <div className="mt-2 flex flex-wrap gap-1.5">
              {items.map((item, index) => (
                <button
                  key={index}
                  className={"px-3 h-7 min-w-[60px] text-[11px] border rounded " + 
                    (!isLastMessage ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:bg-gray-50")}
                  onClick={() => isLastMessage && sendResponse(selectId, item.text)}
                  disabled={!isLastMessage}
                  title={item.description}
                >
                  <div className="font-medium">{item.text}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Responses component
interface ResponsesProps {
  responses: Array<{
    id: string;
    value: string;
  }>;
}

const Responses = ({ responses }: ResponsesProps) => {
  if (!responses.length) return null;

  return (
    <Card className="my-1.5">
      <CardContent className="p-2">
        <div className="flex items-start gap-2">
          <MessageCircle className="w-4 h-4 mt-1 text-blue-500" />
          <div className="flex-1">
            {responses.map((response, index) => (
              <div key={index} className="flex items-center gap-2 text-[11px] text-gray-600">
                <span className="font-medium">{response.id}:</span>
                <span>{response.value}</span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

// Parse GIML content
export const parseGiml = (
  content: React.ReactNode[],
  isLastMessage: boolean = false
): React.ReactNode[] => {
  const children = React.Children.toArray(content);
  const elements: React.ReactNode[] = [];

  // Process each child element in sequence
  children.forEach((child, index) => {
    if (isCodeDiffElement(child)) {
      elements.push(
        <CodeDiff
          key={`code-diff-${index}`}
          file={child.props.file}
          children={child.props.children}
        />
      );
    }
    else if (isLabelElement(child)) {
      elements.push(
        <div key={`label-${index}`} className="text-gray-700 mb-2">
          {getTextContent(child)}
        </div>
      );
    }
    else if (isSelectElement(child)) {
      const items = React.Children.toArray(child.props.children)
        .filter(React.isValidElement)
        .map((item: any) => ({
          description: item.props.description as string | undefined,
          text: getTextContent(item.props.children)
        }));

      elements.push(
        <Select
          key={`select-${index}`}
          selectId={child.props.id}
          items={items}
          isLastMessage={isLastMessage}
        />
      );
    }
    else if (isResponsesElement(child)) {
      const responses = React.Children.toArray(child.props.children)
        .filter(React.isValidElement)
        .map((response: any) => ({
          id: response.props.id,
          value: response.props.value
        }));

      elements.push(
        <Responses
          key={`responses-${index}`}
          responses={responses}
        />
      );
    }
  });

  // If no elements were processed, show raw content for debugging
  if (elements.length === 0) {
    elements.push(
      <pre key="debug" className="bg-red-50 p-2 rounded text-xs">
        {children.map((child, i) => {
          if (React.isValidElement(child)) {
            return `Element ${i}: <${typeof child.type === 'string' ? child.type : 'Component'} />`;
          }
          return `Node ${i}: ${String(child)}`;
        }).join('\n')}
      </pre>
    );
  }

  return elements;
};