'use client';

import { BadgeList } from './BadgeList';
import { MarkdownText } from './MarkdownText';
import { ActionRow } from './ActionRow';

interface MinimumViableRowProps {
  title?: string;
  status?: string;
}

export function MinimumViableRow({ title = 'Untitled', status = 'sourcing' }: MinimumViableRowProps) {
  return (
    <div className="space-y-2 p-3 bg-white rounded-lg border border-gray-200">
      <MarkdownText type="MarkdownText" content={`**${title}**`} />
      <BadgeList type="BadgeList" tags={[status]} />
      <ActionRow
        type="ActionRow"
        actions={[{ label: 'View Raw Options', intent: 'view_raw' }]}
      />
    </div>
  );
}
