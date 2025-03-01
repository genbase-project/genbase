import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import type { ReactNode } from 'react';
import { baseOptions } from '@/app/layout.config';
import { source } from '@/lib/source';

export default function Layout({ children }: { children: ReactNode }) {
  return (
  // @ts-expect-error - Component accepts children in practice despite type definition
  <DocsLayout tree={source.pageTree} {...baseOptions}>
  {children}
</DocsLayout>
  );
}
