// components/elements.tsx
import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';
import { Card, CardContent } from "@/components/ui/card"; // Assuming path is correct
import { AlertCircle } from 'lucide-react';


interface SandboxedHtmlRendererProps {
  htmlContent: string;
}

export const SandboxedHtmlRenderer: React.FC<SandboxedHtmlRendererProps> = ({ htmlContent }) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [iframeHeight, setIframeHeight] = useState<string>('150px'); // Default height

  // Basic style to reset margin and ensure content flows within the iframe
  const iframeStyleOverrides = `
    <style>
      body { margin: 0; padding: 8px; overflow: auto; font-family: Inter, sans-serif; font-size: 13px; line-height: 1.5; color: #333; background-color: #fff; }
      img, video, embed, iframe, object { max-width: 100%; height: auto; } /* Basic responsive media */
      /* Add any other baseline styles needed for the sandboxed content */
    </style>
  `;

  const combinedSrcDoc = `${iframeStyleOverrides}${htmlContent}`;

  useEffect(() => {
    // Function to attempt resizing the iframe based on its content
    const resizeIframe = () => {
      if (iframeRef.current?.contentWindow?.document?.body) {
        // Use scrollHeight for potentially dynamic content height
        const contentHeight = iframeRef.current.contentWindow.document.body.scrollHeight;
        // Set a reasonable max height and a minimum height
        const newHeight = Math.min(Math.max(contentHeight, 50), 800); // Min 50px, Max 800px
        setIframeHeight(`${newHeight}px`);
      }
    };

    const iframe = iframeRef.current;
    if (iframe) {
      // Add listener for the load event
      iframe.addEventListener('load', resizeIframe);
      // Initial resize attempt shortly after render, might catch faster content
      const timer = setTimeout(resizeIframe, 250);

      // Cleanup function to remove listener
      return () => {
        iframe.removeEventListener('load', resizeIframe);
        clearTimeout(timer);
      };
    }
  }, [htmlContent]); // Rerun effect if htmlContent changes

  return (
    <div className="sandboxed-html-container my-1.5 border rounded-md overflow-hidden bg-white shadow-sm">
      <iframe
        ref={iframeRef}
        srcDoc={combinedSrcDoc}
        // SECURITY: Configure sandbox carefully. 'allow-scripts' enables JS execution.
        // Remove 'allow-scripts' if only static, non-interactive HTML is expected.
        // Avoid 'allow-same-origin', 'allow-forms', 'allow-popups' unless strictly necessary and source is trusted.
        sandbox="allow-scripts"
        title="Sandboxed HTML Content"
        width="100%"
        height={iframeHeight} // Dynamically set height
        style={{ border: 'none', display: 'block', transition: 'height 0.2s ease-in-out' }}
        loading="lazy" // Defer loading if offscreen
      />
    </div>
  );
};


// --- Mermaid Diagram Renderer ---

// Consider initializing Mermaid once in your main App or layout component:
// mermaid.initialize({ startOnLoad: false, theme: 'default', securityLevel: 'loose' });

interface MermaidRendererProps {
  chart: string; // The raw Mermaid code
}

export const MermaidRenderer: React.FC<MermaidRendererProps> = ({ chart }) => {
  const mermaidRef = useRef<HTMLDivElement>(null);
  const [hasError, setHasError] = useState(false);
  const [svgContent, setSvgContent] = useState<string | null>(null);
  // Unique ID for rendering, prevents conflicts if multiple charts are on the page
  const chartId = useRef(`mermaid-chart-${Math.random().toString(36).substring(2, 15)}`).current;

  useEffect(() => {
    if (!mermaid?.render) {
      console.warn("Mermaid library not ready for rendering.");
      setHasError(true); // Mark as error if mermaid isn't loaded
      return;
    }

    setHasError(false);
    setSvgContent(null); // Clear previous state

    if (chart && mermaidRef.current) {
      try {
        // Use mermaid.render to generate SVG directly
        mermaid.render(chartId, chart, (svgCode) => {
          setSvgContent(svgCode);
        }, mermaidRef.current); // Provide the container for context if needed by mermaid internals
      } catch (error) {
        console.error("Mermaid rendering error:", error);
        setHasError(true);
        setSvgContent(null);
      }
    } else {
      // If chart string is empty, ensure nothing is rendered
      setSvgContent(null);
    }
  }, [chart, chartId]); // Re-run if the chart content or unique ID changes

  return (
    <Card className="my-1.5 bg-white shadow-sm border rounded-md"> {/* Use Card for consistent look */}
      <CardContent className="p-3"> {/* Slightly more padding */}
        {hasError ? (
          <div className="flex items-center gap-2 text-red-600 text-xs p-2 bg-red-50 rounded">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>Failed to render Mermaid diagram. Please check the syntax.</span>
          </div>
        ) : (
          // Container div for the SVG
          <div
            ref={mermaidRef}
            id={`container-${chartId}`} // ID for potential targeting
            className="mermaid-diagram-container flex justify-center items-center" // Center diagram
            // Render the SVG string when available
            dangerouslySetInnerHTML={svgContent ? { __html: svgContent } : undefined}
            // Style to prevent collapsing and show loading state
            style={{ minHeight: svgContent ? 'auto' : '60px' }} // Ensure minimum height
          >
            {/* Show loading indicator only when SVG isn't ready and there's no error */}
            {!svgContent && !hasError && (
              <span className="text-xs text-gray-400 italic">Rendering diagram...</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// You can add other element renderers here in the future if needed.