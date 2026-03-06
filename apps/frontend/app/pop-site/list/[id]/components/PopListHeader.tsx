interface PopListHeaderProps {
  title: string;
  shoppingMode: boolean;
  isLoggedIn: boolean;
  selectedCount: number;
  totalItems: number;
  checkedCount: number;
  togglingMode: boolean;
  isClearing: boolean;
  onShowBulkParse: () => void;
  onShowHousehold: () => void;
  onToggleShoppingMode: () => void;
  onClearCompleted: () => void;
}

export default function PopListHeader({
  title,
  shoppingMode,
  isLoggedIn,
  selectedCount,
  totalItems,
  checkedCount,
  togglingMode,
  isClearing,
  onShowBulkParse,
  onShowHousehold,
  onToggleShoppingMode,
  onClearCompleted,
}: PopListHeaderProps) {
  return (
    <div className="mb-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <span>{shoppingMode ? '🛍️' : '🛒'}</span> {title}
        </h1>
        <div className="flex items-center gap-2">
          {!shoppingMode && isLoggedIn && (
            <button
              onClick={onShowBulkParse}
              className="text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 px-3 py-1.5 rounded-full transition-colors flex items-center gap-1"
            >
              📋 Paste Recipe
            </button>
          )}
          {!shoppingMode && isLoggedIn && (
            <button
              onClick={onShowHousehold}
              className="text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 px-3 py-1.5 rounded-full transition-colors flex items-center gap-1"
            >
              👨‍👩‍👧 Household
            </button>
          )}
          {shoppingMode && (
            <button
              onClick={() => window.print()}
              className="text-xs font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 px-3 py-1.5 rounded-full transition-colors flex items-center gap-1"
            >
              🖨️ Print
            </button>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between mt-2">
        <p className="text-sm text-gray-500">
          {shoppingMode
            ? `${selectedCount} selected item${selectedCount !== 1 ? 's' : ''} — Shopping Mode`
            : checkedCount > 0
              ? `${checkedCount} of ${totalItems} checked off`
              : `${totalItems} item${totalItems !== 1 ? 's' : ''}`}
          {!shoppingMode && selectedCount > 0 && (
            <span className="ml-2 text-emerald-700 font-medium">
              · {selectedCount} picked
            </span>
          )}
        </p>
        <div className="flex items-center gap-2">
          {checkedCount > 0 && isLoggedIn && !shoppingMode && (
            <button
              onClick={onClearCompleted}
              disabled={isClearing}
              className="text-xs font-medium text-gray-500 hover:text-red-600 transition-colors flex items-center gap-1 disabled:opacity-50"
            >
              {isClearing ? 'Clearing...' : '🗑️ Clear Completed'}
            </button>
          )}
        </div>
      </div>
      {isLoggedIn && (
        <button
          onClick={onToggleShoppingMode}
          disabled={togglingMode}
          className={`mt-3 w-full py-2.5 rounded-xl text-sm font-semibold transition-colors disabled:opacity-50 ${
            shoppingMode
              ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              : 'bg-green-600 text-white hover:bg-green-700'
          }`}
        >
          {togglingMode
            ? '...'
            : shoppingMode
              ? '✏️ Edit List'
              : selectedCount > 0
                ? `🛍️ Ready to Shop (${selectedCount})`
                : '🛍️ Ready to Shop'}
        </button>
      )}
    </div>
  );
}
