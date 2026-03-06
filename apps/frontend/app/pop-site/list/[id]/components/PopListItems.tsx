import Link from 'next/link';
import { ItemComment, ItemLikeState, ListItem, TabType } from './types';
import PopListItemCard from './PopListItemCard';

interface PopListItemsProps {
  totalItems: number;
  visibleItems: ListItem[];
  checkedItems: Set<number>;
  expandedItems: Set<number>;
  shoppingMode: boolean;
  isLoggedIn: boolean;
  itemLikes: Record<number, ItemLikeState>;
  commentingItemId: number | null;
  commentText: string;
  itemComments: Record<number, ItemComment[]>;
  onToggleChecked: (itemId: number) => void;
  onToggleExpanded: (itemId: number) => void;
  getItemTab: (itemId: number) => TabType;
  onSetItemTab: (itemId: number, tab: TabType) => void;
  onQuantityChange: (itemId: number, qty: number) => void;
  onClaimDeal: (itemId: number, dealId: number) => void;
  onUnclaimDeal: (itemId: number, dealId: number) => void;
  onClaimSwap: (itemId: number, swapId: number) => void;
  onUnclaimSwap: (itemId: number, swapId: number) => void;
  onEditItem: (item: ListItem) => void;
  onToggleLike: (rowId: number) => void;
  onToggleComments: (rowId: number) => void;
  onSetCommentText: (value: string) => void;
  onSubmitComment: (rowId: number) => void;
}

export default function PopListItems({
  totalItems,
  visibleItems,
  checkedItems,
  expandedItems,
  shoppingMode,
  isLoggedIn,
  itemLikes,
  commentingItemId,
  commentText,
  itemComments,
  onToggleChecked,
  onToggleExpanded,
  getItemTab,
  onSetItemTab,
  onQuantityChange,
  onClaimSwap,
  onUnclaimSwap,
  onClaimDeal,
  onUnclaimDeal,
  onEditItem,
  onToggleLike,
  onToggleComments,
  onSetCommentText,
  onSubmitComment,
}: PopListItemsProps) {
  if (totalItems === 0) {
    return (
      <div className="text-center py-16">
        <span className="text-5xl block mb-4">📝</span>
        <p className="text-gray-500 mb-4">Your list is empty</p>
        <Link
          href="/chat"
          className="inline-block bg-green-600 text-white font-medium px-6 py-3 rounded-xl hover:bg-green-700 transition-colors"
        >
          Chat with Pop to add items
        </Link>
      </div>
    );
  }

  return (
    <ul className="space-y-3">
      {visibleItems.map((item) => {
        return (
          <PopListItemCard
            key={item.id}
            item={item}
            isChecked={checkedItems.has(item.id)}
            isExpanded={expandedItems.has(item.id)}
            tab={getItemTab(item.id)}
            shoppingMode={shoppingMode}
            isLoggedIn={isLoggedIn}
            itemLike={itemLikes[item.id]}
            commentingItemId={commentingItemId}
            commentText={commentText}
            itemComments={itemComments}
            onToggleChecked={onToggleChecked}
            onToggleExpanded={onToggleExpanded}
            onSetItemTab={onSetItemTab}
            onQuantityChange={onQuantityChange}
            onClaimDeal={onClaimDeal}
            onUnclaimDeal={onUnclaimDeal}
            onClaimSwap={onClaimSwap}
            onUnclaimSwap={onUnclaimSwap}
            onEditItem={onEditItem}
            onToggleLike={onToggleLike}
            onToggleComments={onToggleComments}
            onSetCommentText={onSetCommentText}
            onSubmitComment={onSubmitComment}
          />
        );
      })}
    </ul>
  );
}
