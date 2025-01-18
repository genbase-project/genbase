import React, { useState, useEffect } from 'react';
import { Allotment } from "allotment";
import { Tree, NodeRendererProps } from 'react-arborist';
import CodeEditor from '../CodeEditor';
import { ChevronRight, ChevronDown, Box } from 'lucide-react';
import { RuntimeModule } from '../TreeView';

interface TreeItem {
  id: string;
  name: string;
  children?: TreeItem[];
  isFolder?: boolean;
  content?: string;
  description?: string;
}

interface ApiResponse {
  path: string;
  name: string;
  content: string;
  description: string;
}

const TABS = ['documentation', 'specification', 'workspace'];

const buildTreeFromPaths = (items: ApiResponse[]): TreeItem[] => {
  const root: { [key: string]: TreeItem } = {};

  items.forEach(item => {
    const parts = item.path.split('/');
    let currentLevel = root;

    parts.forEach((part, index) => {
      const isLast = index === parts.length - 1;
      const id = parts.slice(0, index + 1).join('/');

      if (!currentLevel[id]) {
        currentLevel[id] = {
          id,
          name: part,
          isFolder: !isLast,
          children: isLast ? undefined : [],
          content: isLast ? item.content : undefined,
          description: isLast ? item.description : undefined
        };

        const parentId = parts.slice(0, index).join('/');
        if (index > 0 && root[parentId]) {
          root[parentId].children?.push(currentLevel[id]);
        }
      }

      currentLevel = currentLevel[id].children ? 
        root : 
        {};
    });
  });

  return Object.values(root).filter(item => !item.id.includes('/'));
};

const MainContent = ({selectedModule}:{selectedModule: RuntimeModule | null}) => {
  const [tabStateCache, setTabStateCache] = useState<{ [moduleId: string]: string }>({});
  const activeTab = selectedModule ? (tabStateCache[selectedModule.id] || TABS[0]) : TABS[0];
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [treeData, setTreeData] = useState<TreeItem[]>([]);
  const [contentCache, setContentCache] = useState<{ [key: string]: string }>({});

  useEffect(() => {
    if (!selectedModule) {
      setTreeData([]);
      setContentCache({});
      setSelectedNodeId(null);
      return;
    }

    const fetchData = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/resource/${selectedModule.id}/${activeTab}`
        );
        const data: ApiResponse[] = await response.json();
        const tree = buildTreeFromPaths(data);
        setTreeData(tree);

        const newCache: { [key: string]: string } = {};
        data.forEach(item => {
          newCache[item.path] = item.content;
        });
        setContentCache(newCache);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
  }, [selectedModule, activeTab]);

  if (!selectedModule) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center p-8">
          <h2 className="text-xl font-semibold text-gray-700 mb-2">No Module Selected</h2>
          <p className="text-gray-500">Select a module from the sidebar to explore its contents</p>
        </div>
      </div>
    );
  }

  const Node = React.forwardRef<HTMLDivElement, NodeRendererProps<TreeItem>>((props, ref) => {
    const { node, style } = props;
    const isSelected = node.id === selectedNodeId;
    
    const handleNodeClick = () => {
      if (node.isInternal) {
        node.toggle();
      }
      if (!node.data.isFolder) {
        setSelectedNodeId(node.id);
      }
    };
    
    return (
      <div 
        ref={ref}
        style={style}
        className={`flex items-center py-0.5 px-1 hover:bg-gray-100 ${
          isSelected ? 'bg-blue-50 hover:bg-blue-100' : ''
        }`}
        onClick={handleNodeClick}
      >
        <div className="flex items-center gap-1">
          {node.data.isFolder ? (
            <>
              {node.isOpen ? 
                <ChevronDown className="h-3 w-3 text-gray-400" /> : 
                <ChevronRight className="h-3 w-3 text-gray-400" />
              }
            </>
          ) : (
            <>
              <span className="w-3" />
              <Box className="h-3 w-3 text-gray-400" />
            </>
          )}
          <span className="text-sm">{node.data.name}</span>
        </div>
      </div>
    );
  });

  Node.displayName = 'Node';

  const handleTabChange = (tabId: string) => {
    if (selectedModule) {
      setTabStateCache(prev => ({
        ...prev,
        [selectedModule.id]: tabId
      }));
    }
    setSelectedNodeId(null);
  };

  const handleContentChange = (newValue: string) => {
    if (selectedNodeId) {
      setContentCache(prev => ({
        ...prev,
        [selectedNodeId]: newValue
      }));
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div className="flex h-8 items-center px-2 border-b">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => handleTabChange(tab)}
            className={`px-2 py-0.5 mx-1 rounded text-sm ${
              activeTab === tab
                ? 'bg-slate-100 hover:bg-slate-200'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="flex-1">
        <div className="h-full border rounded">
          <Allotment>
            <Allotment.Pane preferredSize={200} minSize={150}>
              <div className="h-full border-r">
                <Tree<TreeItem>
                  data={treeData}
                  width="100%"
                  height={800}
                  indent={16}
                  rowHeight={24}
                  overscanCount={1}
                >
                  {Node}
                </Tree>
              </div>
            </Allotment.Pane>

            <Allotment.Pane>
              <div className="h-full">
                {selectedNodeId ? (
                  <CodeEditor 
                    key={selectedNodeId}
                    value={contentCache[selectedNodeId] || '// No content available'}
                    onChange={handleContentChange}
                  />
                ) : (
                  <div className="p-4 text-gray-500">
                    Select a file to view its content
                  </div>
                )}
              </div>
            </Allotment.Pane>
          </Allotment>
        </div>
      </div>
    </div>
  );
};

export default MainContent;