import React from 'react';
import Editor from '@monaco-editor/react';

interface CodeEditorProps {
  language?: string;
  value?: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ 
  language = 'javascript',
  value = '// Start coding here',
  onChange ,
  readOnly = true
}) => {
  const handleEditorChange = (value: string | undefined) => {
    if (onChange && value !== undefined) {
      onChange(value);
    }
  };

  return (
    <Editor
      height="100%"
      defaultLanguage={language}
      defaultValue={value}
      theme="vs-dark"
      onChange={handleEditorChange}
      options={{
        readOnly: true,
        minimap: { enabled: false },
        fontSize: 14,
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        automaticLayout: true,
        padding: { top: 10 }
      }}
    />
  );
};

export default CodeEditor;