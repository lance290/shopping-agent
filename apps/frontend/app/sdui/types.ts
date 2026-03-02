/**
 * SDUI Type Definitions — mirrors backend services/sdui_schema.py
 *
 * Single source of truth for frontend SDUI rendering.
 * See PRD-SDUI-Schema-Spec.md for the full contract.
 */

// ---------------------------------------------------------------------------
// Layout Tokens
// ---------------------------------------------------------------------------

export type LayoutToken = 'ROW_COMPACT' | 'ROW_MEDIA_LEFT' | 'ROW_TIMELINE';

export const LAYOUT_TOKENS: LayoutToken[] = ['ROW_COMPACT', 'ROW_MEDIA_LEFT', 'ROW_TIMELINE'];

// ---------------------------------------------------------------------------
// Value Vectors
// ---------------------------------------------------------------------------

export type ValueVector = 'unit_price' | 'safety' | 'speed' | 'reliability' | 'durability';

export const VALUE_VECTORS: ValueVector[] = ['unit_price', 'safety', 'speed', 'reliability', 'durability'];

// ---------------------------------------------------------------------------
// Action Intents
// ---------------------------------------------------------------------------

export type ActionIntent =
  | 'outbound_affiliate'
  | 'claim_swap'
  | 'fund_escrow'
  | 'send_tip'
  | 'contact_vendor'
  | 'view_all_bids'
  | 'view_raw'
  | 'edit_request';

export const ACTION_INTENTS: ActionIntent[] = [
  'outbound_affiliate',
  'claim_swap',
  'fund_escrow',
  'send_tip',
  'contact_vendor',
  'view_all_bids',
  'view_raw',
  'edit_request',
];

// ---------------------------------------------------------------------------
// Block Types (the 13 v0 Legos)
// ---------------------------------------------------------------------------

export type BlockType =
  | 'ProductImage'
  | 'PriceBlock'
  | 'DataGrid'
  | 'FeatureList'
  | 'BadgeList'
  | 'MarkdownText'
  | 'Timeline'
  | 'MessageList'
  | 'ChoiceFactorForm'
  | 'ActionRow'
  | 'ReceiptUploader'
  | 'WalletLedger'
  | 'EscrowStatus';

export const BLOCK_TYPES: BlockType[] = [
  'ProductImage',
  'PriceBlock',
  'DataGrid',
  'FeatureList',
  'BadgeList',
  'MarkdownText',
  'Timeline',
  'MessageList',
  'ChoiceFactorForm',
  'ActionRow',
  'ReceiptUploader',
  'WalletLedger',
  'EscrowStatus',
];

export const STATE_DRIVEN_BLOCKS: BlockType[] = ['ReceiptUploader', 'WalletLedger', 'EscrowStatus'];

// ---------------------------------------------------------------------------
// Block Data Shapes
// ---------------------------------------------------------------------------

export interface ProductImageBlock {
  type: 'ProductImage';
  url: string;
  alt: string;
}

export interface PriceBlockData {
  type: 'PriceBlock';
  amount: number | null;
  currency: string;
  label: string;
}

export interface DataGridItem {
  key: string;
  value: string;
}

export interface DataGridBlock {
  type: 'DataGrid';
  items: DataGridItem[];
}

export interface FeatureListBlock {
  type: 'FeatureList';
  features: string[];
}

export interface BadgeListBlock {
  type: 'BadgeList';
  tags: string[];
  source_refs?: string[];
}

export interface MarkdownTextBlock {
  type: 'MarkdownText';
  content: string;
}

export interface TimelineStep {
  label: string;
  status: 'pending' | 'active' | 'done';
}

export interface TimelineBlock {
  type: 'Timeline';
  steps: TimelineStep[];
}

export interface MessageItem {
  sender: string;
  text: string;
}

export interface MessageListBlock {
  type: 'MessageList';
  messages: MessageItem[];
}

export interface ChoiceFactorFormBlock {
  type: 'ChoiceFactorForm';
  factors: Record<string, any>[];
}

export interface ActionObject {
  label: string;
  intent: ActionIntent;
  bid_id?: string;
  url?: string;
  merchant_id?: string;
  product_id?: string;
  amount?: number;
  count?: number;
}

export interface ActionRowBlock {
  type: 'ActionRow';
  actions: ActionObject[];
}

export interface ReceiptUploaderBlock {
  type: 'ReceiptUploader';
  campaign_id: string;
}

export interface WalletLedgerBlock {
  type: 'WalletLedger';
}

export interface EscrowStatusBlock {
  type: 'EscrowStatus';
  deal_id: string;
}

// Union of all block types
export type UIBlock =
  | ProductImageBlock
  | PriceBlockData
  | DataGridBlock
  | FeatureListBlock
  | BadgeListBlock
  | MarkdownTextBlock
  | TimelineBlock
  | MessageListBlock
  | ChoiceFactorFormBlock
  | ActionRowBlock
  | ReceiptUploaderBlock
  | WalletLedgerBlock
  | EscrowStatusBlock;

// ---------------------------------------------------------------------------
// Top-Level Schema
// ---------------------------------------------------------------------------

export interface UISchema {
  version: number;
  layout: LayoutToken;
  value_vector?: ValueVector | null;
  value_rationale_refs?: string[];
  blocks: UIBlock[];
}

// ---------------------------------------------------------------------------
// UIHint (LLM output)
// ---------------------------------------------------------------------------

export interface UIHint {
  layout: LayoutToken;
  blocks: BlockType[];
  value_vector?: ValueVector | null;
}

// ---------------------------------------------------------------------------
// SSE Event
// ---------------------------------------------------------------------------

export interface UISchemaUpdatedEvent {
  entity_type: 'project' | 'row';
  entity_id: number;
  schema: UISchema;
  version: number;
  trigger: string;
}

// ---------------------------------------------------------------------------
// Validation Limits
// ---------------------------------------------------------------------------

export const LIMITS = {
  MAX_BLOCKS_PER_ROW: 8,
  MAX_MARKDOWN_LENGTH: 500,
  MAX_DATAGRID_ITEMS: 12,
  MAX_ACTION_ROW_ACTIONS: 3,
  GROCERY_BID_CAP: 5,
  RETAIL_BID_CAP: 30,
} as const;

// ---------------------------------------------------------------------------
// Validation Helpers
// ---------------------------------------------------------------------------

export function isValidLayoutToken(v: string): v is LayoutToken {
  return LAYOUT_TOKENS.includes(v as LayoutToken);
}

export function isValidBlockType(v: string): v is BlockType {
  return BLOCK_TYPES.includes(v as BlockType);
}

export function isValidActionIntent(v: string): v is ActionIntent {
  return ACTION_INTENTS.includes(v as ActionIntent);
}

export function isValidValueVector(v: string): v is ValueVector {
  return VALUE_VECTORS.includes(v as ValueVector);
}

export function validateUISchema(data: unknown): UISchema | null {
  if (!data || typeof data !== 'object') return null;
  const d = data as Record<string, unknown>;

  if (typeof d.version !== 'number') return null;
  if (typeof d.layout !== 'string' || !isValidLayoutToken(d.layout)) return null;
  if (!Array.isArray(d.blocks)) return null;

  // Enforce block limit
  const blocks = d.blocks.slice(0, LIMITS.MAX_BLOCKS_PER_ROW);

  // Strip unknown block types
  const validBlocks = blocks.filter(
    (b: unknown) => b && typeof b === 'object' && isValidBlockType((b as any).type)
  ) as UIBlock[];

  return {
    version: d.version,
    layout: d.layout as LayoutToken,
    value_vector: typeof d.value_vector === 'string' && isValidValueVector(d.value_vector) ? d.value_vector : null,
    value_rationale_refs: Array.isArray(d.value_rationale_refs) ? d.value_rationale_refs : undefined,
    blocks: validBlocks,
  };
}

export function getMinimumViableRow(title = 'Untitled', status = 'sourcing'): UISchema {
  return {
    version: 1,
    layout: 'ROW_COMPACT',
    blocks: [
      { type: 'MarkdownText', content: `**${title}**` },
      { type: 'BadgeList', tags: [status] },
      { type: 'ActionRow', actions: [{ label: 'View Raw Options', intent: 'view_raw' }] },
    ],
  };
}
