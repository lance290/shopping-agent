'use client';

import { validateUISchema } from '../../sdui/types';
import type { UIBlock } from '../../sdui/types';
import { ProductImage } from './ProductImage';
import { PriceBlock } from './PriceBlock';
import { DataGrid } from './DataGrid';
import { FeatureList } from './FeatureList';
import { BadgeList } from './BadgeList';
import { MarkdownText } from './MarkdownText';
import { Timeline } from './Timeline';
import { MessageList } from './MessageList';
import { ChoiceFactorForm } from './ChoiceFactorForm';
import { ActionRow } from './ActionRow';
import { ReceiptUploader } from './ReceiptUploader';
import { WalletLedger } from './WalletLedger';
import { EscrowStatus } from './EscrowStatus';
import { MinimumViableRow } from './MinimumViableRow';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const COMPONENT_REGISTRY: Record<string, React.ComponentType<any>> = {
  ProductImage,
  PriceBlock,
  DataGrid,
  FeatureList,
  BadgeList,
  MarkdownText,
  Timeline,
  MessageList,
  ChoiceFactorForm,
  ActionRow,
  ReceiptUploader,
  WalletLedger,
  EscrowStatus,
};

interface DynamicRendererProps {
  schema: unknown;
  fallbackTitle?: string;
  fallbackStatus?: string;
}

export function DynamicRenderer({ schema, fallbackTitle, fallbackStatus }: DynamicRendererProps) {
  const validated = validateUISchema(schema);

  if (!validated || !validated.blocks || validated.blocks.length === 0) {
    return <MinimumViableRow title={fallbackTitle} status={fallbackStatus} />;
  }

  const layoutClass = getLayoutClass(validated.layout);

  return (
    <div className={layoutClass} role="article">
      {validated.blocks.map((block: UIBlock, idx: number) => {
        const Component = COMPONENT_REGISTRY[block.type];
        if (!Component) {
          if (process.env.NODE_ENV === 'development') {
            return (
              <div key={idx} className="p-2 bg-yellow-100 text-yellow-800 text-xs rounded">
                [Unsupported block: {block.type}]
              </div>
            );
          }
          return null;
        }
        return <Component key={idx} {...block} />;
      })}
    </div>
  );
}

function getLayoutClass(layout: string): string {
  switch (layout) {
    case 'ROW_COMPACT':
      return 'space-y-2 p-3';
    case 'ROW_MEDIA_LEFT':
      return 'flex gap-4 p-3 items-start';
    case 'ROW_TIMELINE':
      return 'space-y-3 p-3 border-l-2 border-blue-200 pl-4';
    default:
      return 'space-y-2 p-3';
  }
}
