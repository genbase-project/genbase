import { makeMarkdownText } from "@assistant-ui/react-markdown";
import { cn } from "@/lib/utils";

export const MarkdownText = makeMarkdownText({
  components: {
    // Style code blocks
    code: ({ className, children, ...props }) => {
      const match = /language-(\w+)/.exec(className || '');
      return (
        <code
          className={cn(
            "relative rounded bg-background-secondary px-[0.3rem] py-[0.2rem] font-mono text-sm",
            match && "block p-4",
            className
          )}
          {...props}
        >
          {children}
        </code>
      );
    },
    // Style headings
    h1: ({ className, ...props }) => (
      <h1 className={cn("mt-6 scroll-m-20 text-2xl font-bold", className)} {...props} />
    ),
    h2: ({ className, ...props }) => (
      <h2 className={cn("mt-5 scroll-m-20 text-xl font-semibold", className)} {...props} />
    ),
    h3: ({ className, ...props }) => (
      <h3 className={cn("mt-4 scroll-m-20 text-lg font-semibold", className)} {...props} />
    ),
    // Style links
    a: ({ className, ...props }) => (
      <a className={cn("text-blue-400 hover:text-blue-300 underline", className)} {...props} />
    ),
    // Style lists
    ul: ({ className, ...props }) => (
      <ul className={cn("my-2 ml-6 list-disc", className)} {...props} />
    ),
    ol: ({ className, ...props }) => (
      <ol className={cn("my-2 ml-6 list-decimal", className)} {...props} />
    ),
    // Style blockquotes
    blockquote: ({ className, ...props }) => (
      <blockquote
        className={cn(
          "mt-4 border-l-2 border-gray-500 pl-4 italic text-gray-300",
          className
        )}
        {...props}
      />
    ),
  },
});