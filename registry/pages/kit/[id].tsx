import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import { getFirestore, collection, query, where, getDocs } from 'firebase/firestore';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Package,
  FileCode,
  Settings,
  PlayCircle,
  FileText,
  ChevronRight,
} from 'lucide-react';

const PackageDetails = () => {
  const router = useRouter();
  const { id } = router.query;
  const [packageData, setPackageData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState<string | null>(null);
  const [fileLoading, setFileLoading] = useState(false);

  useEffect(() => {
    const fetchPackageDetails = async () => {
      if (!id) return;

      try {
        const db = getFirestore();
        const packagesRef = collection(db, 'packages');
        const q = query(packagesRef, where('kitConfig.id', '==', id));
        const querySnapshot = await getDocs(q);

        if (!querySnapshot.empty) {
          setPackageData(querySnapshot.docs[0].data());
        }
      } catch (error) {
        console.error('Error fetching package:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchPackageDetails();
  }, [id]);

  const handleFileClick = async (filePath: string) => {
    try {
      setSelectedFile(filePath);
      setFileLoading(true);

      const response = await fetch('/api/registry/file-content', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          downloadURL: packageData.downloadURL,
          filePath,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch file content');
      }

      const data = await response.json();
      setFileContent(data.content);
    } catch (error) {
      console.error('Error fetching file:', error);
      setFileContent('Error loading file content');
    } finally {
      setFileLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900" />
      </div>
    );
  }

  if (!packageData) {
    return <div>Package not found</div>;
  }

  const { kitConfig } = packageData;

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
          <Link href="/">Registry</Link>
          <ChevronRight className="h-4 w-4" />
          <span>{kitConfig.name}</span>
        </div>
        
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-bold mb-2">{kitConfig.name}</h1>
            <div className="flex gap-2 mb-4">
              <Badge>{kitConfig.owner}</Badge>
              <Badge variant="outline">v{kitConfig.version}</Badge>
              {kitConfig.docVersion && (
                <Badge variant="secondary">Doc {kitConfig.docVersion}</Badge>
              )}
            </div>
          </div>
        </div>
      </div>

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="workflows">Workflows</TabsTrigger>
          <TabsTrigger value="environment">Environment</TabsTrigger>
          <TabsTrigger value="files">Files</TabsTrigger>
          <TabsTrigger value="allFiles">All Files</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          {kitConfig.instructions?.documentation && (
            <Card>
              <CardHeader>
                <CardTitle>Documentation</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {kitConfig.instructions.documentation.map((doc: any) => (
                    <li key={doc.path} className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <span className="cursor-pointer hover:text-primary"
                            onClick={() => handleFileClick(`instructions/${doc.path}`)}>
                        {doc.name}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        - {doc.description}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {kitConfig.dependencies && (
            <Card>
              <CardHeader>
                <CardTitle>Dependencies</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {kitConfig.dependencies.map((dep: string) => (
                    <Badge key={dep} variant="secondary">
                      {dep}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="workflows" className="space-y-4">
          {Object.entries(kitConfig.workflows || {}).map(([name, workflow]: [string, any]) => (
            <Card key={name}>
              <CardHeader>
                <CardTitle className="capitalize">{name}</CardTitle>
              </CardHeader>
              <CardContent>
                {workflow.actions && (
                  <div className="space-y-2">
                    {workflow.actions.map((action: any) => (
                      <div key={action.path} className="flex items-center gap-2">
                        <PlayCircle className="h-4 w-4" />
                        <span>{action.name}</span>
                        <span className="text-sm text-muted-foreground">
                          - {action.description}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {workflow.instruction && (
                  <div className="mt-2 text-sm text-muted-foreground cursor-pointer hover:text-primary"
                       onClick={() => handleFileClick(`instructions/${workflow.instruction}`)}>
                    Instruction file: {workflow.instruction}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="environment" className="space-y-4">
          {kitConfig.environment && kitConfig.environment.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Environment Variables</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {kitConfig.environment.map((env: any) => (
                    <div key={env.name} className="space-y-1">
                      <div className="font-medium">{env.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {env.description}
                      </div>
                      {env.default && (
                        <div className="text-sm">
                          Default: <code>{env.default}</code>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="text-muted-foreground">
              No environment variables required
            </div>
          )}
        </TabsContent>

        <TabsContent value="files" className="space-y-4">
          {kitConfig.workspace?.files && (
            <Card>
              <CardHeader>
                <CardTitle>Workspace Files</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {kitConfig.workspace.files.map((file: any) => (
                    <li key={file.path} className="flex items-center gap-2">
                      <FileCode className="h-4 w-4" />
                      <span className="cursor-pointer hover:text-primary"
                            onClick={() => handleFileClick(file.path)}>
                        {file.path}
                      </span>
                      {file.description && (
                        <span className="text-sm text-muted-foreground">
                          - {file.description}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="allFiles" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>All Package Files</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Actions Files */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Action Files</h3>
                <div className="space-y-2 pl-4">
                  {Object.entries(kitConfig.workflows || {}).map(([workflowName, workflow]: [string, any]) => (
                    workflow.actions?.map((action: any) => {
                      const [filePath, functionName] = action.path.split(':');
                      return (
                        <div key={action.path} className="flex items-start gap-2">
                          <FileCode className="h-4 w-4 mt-1" />
                          <div>
                            <div className="font-medium cursor-pointer hover:text-primary"
                                 onClick={() => handleFileClick(`actions/${filePath}.py`)}>
                              actions/{filePath}.py
                            </div>
                            <div className="text-sm text-muted-foreground">
                              Function: {functionName}
                              {action.description && ` - ${action.description}`}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  ))}
                </div>
              </div>

              {/* Instruction Files */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Instruction Files</h3>
                <div className="space-y-2 pl-4">
                  {/* Documentation Instructions */}
                  {kitConfig.instructions?.documentation?.map((doc: any) => (
                    <div key={doc.path} className="flex items-start gap-2">
                      <FileText className="h-4 w-4 mt-1" />
                      <div>
                        <div className="font-medium cursor-pointer hover:text-primary"
                             onClick={() => handleFileClick(`instructions/${doc.path}`)}>
                          instructions/{doc.path}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Documentation: {doc.name}
                          {doc.description && ` - ${doc.description}`}
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Workflow Instructions */}
                  {Object.entries(kitConfig.workflows || {}).map(([workflowName, workflow]: [string, any]) => (
                    workflow.instruction && (
                      <div key={workflowName} className="flex items-start gap-2">
                        <FileText className="h-4 w-4 mt-1" />
                        <div>
                          <div className="font-medium cursor-pointer hover:text-primary"
                               onClick={() => handleFileClick(`instructions/${workflow.instruction}`)}>
                            instructions/{workflow.instruction}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Workflow: {workflowName} instructions
                          </div>
                        </div>
                      </div>
                    )
                  ))}
                </div>
              </div>

              {/* Workspace Files */}
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Workspace Files</h3>
                <div className="space-y-2 pl-4">
                  {kitConfig.workspace?.files?.map((file: any) => (
                    <div key={file.path} className="flex items-start gap-2">
                      <FileCode className="h-4 w-4 mt-1" />
                      <div>
                        <div className="font-medium cursor-pointer hover:text-primary"
                             onClick={() => handleFileClick(file.path)}>
                          {file.path}
                        </div>
                        {file.description && (
                          <div className="text-sm text-muted-foreground">
                            {file.description}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Configuration Files */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Configuration Files</h3>
                <div className="space-y-2 pl-4">
                  <div className="flex items-start gap-2">
                    <FileCode className="h-4 w-4 mt-1" />
                    <div>
                      <div className="font-medium cursor-pointer hover:text-primary"
                           onClick={() => handleFileClick('kit.yaml')}>
                        kit.yaml
                      </div>
                      <div className="text-sm text-muted-foreground">
                        Package configuration file
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={!!selectedFile} onOpenChange={() => {
        setSelectedFile(null);
        setFileContent(null);
      }}>
        <DialogContent className="max-w-3xl h-[80vh]">
          <DialogHeader>
            <DialogTitle>{selectedFile}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-auto">
            {fileLoading ? (
              <div className="flex justify-center items-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900" />
              </div>
            ) : (
              <pre className="p-4 bg-muted rounded-lg overflow-auto">
                <code>{fileContent}</code>
              </pre>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default PackageDetails;