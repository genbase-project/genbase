import React, { useState, useEffect } from 'react';
import { FileText, Image, Video, File, Download, Music, Film, AlertTriangle } from 'lucide-react';
import CodeEditor from '../../../components/CodeEditor';
import MarkdownToJSX from 'markdown-to-jsx';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// Define types for viewer components
interface FileViewerProps {
  content: string | ArrayBuffer;
  onChange?: (value: string) => void;
  filePath: string;
  mimeType?: string;
  viewOnly?: boolean;
  fileSize?: number;
}

interface MarkdownViewerProps extends Omit<FileViewerProps, 'viewOnly'> {
  viewMode: 'preview' | 'code';
}

// Maximum size for binary files to be displayed as text (2MB)
const MAX_BINARY_TEXT_SIZE = 2 * 1024 * 1024;

// Function to try to convert binary data to readable text
const tryBinaryToText = (buffer: ArrayBuffer): string => {
  try {
    // Try UTF-8 first
    return new TextDecoder('utf-8').decode(buffer);
  } catch (e) {
    try {
      // Try Latin1 (ISO-8859-1) as fallback
      return new TextDecoder('iso-8859-1').decode(buffer);
    } catch (e) {
      // If all else fails, convert to hex representation
      const array = new Uint8Array(buffer);
      let hexString = '';
      for (let i = 0; i < Math.min(array.length, 1000); i++) {
        const hex = array[i].toString(16).padStart(2, '0');
        hexString += hex + (i % 16 === 15 ? '\n' : ' ');
      }
      if (array.length > 1000) {
        hexString += '\n... (truncated)';
      }
      return hexString;
    }
  }
};

// Text/Code Viewer Component
const CodeViewer: React.FC<FileViewerProps> = ({ content, onChange, viewOnly }) => {
  return (
    <CodeEditor 
      value={typeof content === 'string' ? content : '[Binary content cannot be displayed]'}
      onChange={onChange}
      readOnly={viewOnly}
    />
  );
};

// Markdown Viewer Component with preview/code toggle
const MarkdownViewer: React.FC<MarkdownViewerProps> = ({ content, onChange, viewMode }) => {
  if (viewMode === 'preview') {
    return (
      <div className="h-full w-full overflow-hidden">
        <ScrollArea className="h-full w-full overflow-auto" scrollHideDelay={0}>
          <div className="prose max-w-none p-4">
            <MarkdownToJSX options={{
              overrides: {
                h1: {
                  props: {
                    className: 'text-2xl font-bold my-4',
                  },
                },
                h2: {
                  props: {
                    className: 'text-xl font-bold my-3',
                  },
                },
                h3: {
                  props: {
                    className: 'text-lg font-bold my-2',
                  },
                },
                p: {
                  props: {
                    className: 'my-2',
                  },
                },
                ul: {
                  props: {
                    className: 'list-disc ml-5 my-2',
                  },
                },
                ol: {
                  props: {
                    className: 'list-decimal ml-5 my-2',
                  },
                },
                li: {
                  props: {
                    className: 'my-1',
                  },
                },
                blockquote: {
                  props: {
                    className: 'border-l-4 border-gray-200 pl-4 italic my-2',
                  },
                },
                code: {
                  props: {
                    className: 'bg-gray-100 rounded px-1 font-mono text-sm',
                  },
                },
                pre: {
                  props: {
                    className: 'bg-gray-100 rounded p-3 my-2 overflow-auto',
                  },
                },
              },
            }}>
              {typeof content === 'string' ? content : '[Binary content cannot be displayed]'}
            </MarkdownToJSX>
          </div>
        </ScrollArea>
      </div>
    );
  } else {
    return (
      <CodeEditor 
        value={typeof content === 'string' ? content : '[Binary content cannot be displayed]'}
        onChange={onChange}
      />
    );
  }
};

// Image Viewer Component
const ImageViewer: React.FC<FileViewerProps> = ({ content, filePath, mimeType }) => {
  // For base64 encoded content
  const src = typeof content === 'string' && content.startsWith('data:') 
    ? content 
    : `data:${mimeType || 'image/png'};base64,${
        typeof content === 'string' 
          ? btoa(content) 
          : arrayBufferToBase64(content)
      }`;
  
  return (
    <div className="h-full w-full flex items-center justify-center p-4 bg-gray-50">
      <div className="max-w-full max-h-full overflow-auto shadow-lg rounded">
        <img 
          src={src}
          alt={filePath.split('/').pop() || 'Image'} 
          className="max-w-full max-h-full object-contain"
        />
      </div>
    </div>
  );
};

// Video Viewer Component
const VideoViewer: React.FC<FileViewerProps> = ({ content, mimeType }) => {
  // For base64 encoded content
  const src = typeof content === 'string' && content.startsWith('data:') 
    ? content 
    : `data:${mimeType || 'video/mp4'};base64,${
        typeof content === 'string' 
          ? btoa(content) 
          : arrayBufferToBase64(content)
      }`;

  return (
    <div className="h-full w-full flex items-center justify-center p-4 bg-gray-50">
      <video 
        controls 
        className="max-w-full max-h-full shadow-lg rounded"
      >
        <source src={src} type={mimeType} />
        Your browser does not support video playback.
      </video>
    </div>
  );
};

// Audio Viewer Component
const AudioViewer: React.FC<FileViewerProps> = ({ content, mimeType }) => {
  // For base64 encoded content
  const src = typeof content === 'string' && content.startsWith('data:') 
    ? content 
    : `data:${mimeType || 'audio/mpeg'};base64,${
        typeof content === 'string' 
          ? btoa(content) 
          : arrayBufferToBase64(content)
      }`;

  return (
    <div className="h-full w-full flex flex-col items-center justify-center p-4 bg-gray-50">
      <Music className="h-16 w-16 text-gray-400 mb-4" />
      <audio controls className="w-full max-w-md shadow-lg rounded">
        <source src={src} type={mimeType} />
        Your browser does not support audio playback.
      </audio>
    </div>
  );
};

// Binary File Viewer Component with text view option and download
const BinaryViewer: React.FC<FileViewerProps> = ({ filePath, mimeType, content, fileSize = 0 }) => {
  const [viewMode, setViewMode] = useState<'download' | 'text'>('download');
  const [textContent, setTextContent] = useState<string>('');
  const fileName = filePath.split('/').pop() || 'file';
  
  useEffect(() => {
    if (viewMode === 'text' && content instanceof ArrayBuffer) {
      setTextContent(tryBinaryToText(content));
    }
  }, [viewMode, content]);
  
  // Only show text option if the binary file isn't too large
  const canViewAsText = fileSize <= MAX_BINARY_TEXT_SIZE;
  
  // Create a download link for the content
  const createDownloadLink = () => {
    let blob;
    if (typeof content === 'string') {
      // If we have a base64 string
      if (content.startsWith('data:')) {
        const base64Data = content.split(',')[1];
        blob = base64ToBlob(base64Data, mimeType);
      } else {
        // Assuming it's text content
        blob = new Blob([content], { type: mimeType });
      }
    } else {
      // ArrayBuffer
      blob = new Blob([new Uint8Array(content as ArrayBuffer)], { type: mimeType });
    }
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (canViewAsText) {
    return (
      <div className="h-full flex flex-col">
      
        <div className="flex-1 overflow-auto">
          <CodeEditor 
            value={textContent}
            readOnly={true}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col">
      <div className="p-2 bg-gray-100 border-b flex justify-between items-center">
 
        <div className="flex items-center gap-2">
       
          <Button 
            size="sm"
            variant="outline"
            onClick={createDownloadLink}
            className="h-8 text-xs gap-1"
          >
            <Download className="h-3 w-3" />
            Download
          </Button>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center p-8">
          <File className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-800 mb-2">{fileName}</h3>
          <p className="text-sm text-gray-500 mb-4">
            {mimeType || 'Binary file'} · {formatBytes(fileSize)}
          </p>
          {!canViewAsText && (
            <div className="flex items-center justify-center gap-2 text-amber-600 mb-4">
              <AlertTriangle className="h-4 w-4" />
              <p className="text-sm">File is too large to view as text</p>
            </div>
          )}
          <Button 
            onClick={createDownloadLink}
            className="flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Download File
          </Button>
        </div>
      </div>
    </div>
  );
};

// Helper function to format bytes into readable format
function formatBytes(bytes: number, decimals = 2): string {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Helper function to convert ArrayBuffer to Base64
function arrayBufferToBase64(buffer: ArrayBuffer): string {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const len = bytes.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

// Function to convert Base64 to Blob
function base64ToBlob(base64: string, contentType: string = '') {
  const byteCharacters = atob(base64);
  const byteArrays = [];
  for (let offset = 0; offset < byteCharacters.length; offset += 512) {
    const slice = byteCharacters.slice(offset, offset + 512);
    const byteNumbers = new Array(slice.length);
    for (let i = 0; i < slice.length; i++) {
      byteNumbers[i] = slice.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    byteArrays.push(byteArray);
  }
  return new Blob(byteArrays, { type: contentType });
}

// Define all the mime type matchers
const isTextFile = (mimeType?: string, fileName?: string): boolean => {
  if (!mimeType && !fileName) return true; // Default to text if no info
  
  // Check mime type first
  if (mimeType) {
    if (mimeType.startsWith('text/')) return true;
    if (['application/json', 'application/javascript', 'application/xml', 'application/xhtml+xml', 
         'application/x-sh', 'application/x-typescript'].includes(mimeType)) return true;
  }
  
  // Check file extension as backup
  if (fileName) {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext && ['txt', 'md', 'js', 'jsx', 'ts', 'tsx', 'html', 'htm', 'css', 'scss', 'json', 'xml', 
                'yaml', 'yml', 'sh', 'bash', 'py', 'rb', 'java', 'c', 'cpp', 'h', 'cs', 'go', 'rust', 
                'php', 'sql', 'log', 'cfg', 'conf'].includes(ext)) {
      return true;
    }
  }
  
  return false;
};

const isMarkdownFile = (filePath: string): boolean => {
  return filePath.toLowerCase().endsWith('.md') || filePath.toLowerCase().endsWith('.markdown');
};

const isImageFile = (mimeType?: string, fileName?: string): boolean => {
  if (mimeType?.startsWith('image/')) return true;
  
  if (fileName) {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext && ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico'].includes(ext)) {
      return true;
    }
  }
  
  return false;
};

const isVideoFile = (mimeType?: string, fileName?: string): boolean => {
  if (mimeType?.startsWith('video/')) return true;
  
  if (fileName) {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext && ['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'flv'].includes(ext)) {
      return true;
    }
  }
  
  return false;
};

const isAudioFile = (mimeType?: string, fileName?: string): boolean => {
  if (mimeType?.startsWith('audio/')) return true;
  
  if (fileName) {
    const ext = fileName.split('.').pop()?.toLowerCase();
    if (ext && ['mp3', 'wav', 'ogg', 'flac', 'aac', 'm4a'].includes(ext)) {
      return true;
    }
  }
  
  return false;
};

// Main component that determines which viewer to use based on file type
export const FileViewer: React.FC<{
  content: string | ArrayBuffer;
  filePath: string;
  mimeType?: string;
  viewMode?: 'preview' | 'code';
  onChange?: (value: string) => void;
  viewOnly?: boolean;
  fileSize?: number;
}> = ({ 
  content, 
  filePath,
  mimeType,
  viewMode = 'code',
  onChange,
  viewOnly = false,
  fileSize = typeof content === 'string' ? content.length : (content as ArrayBuffer).byteLength
}) => {
  // Determine the file type by mime type and file extension
  const fileName = filePath.split('/').pop();

  // Decide which viewer to use
  if (isMarkdownFile(filePath)) {
    return <MarkdownViewer 
      content={content} 
      onChange={onChange}
      filePath={filePath}
      mimeType={mimeType}
      viewMode={viewMode}
    />;
  } else if (isImageFile(mimeType, fileName)) {
    return <ImageViewer 
      content={content} 
      filePath={filePath}
      mimeType={mimeType}
    />;
  } else if (isVideoFile(mimeType, fileName)) {
    return <VideoViewer 
      content={content} 
      filePath={filePath}
      mimeType={mimeType}
    />;
  } else if (isAudioFile(mimeType, fileName)) {
    return <AudioViewer 
      content={content} 
      filePath={filePath}
      mimeType={mimeType}
    />;
  } else if (isTextFile(mimeType, fileName)) {
    return <CodeViewer 
      content={content} 
      onChange={onChange}
      filePath={filePath}
      mimeType={mimeType}
      viewOnly={viewOnly} 
    />;
  } else {
    // Binary file or unknown type
    return <BinaryViewer 
      content={content} 
      filePath={filePath}
      mimeType={mimeType}
      fileSize={fileSize}
    />;
  }
};

// Export component and type checks for use elsewhere
export {
  isTextFile,
  isMarkdownFile,
  isImageFile,
  isVideoFile,
  isAudioFile
};

export default FileViewer;