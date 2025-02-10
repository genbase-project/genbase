import React from 'react';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Dialog, DialogContent, DialogTrigger } from "@/components/ui/dialog";
import { ChevronRight, Expand } from 'lucide-react';

interface EditBlock {
  filePath: string;
  original: string;
  updated: string;
}

interface CodeDiffViewerProps {
  content: string;
}

const parseEditXml = (xmlContent: string): EditBlock[] => {
  const editBlocks: EditBlock[] = [];
  const parser = new DOMParser();

  // Wrap in root element to parse multiple edit_file blocks
  const wrappedXml = `<edits>${xmlContent}</edits>`;
  const xmlDoc = parser.parseFromString(wrappedXml, 'text/xml');

  const editFiles = xmlDoc.getElementsByTagName('edit_file');

  for (let i = 0; i < editFiles.length; i++) {
    const editFile = editFiles[i];
    const filePath = editFile.getAttribute('file_path') || '';
    const original = editFile.getElementsByTagName('original')[0]?.textContent || '';
    const updated = editFile.getElementsByTagName('updated')[0]?.textContent || '';

    editBlocks.push({
      filePath,
      original,
      updated
    });
  }

  return editBlocks;
};

const CodeDiffViewer: React.FC<CodeDiffViewerProps> = ({ content }) => {
  try {
    const editBlocks = parseEditXml(content);

    return (
      <div className="space-y-1 text-[15px] leading-5">
        {editBlocks.map((block, index) => (
          <Collapsible key={index}>
            <div className="border rounded-lg overflow-hidden">
              <CollapsibleTrigger className="w-full">
                <div className="bg-gray-100 hover:bg-gray-200 transition-colors px-2 py-0.5 border-b flex items-center justify-between">
                  <span className="text-[11px] font-medium text-gray-700">{block.filePath}</span>
                  <div className="flex items-center gap-2">
                    <Dialog>
                      <DialogTrigger asChild>
                        <button className="hover:bg-gray-300/50 p-0.5 rounded">
                          <Expand className="w-3 h-3 text-gray-500" />
                        </button>
                      </DialogTrigger>
                      <DialogContent className="max-w-[90vw] max-h-[90vh] overflow-hidden flex flex-col">
                        <div className="text-sm font-medium mb-4 border-b pb-2">
                          {block.filePath}
                        </div>
                        <div className="overflow-auto flex-1 p-4">
                        <ReactDiffViewer
                          oldValue={block.original}
                          newValue={block.updated}
                          splitView={true}
                          hideLineNumbers={true}
                          showDiffOnly={true}
                          useDarkTheme={false}
                          disableWordDiff={true}
                          extraLinesSurroundingDiff={0}
                          compareMethod={DiffMethod.LINES}
                          styles={{
                            variables: {
                              light: {
                                diffViewerBackground: '#fff',
                                diffViewerColor: '#212529',
                                addedBackground: '#e6ffed',
                                addedColor: '#24292e',
                                removedBackground: '#ffeef0',
                                removedColor: '#24292e',
                              }
                            },
                            diffContainer: {
                              width: '100%'
                            },
                            line: {
                              padding: '4px 2px',
                              fontSize: '14px',
                              lineHeight: '1.3'
                            },
                            gutter: {
                              padding: '0 10px'
                            },
                            content: {
                              padding: '0 10px'
                            }
                          }}
                        />
                           </div> 
                      </DialogContent>
                    </Dialog>
                    <ChevronRight className="w-3 h-3 text-gray-500" />
                  </div>
                </div>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="text-[11px] leading-5 max-w-[800px] mx-auto">
                  <div className="overflow-hidden">
                    <ReactDiffViewer
                      oldValue={block.original}
                      newValue={block.updated}
                      splitView={true}
                 
                      hideLineNumbers={true}
                      showDiffOnly={true}
                      useDarkTheme={false}
                      disableWordDiff={true}
                      extraLinesSurroundingDiff={0}
                      compareMethod={DiffMethod.LINES}

                      styles={{
                        variables: {
                          light: {
                            diffViewerBackground: '#fff',
                            diffViewerColor: '#212529',
                            addedBackground: '#e6ffed',
                            addedColor: '#24292e',
                            removedBackground: '#ffeef0',
                            removedColor: '#24292e',
                          }
                        },
                        diffContainer: {
                          width: '100%',
                     
                        },
                        line: {
                          padding: 0,
                          fontSize: '15px',
                          lineHeight: '10px'
                        },
                        gutter: {
                          minWidth: '10px',
                          padding: '0 4px'
                        },
                        content: {
                          padding: '0 4px',
                          fontSize: '15px',
                          lineHeight: '10px'
                          
                        }

                      }}
                    />
                  </div>
                </div>
              </CollapsibleContent>
            </div>
          </Collapsible>
        ))}
      </div>
    );
  } catch (error) {
    console.error('Failed to parse edit XML:', error);
    // If XML parsing fails, return the original content
    return <pre className="whitespace-pre-wrap text-[11px]">{content}</pre>;
  }
};

export default CodeDiffViewer;
