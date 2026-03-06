import { useEffect, useState } from 'react';
import Link from 'next/link';

interface PopListFooterActionsProps {
  id: string;
  title: string;
  totalItems: number;
  isLoggedIn: boolean;
  hasJoined: boolean;
  isJoining: boolean;
  joinError: string | null;
  onJoinList: () => void;
}

export default function PopListFooterActions({
  id,
  title,
  totalItems,
  isLoggedIn,
  hasJoined,
  isJoining,
  joinError,
  onJoinList,
}: PopListFooterActionsProps) {
  const [isSharing, setIsSharing] = useState(false);
  const [copiedInvite, setCopiedInvite] = useState(false);
  const [copiedReferral, setCopiedReferral] = useState(false);
  const [referralLink, setReferralLink] = useState<string | null>(null);

  useEffect(() => {
    async function loadReferralLink() {
      if (!isLoggedIn) return;
      try {
        const refRes = await fetch('/api/pop/referral');
        if (refRes.ok) {
          const refData = await refRes.json();
          setReferralLink(refData.referral_link || null);
        }
      } catch {
        setReferralLink(null);
      }
    }
    loadReferralLink();
  }, [isLoggedIn]);

  return (
    <>
      {isLoggedIn && !hasJoined && (
        <div className="mt-4 bg-green-50 border border-green-200 rounded-2xl px-4 py-4 text-center">
          <p className="text-sm text-green-800 font-medium mb-3">
            Want to add items to this list together?
          </p>
          {joinError && (
            <p className="text-xs text-red-500 mb-2">{joinError}</p>
          )}
          <button
            onClick={onJoinList}
            disabled={isJoining}
            className="inline-flex items-center gap-2 bg-green-600 text-white text-sm font-semibold px-5 py-2.5 rounded-full hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            {isJoining ? 'Joining...' : '🤝 Join this list'}
          </button>
        </div>
      )}
      {isLoggedIn && hasJoined && (
        <div className="mt-4 bg-green-100 border border-green-300 rounded-2xl px-4 py-3 text-center">
          <p className="text-sm text-green-800 font-semibold">✓ You joined this list!</p>
          <Link
            href={`/pop-site/chat?list=${id}`}
            className="inline-block mt-2 text-sm text-green-700 underline hover:text-green-900"
          >
            Add items now →
          </Link>
        </div>
      )}
      {totalItems > 0 && (
        <div className="mt-6 space-y-3">
          <p className="text-center text-xs text-gray-500 font-medium uppercase tracking-wide">United we save</p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3" data-testid="dual-copylink">
            <button
              data-testid="copy-list-link"
              disabled={isSharing}
              onClick={async () => {
                setIsSharing(true);
                try {
                  let shareUrl = window.location.href;
                  if (isLoggedIn) {
                    const res = await fetch(`/api/pop/invite/${id}`, { method: 'POST' });
                    if (res.ok) {
                      const data = await res.json();
                      shareUrl = data.invite_url || shareUrl;
                    }
                  }
                  if (navigator.share) {
                    await navigator.share({ title, text: 'Join my grocery list on Pop! United we save.', url: shareUrl });
                  } else {
                    await navigator.clipboard.writeText(shareUrl);
                    setCopiedInvite(true);
                    setTimeout(() => setCopiedInvite(false), 2500);
                  }
                } finally {
                  setIsSharing(false);
                }
              }}
              className="inline-flex items-center gap-2 text-sm text-green-700 bg-green-50 hover:bg-green-100 font-medium px-5 py-2.5 rounded-full transition-colors disabled:opacity-50"
            >
              {copiedInvite ? '✓ List link copied!' : isSharing ? 'Creating link...' : '🏠 Share List with Family'}
            </button>
            {isLoggedIn && referralLink && (
              <button
                data-testid="copy-referral-link"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(referralLink);
                    setCopiedReferral(true);
                    setTimeout(() => setCopiedReferral(false), 2500);
                  } catch {
                    return;
                  }
                }}
                className="inline-flex items-center gap-2 text-sm text-purple-700 bg-purple-50 hover:bg-purple-100 font-medium px-5 py-2.5 rounded-full transition-colors"
              >
                {copiedReferral ? '✓ Referral link copied!' : '🤝 Refer Friends — Save $100/mo'}
              </button>
            )}
          </div>
        </div>
      )}
      <footer className="mt-12 py-6 text-center text-xs text-gray-400">
        <p>
          Powered by <Link href="/" className="text-green-600 hover:underline">Pop</Link> — your AI grocery savings assistant
        </p>
      </footer>
    </>
  );
}
