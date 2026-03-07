import { ItemComment, ItemLikeState, ListItem, TabType } from './types';

interface PopListItemCardProps {
  item: ListItem;
  isChecked: boolean;
  isExpanded: boolean;
  tab: TabType;
  shoppingMode: boolean;
  isLoggedIn: boolean;
  itemLike?: ItemLikeState;
  commentingItemId: number | null;
  commentText: string;
  itemComments: Record<number, ItemComment[]>;
  onToggleChecked: (itemId: number) => void;
  onToggleExpanded: (itemId: number) => void;
  onSetItemTab: (itemId: number, tab: TabType) => void;
  onQuantityChange: (itemId: number, qty: number) => void;
  onClaimDeal: (itemId: number, dealId: number) => void;
  onUnclaimDeal: (itemId: number, dealId: number) => void;
  onEditItem: (item: ListItem) => void;
  onToggleLike: (rowId: number) => void;
  onToggleComments: (rowId: number) => void;
  onSetCommentText: (value: string) => void;
  onSubmitComment: (rowId: number) => void;
}

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const seconds = Math.floor((new Date().getTime() - new Date(dateStr).getTime()) / 1000);
  let interval = seconds / 31536000;
  if (interval > 1) return Math.floor(interval) + 'y ago';
  interval = seconds / 2592000;
  if (interval > 1) return Math.floor(interval) + 'mo ago';
  interval = seconds / 86400;
  if (interval > 1) return Math.floor(interval) + 'd ago';
  interval = seconds / 3600;
  if (interval > 1) return Math.floor(interval) + 'h ago';
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + 'm ago';
  return Math.floor(seconds) + 's ago';
}

export default function PopListItemCard({
  item,
  isChecked,
  isExpanded,
  tab,
  shoppingMode,
  isLoggedIn,
  itemLike,
  commentingItemId,
  commentText,
  itemComments,
  onToggleChecked,
  onToggleExpanded,
  onSetItemTab,
  onQuantityChange,
  onClaimDeal,
  onUnclaimDeal,
  onEditItem,
  onToggleLike,
  onToggleComments,
  onSetCommentText,
  onSubmitComment,
}: PopListItemCardProps) {
  const selectedDeal = item.deals.find((d) => d.is_selected);
  const qty = parseInt(item.quantity || '1', 10) || 1;

  return (
    <li
      className={`bg-white rounded-2xl shadow-sm overflow-hidden transition-opacity ${
        isChecked ? 'opacity-60' : ''
      }`}
    >
      <div className="flex items-center gap-3 px-4 py-4">
        <button
          onClick={() => onToggleChecked(item.id)}
          className={`w-6 h-6 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
            isChecked
              ? 'bg-green-600 border-green-600'
              : 'border-gray-300 hover:border-green-400'
          }`}
        >
          {isChecked && (
            <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          )}
        </button>

        <button
          className="flex-1 min-w-0 text-left"
          onClick={() => onToggleExpanded(item.id)}
        >
          <span
            className={`text-sm font-medium block truncate ${
              isChecked ? 'line-through text-gray-400' : 'text-gray-900'
            }`}
          >
            {item.title}
          </span>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {item.department && (
              <span className="text-[10px] font-medium bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-full">
                {item.department}
              </span>
            )}
            {selectedDeal && (
              <span className="text-[10px] font-medium bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">
                ✓ {selectedDeal.title.slice(0, 30)}{selectedDeal.title.length > 30 ? '…' : ''} — ${selectedDeal.price?.toFixed(2) ?? '?'}
              </span>
            )}
            {!selectedDeal && item.lowest_price != null && (
              <span className="text-xs font-semibold text-green-700">
                from ${item.lowest_price.toFixed(2)}
              </span>
            )}
            {!selectedDeal && item.deal_count > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
                🏷️ {item.deal_count} deal{item.deal_count !== 1 ? 's' : ''}
              </span>
            )}
            {item.swaps.length > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">
                🔄 {item.swaps.length} swap{item.swaps.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </button>

        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => onQuantityChange(item.id, qty - 1)}
            disabled={qty <= 1}
            className="w-6 h-6 rounded-md bg-gray-100 text-gray-600 text-xs font-bold hover:bg-gray-200 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
          >
            −
          </button>
          <span className="w-5 text-center text-xs font-semibold text-gray-700">{qty}</span>
          <button
            onClick={() => onQuantityChange(item.id, qty + 1)}
            className="w-6 h-6 rounded-md bg-gray-100 text-gray-600 text-xs font-bold hover:bg-gray-200 flex items-center justify-center"
          >
            +
          </button>
        </div>

        {!shoppingMode && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onEditItem(item);
            }}
            className="p-1.5 flex-shrink-0 text-gray-300 hover:text-green-600 transition-colors"
            title="Edit item"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
        )}

        <button
          onClick={() => onToggleExpanded(item.id)}
          className="p-1 flex-shrink-0"
        >
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
      </div>

      {shoppingMode && selectedDeal && (
        <div className="flex items-center gap-2 px-4 pb-3">
          <a
            href={selectedDeal.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 text-center text-xs font-semibold py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors"
          >
            🛒 Buy Online
          </a>
          {item.coupon && (
            <a
              href={item.coupon.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 text-center text-xs font-semibold py-2 rounded-lg bg-amber-100 text-amber-800 hover:bg-amber-200 transition-colors"
            >
              🎟️ Store Coupon {item.coupon.savings_display}
            </a>
          )}
        </div>
      )}

      {item.coupon && (
        <div className="px-4 py-2 border-t border-gray-50" data-testid={`coupon-badge-${item.id}`}>
          <a
            href={item.coupon.url || '#'}
            target="_blank"
            rel="noopener noreferrer"
            className={`inline-flex items-center gap-2 rounded-lg px-3 py-1.5 transition-colors border ${
              item.coupon.is_sponsored
                ? 'bg-blue-50 border-blue-200 hover:bg-blue-100'
                : 'bg-amber-50 border-amber-200 hover:bg-amber-100'
            }`}
            onClick={(e) => e.stopPropagation()}
          >
            <span className="text-sm">{item.coupon.is_sponsored ? '⭐' : '🎟️'}</span>
            <span className={`text-xs font-semibold ${item.coupon.is_sponsored ? 'text-blue-800' : 'text-amber-800'}`}>
              {item.coupon.savings_display}
            </span>
            <span className={`text-[10px] ${item.coupon.is_sponsored ? 'text-blue-600' : 'text-amber-600'}`}>
              {item.coupon.is_sponsored ? 'Sponsored' : 'Clip Coupon'}{item.coupon.brand_name ? ` — ${item.coupon.brand_name}` : ''}
            </span>
          </a>
        </div>
      )}

      {isLoggedIn && (
        <div className="flex items-center gap-4 px-4 py-1.5 border-t border-gray-50" data-testid={`social-bar-${item.id}`}>
          <button
            data-testid={`like-btn-${item.id}`}
            onClick={() => onToggleLike(item.id)}
            className={`flex items-center gap-1 text-xs transition-colors ${
              itemLike?.liked ? 'text-red-500' : 'text-gray-400 hover:text-red-400'
            }`}
          >
            <svg className="w-4 h-4" fill={itemLike?.liked ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
            {(itemLike?.count || 0) > 0 && (
              <span>{itemLike?.count}</span>
            )}
          </button>
          <button
            data-testid={`comment-btn-${item.id}`}
            onClick={() => onToggleComments(item.id)}
            className={`flex items-center gap-1 text-xs transition-colors ${
              commentingItemId === item.id ? 'text-green-600' : 'text-gray-400 hover:text-green-500'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            {Math.max(item.comment_count || 0, itemComments[item.id]?.length || 0) > 0 && (
              <span>{Math.max(item.comment_count || 0, itemComments[item.id]?.length || 0)}</span>
            )}
          </button>
        </div>
      )}

      {commentingItemId === item.id && (
        <div className="px-4 py-3 border-t border-gray-100 bg-gray-50/50" data-testid={`comment-thread-${item.id}`}>
          {(itemComments[item.id] || []).map((c) => (
            <div key={c.id} className="flex gap-2 mb-2">
              <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                <span className="text-[10px] font-bold text-green-700">{(c.user_name || '?')[0].toUpperCase()}</span>
              </div>
              <div className="min-w-0">
                <span className="text-xs font-medium text-gray-700">{c.user_name}</span>
                {c.created_at && (
                  <span className="text-[10px] text-gray-400 ml-1">• {timeAgo(c.created_at)}</span>
                )}
                <p className="text-xs text-gray-600 mt-0.5">{c.text}</p>
              </div>
            </div>
          ))}
          <form
            className="flex gap-2 mt-2"
            onSubmit={(e) => {
              e.preventDefault();
              onSubmitComment(item.id);
            }}
          >
            <input
              type="text"
              value={commentText}
              onChange={(e) => onSetCommentText(e.target.value)}
              placeholder="Add a comment..."
              className="flex-1 text-xs px-3 py-1.5 rounded-lg border border-gray-200 focus:outline-none focus:ring-1 focus:ring-green-500 text-gray-900 placeholder-gray-400"
              maxLength={500}
            />
            <button
              type="submit"
              disabled={!commentText.trim()}
              className="text-xs font-medium text-green-600 hover:text-green-700 disabled:text-gray-300 disabled:cursor-not-allowed px-2"
            >
              Send
            </button>
          </form>
        </div>
      )}

      {isExpanded && (item.deals.length > 0 || item.swaps.length > 0) && (
        <div className="border-t border-gray-100">
          {item.swaps.length > 0 && (
            <div className="flex border-b border-gray-100">
              <button
                onClick={() => onSetItemTab(item.id, 'deals')}
                className={`flex-1 text-xs font-medium py-2.5 text-center transition-colors ${
                  tab === 'deals'
                    ? 'text-green-700 border-b-2 border-green-600'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                🏷️ Best Deals ({item.deals.length})
              </button>
              <button
                onClick={() => onSetItemTab(item.id, 'swaps')}
                className={`flex-1 text-xs font-medium py-2.5 text-center transition-colors ${
                  tab === 'swaps'
                    ? 'text-amber-700 border-b-2 border-amber-500'
                    : 'text-gray-400 hover:text-gray-600'
                }`}
              >
                🔄 Try Instead ({item.swaps.length})
              </button>
            </div>
          )}

          {tab === 'deals' && item.deals.length > 0 && (
            <div className="px-4 py-3 bg-green-50/30">
              <div className="space-y-2">
                {item.deals.map((deal) => (
                  <div
                    key={deal.id}
                    className={`flex items-center gap-3 bg-white rounded-xl px-3 py-2.5 transition-shadow ${
                      deal.is_selected ? 'ring-2 ring-emerald-400 shadow-sm' : 'hover:shadow-md'
                    }`}
                  >
                    <button
                      onClick={() => deal.is_selected ? onUnclaimDeal(item.id, deal.id) : onClaimDeal(item.id, deal.id)}
                      className={`w-5 h-5 rounded-full border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                        deal.is_selected
                          ? 'bg-emerald-500 border-emerald-500'
                          : 'border-gray-300 hover:border-emerald-400'
                      }`}
                      title={deal.is_selected ? 'Deselect this deal' : 'Select this deal'}
                    >
                      {deal.is_selected && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </button>
                    <a
                      href={deal.url || '#'}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 flex-1 min-w-0"
                    >
                      {deal.image_url ? (
                        <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 relative">
                          <img
                            src={deal.image_url}
                            alt=""
                            className="w-full h-full object-cover"
                          />
                        </div>
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center flex-shrink-0">
                          <span className="text-lg">🏷️</span>
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <span className="text-sm text-gray-900 block truncate">
                          {deal.title}
                        </span>
                        <span className="text-xs text-gray-500">{deal.source}</span>
                      </div>
                    </a>
                    {deal.price != null && (
                      <span className="text-sm font-semibold text-green-700 flex-shrink-0">
                        ${deal.price.toFixed(2)}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === 'swaps' && item.swaps.length > 0 && (
            <div className="px-4 py-3 bg-amber-50/30">
              <p className="text-xs text-amber-700 mb-2">
                Try these alternatives and save!
              </p>
              <div className="space-y-2">
                {item.swaps.map((swap) => (
                  <a
                    key={swap.id}
                    href={swap.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 bg-white rounded-xl px-3 py-2.5 hover:shadow-md transition-shadow"
                  >
                    {swap.image_url ? (
                      <div className="w-10 h-10 rounded-lg overflow-hidden flex-shrink-0 relative">
                        <img
                          src={swap.image_url}
                          alt=""
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
                        <span className="text-lg">🔄</span>
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <span className="text-sm text-gray-900 block truncate">
                        {swap.title}
                      </span>
                      <span className="text-xs text-gray-500">{swap.source}</span>
                    </div>
                    <div className="text-right flex-shrink-0">
                      {swap.price != null && (
                        <span className="text-sm font-semibold text-amber-700 block">
                          ${swap.price.toFixed(2)}
                        </span>
                      )}
                      {swap.savings_vs_first != null && swap.savings_vs_first > 0 && (
                        <span className="text-[10px] font-bold text-green-600">
                          Save ${swap.savings_vs_first.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </a>
                ))}
              </div>
            </div>
          )}

          {tab === 'deals' && item.deals.length === 0 && (
            <div className="px-4 py-6 text-center">
              <p className="text-xs text-gray-400">Pop is searching for deals...</p>
            </div>
          )}
        </div>
      )}
    </li>
  );
}
