import React, { useState } from 'react';
import { Allotment } from "allotment";
import { UncontrolledTreeEnvironment, Tree, StaticTreeDataProvider } from 'react-complex-tree';
import CodeEditor from '../CodeEditor';
import { codeTreeItems } from '../../data/treeData';

interface MainContentProps {
  activeMainTab: string;
  setActiveMainTab: (tab: string) => void;
}

const MainContent: React.FC<MainContentProps> = ({ activeMainTab, setActiveMainTab }) => {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [codeContent, setCodeContent] = useState<string>('// Select a file to start coding');
  
  const tabs = ['Human Explanation', 'Specification', 'Data views', 'Access', 'Custom', 'code'];

  return (
    <div className="h-full flex flex-col bg-background">
      <div className="flex h-10 items-center px-4 border-b border-gray-800">
        {tabs.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveMainTab(tab.toLowerCase())}
            className={`px-3 py-1 mx-1 ${
              activeMainTab === tab.toLowerCase()
                ? 'bg-background-secondary  hover:text-white rounded '
                : 'text-gray-400 hover:text-white'
            }`}
          >
            
            {tab}
            
        
          </button>
        ))}
      </div>

      <div className="flex-1 p-4">
        {activeMainTab === 'code' && (
          <div className="bg-background border border-gray-800 rounded h-full">
            <Allotment>
              <Allotment.Pane preferredSize={200} minSize={150}>
                <div className="h-full border-r border-gray-800">
                  <UncontrolledTreeEnvironment
                    dataProvider={new StaticTreeDataProvider(codeTreeItems, (item, data) => ({ ...item, data }))}
                    getItemTitle={item => item.data}
                    viewState={{}}
                  >
                    <Tree treeId="code-tree" rootItem="root" treeLabel="Code Structure" />
                  </UncontrolledTreeEnvironment>
                </div>
              </Allotment.Pane>

              <Allotment.Pane>
                <div className="h-full">
                  <CodeEditor 
                    value={codeContent}
                    onChange={setCodeContent}
                  />
                </div>
              </Allotment.Pane>
            </Allotment>
          </div>
        )}
      </div>
    </div>
  );
};

export default MainContent;