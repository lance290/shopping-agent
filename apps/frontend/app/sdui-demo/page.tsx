'use client';

import { useState } from 'react';
import { DynamicRenderer } from '../components/sdui/DynamicRenderer';

const GROCERY_SCHEMA = {
  version: 1,
  layout: 'ROW_MEDIA_LEFT',
  value_vector: 'unit_price',
  blocks: [
    { type: 'ProductImage', url: 'https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=200&h=200&fit=crop', alt: 'Organic Eggs' },
    { type: 'PriceBlock', amount: 3.49, currency: 'USD', label: 'Best Price' },
    { type: 'BadgeList', tags: ['Organic', 'Kroger', 'Pop Swap'] },
    { type: 'FeatureList', features: ['Free Range', 'Non-GMO', 'USDA Organic'] },
    { type: 'ActionRow', actions: [
      { label: 'View Deal', intent: 'outbound_affiliate', bid_id: '100', url: 'https://kroger.com/eggs' },
      { label: 'Claim $1.00 Swap', intent: 'claim_swap' },
    ]},
  ],
};

const JET_CHARTER_SCHEMA = {
  version: 1,
  layout: 'ROW_TIMELINE',
  value_vector: 'safety',
  blocks: [
    { type: 'MarkdownText', content: '**Private Jet Charter — SAN to ASE**' },
    { type: 'DataGrid', items: [
      { key: 'Origin', value: 'San Diego (SAN)' },
      { key: 'Destination', value: 'Aspen (ASE)' },
      { key: 'Passengers', value: '4' },
      { key: 'Date', value: 'February 13, 2026' },
      { key: 'Aircraft', value: 'Light Jet' },
    ]},
    { type: 'BadgeList', tags: ['Wyvern Wingman Certified', 'IS-BAO Stage 3'], source_refs: ['safety_cert_44', 'safety_cert_45'] },
    { type: 'Timeline', steps: [
      { label: 'Sourcing', status: 'done' },
      { label: 'Comparing', status: 'active' },
      { label: 'Negotiating', status: 'pending' },
      { label: 'Funded', status: 'pending' },
    ]},
    { type: 'ActionRow', actions: [
      { label: 'Request Firm Quotes', intent: 'contact_vendor' },
      { label: 'Leave a Tip', intent: 'send_tip', amount: 100 },
    ]},
  ],
};

const ESCROW_SCHEMA = {
  version: 3,
  layout: 'ROW_TIMELINE',
  blocks: [
    { type: 'MarkdownText', content: '**Yacht Charter — Mediterranean** \\n 7-day luxury charter, Dubrovnik to Split' },
    { type: 'PriceBlock', amount: 45000, currency: 'USD', label: 'Escrow Amount' },
    { type: 'EscrowStatus', deal_id: 'deal_789' },
    { type: 'Timeline', steps: [
      { label: 'Sourcing', status: 'done' },
      { label: 'Negotiating', status: 'done' },
      { label: 'Funded', status: 'active' },
      { label: 'In Transit', status: 'pending' },
      { label: 'Delivered', status: 'pending' },
    ]},
    { type: 'ActionRow', actions: [
      { label: 'Leave a Tip', intent: 'send_tip', amount: 500 },
    ]},
  ],
};

const SWAP_CLAIM_SCHEMA = {
  version: 2,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Eggs — Pop Swap Claimed!** \\n Scan your receipt to earn $1.00 back' },
    { type: 'BadgeList', tags: ['Pop Swap', 'Pending Receipt'] },
    { type: 'ReceiptUploader', campaign_id: 'camp_eggs_spring26' },
    { type: 'ActionRow', actions: [
      { label: 'Undo Claim', intent: 'claim_swap' },
    ]},
  ],
};

const COMPACT_TEXT_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Running Shoes** — comparing 12 options across 4 retailers' },
    { type: 'PriceBlock', amount: 89.99, currency: 'USD', label: 'From' },
    { type: 'BadgeList', tags: ['Amazon', 'Nike.com', 'eBay', 'Google Shopping'] },
    { type: 'ActionRow', actions: [
      { label: 'View on Amazon', intent: 'outbound_affiliate', bid_id: '200', url: 'https://amazon.com/shoes' },
      { label: 'View All (12)', intent: 'view_all_bids', count: 12 },
    ]},
  ],
};

const CHOICE_FACTOR_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Custom Engagement Ring** — help us narrow your options' },
    { type: 'ChoiceFactorForm', factors: [
      { name: 'budget', label: 'Budget Range', type: 'select', options: ['$5k-$10k', '$10k-$25k', '$25k-$50k', '$50k+'], required: true },
      { name: 'style', label: 'Ring Style', type: 'select', options: ['Solitaire', 'Halo', 'Three-Stone', 'Vintage'], required: false },
      { name: 'metal', label: 'Preferred Metal', type: 'text', required: false },
    ]},
    { type: 'ActionRow', actions: [
      { label: 'Find Options', intent: 'edit_request' },
    ]},
  ],
};

const ZERO_RESULTS_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: 'No options found for **Unobtainium Quantum Widget**' },
    { type: 'ActionRow', actions: [
      { label: 'Edit Request', intent: 'edit_request' },
      { label: 'View Raw Options', intent: 'view_raw' },
    ]},
  ],
};

const WALLET_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Your Savings Dashboard**' },
    { type: 'WalletLedger' },
    { type: 'BadgeList', tags: ['3 Swaps Claimed', '$4.50 Earned This Week'] },
    { type: 'ActionRow', actions: [
      { label: 'Share & Earn 30%', intent: 'edit_request' },
    ]},
  ],
};

const MESSAGE_HISTORY_SCHEMA = {
  version: 1,
  layout: 'ROW_COMPACT',
  blocks: [
    { type: 'MarkdownText', content: '**Vendor Conversation — NetJets**' },
    { type: 'MessageList', messages: [
      { sender: 'You', text: 'Looking for a light jet SAN to ASE, Feb 13, 4 passengers' },
      { sender: 'NetJets', text: 'We can offer a Citation CJ3+ for $18,500 one-way. Includes catering for 4.' },
      { sender: 'You', text: 'Can you do round-trip with a 3-day layover in Aspen?' },
    ]},
    { type: 'ActionRow', actions: [
      { label: 'Accept Quote', intent: 'fund_escrow', amount: 18500 },
      { label: 'Counter Offer', intent: 'contact_vendor' },
    ]},
  ],
};

type SchemaKey = 'grocery' | 'jet' | 'escrow' | 'swap' | 'compact' | 'choice' | 'zero' | 'wallet' | 'messages';

const SCHEMAS: Record<SchemaKey, { label: string; description: string; schema: Record<string, unknown> }> = {
  grocery: { label: 'Grocery Comparison', description: 'ROW_MEDIA_LEFT — image + price + badges + actions', schema: GROCERY_SCHEMA },
  jet: { label: 'Jet Charter (Service)', description: 'ROW_TIMELINE — specs grid + safety badges + progress', schema: JET_CHARTER_SCHEMA },
  escrow: { label: 'Escrow Funded', description: 'ROW_TIMELINE — post-purchase tracking with escrow status', schema: ESCROW_SCHEMA },
  swap: { label: 'Pop Swap Claimed', description: 'ROW_COMPACT — receipt uploader for swap redemption', schema: SWAP_CLAIM_SCHEMA },
  compact: { label: 'Product Search', description: 'ROW_COMPACT — text-heavy comparison with affiliate links', schema: COMPACT_TEXT_SCHEMA },
  choice: { label: 'Choice Factors', description: 'ROW_COMPACT — interactive form for refining bespoke requests', schema: CHOICE_FACTOR_SCHEMA },
  zero: { label: 'Zero Results', description: 'ROW_COMPACT — graceful empty state with edit action', schema: ZERO_RESULTS_SCHEMA },
  wallet: { label: 'Wallet / Savings', description: 'ROW_COMPACT — savings dashboard with wallet ledger', schema: WALLET_SCHEMA },
  messages: { label: 'Vendor Messages', description: 'ROW_COMPACT — conversation excerpt with accept/counter', schema: MESSAGE_HISTORY_SCHEMA },
};

export default function SDUIDemoPage() {
  const [active, setActive] = useState<SchemaKey>('grocery');
  const [showJson, setShowJson] = useState(false);
  const current = SCHEMAS[active];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">SDUI Component Demo</h1>
          <p className="text-sm text-gray-500 mt-1">
            Server-Driven UI primitives — the LLM selects layout + blocks, the builder hydrates with real data.
            No hardcoded templates. Same engine renders groceries, private jets, and everything in between.
          </p>
        </div>

        {/* Schema Selector */}
        <div className="flex flex-wrap gap-2 mb-6">
          {(Object.keys(SCHEMAS) as SchemaKey[]).map((key) => (
            <button
              key={key}
              onClick={() => setActive(key)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                active === key
                  ? 'bg-blue-600 text-white'
                  : 'bg-white text-gray-700 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              {SCHEMAS[key].label}
            </button>
          ))}
        </div>

        {/* Schema Info */}
        <div className="mb-4 text-sm text-gray-600">
          <span className="font-medium">{current.label}</span> — {current.description}
        </div>

        {/* Rendered Schema */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <DynamicRenderer
            schema={current.schema}
            fallbackTitle="Demo Item"
            fallbackStatus="demo"
          />
        </div>

        {/* JSON Toggle */}
        <div className="mt-4">
          <button
            onClick={() => setShowJson(!showJson)}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            {showJson ? 'Hide' : 'Show'} JSON Schema
          </button>
          {showJson && (
            <pre className="mt-2 bg-gray-900 text-green-400 rounded-lg p-4 text-xs overflow-x-auto max-h-96">
              {JSON.stringify(current.schema, null, 2)}
            </pre>
          )}
        </div>

        {/* Primitives Registry */}
        <div className="mt-12 border-t border-gray-200 pt-8">
          <h2 className="text-lg font-bold text-gray-900 mb-4">v0 Primitive Registry (13 blocks)</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {[
              { name: 'ProductImage', category: 'Display' },
              { name: 'PriceBlock', category: 'Display' },
              { name: 'DataGrid', category: 'Display' },
              { name: 'FeatureList', category: 'Display' },
              { name: 'BadgeList', category: 'Display' },
              { name: 'MarkdownText', category: 'Display' },
              { name: 'Timeline', category: 'Interactive' },
              { name: 'MessageList', category: 'Interactive' },
              { name: 'ChoiceFactorForm', category: 'Interactive' },
              { name: 'ActionRow', category: 'Interactive' },
              { name: 'ReceiptUploader', category: 'State-Driven' },
              { name: 'WalletLedger', category: 'State-Driven' },
              { name: 'EscrowStatus', category: 'State-Driven' },
            ].map((block) => (
              <div key={block.name} className="bg-white rounded-lg border border-gray-200 px-3 py-2">
                <p className="text-sm font-mono font-medium text-gray-800">{block.name}</p>
                <p className={`text-xs mt-0.5 ${
                  block.category === 'Display' ? 'text-blue-500' :
                  block.category === 'Interactive' ? 'text-purple-500' :
                  'text-amber-500'
                }`}>{block.category}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Layout Tokens */}
        <div className="mt-8 border-t border-gray-200 pt-8">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Layout Tokens</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <p className="font-mono text-sm font-bold text-gray-800">ROW_COMPACT</p>
              <p className="text-xs text-gray-500 mt-1">Dense text comparison. No images.</p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <p className="font-mono text-sm font-bold text-gray-800">ROW_MEDIA_LEFT</p>
              <p className="text-xs text-gray-500 mt-1">Visual comparison. Image + details.</p>
            </div>
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <p className="font-mono text-sm font-bold text-gray-800">ROW_TIMELINE</p>
              <p className="text-xs text-gray-500 mt-1">Fulfillment tracking. Progress view.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
