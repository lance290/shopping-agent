# PRD: Phase 6 - Dual CopyLink Growth System (Household + Referral)

> **CRITICAL ARCHITECTURE NOTE:** PopSavings runs in the same monorepo as the primary `BuyAnything` application. You are free to integrate or share components, but you MUST NOT break, modify, or regress any core `BuyAnything` workflows, search APIs, or chat interfaces while implementing this PRD.

## 1. Overview
PopSavings needs to establish two powerful viral loops: 
1. Intra-household growth (inviting family to collaborate on a shared list).
2. Inter-household growth (referring other families/friends to PopSavings via an affiliate link).

This PRD introduces a Dual CopyLink system, providing users with two distinct links directly from the UI, and tracks referrers in the backend to drive wallet-based revenue shares (TeamPop).

## 2. Goals & Acceptance Criteria
- **Joint List Sharing:** Users can click a "Copy List Link" button that copies a stable, invite-capable URL for their specific list (Project).
- **TeamPop Referral Link:** Users can click a "Copy Referral Link" that includes their affiliate code. Kris and Peggy will power this TeamPop link, enabling users to share with their "Top150" network.
- **Messaging / Slogan:** The sharing flow should utilize the hook: "united we save" — helping Americans save $100/mo on their grocery bills.
- **Attribution & Wallet:** When a new user signs up via a referral link, the backend records the referrer. The system must issue a standard referral reward to the referrer's wallet.
- **Acceptance Criteria:**
  - UI displays two clear "Copy Link" actions (Share List vs. Refer Friends).
  - Clicking either copies the correct respective URL to the clipboard.
  - New user registration payload accepts a `ref` or `affiliate_code` parameter.
  - Test showing User B signing up with User A's code results in User A's wallet balance increasing.

## 3. Scope
- **Database:** Extend `User` model to include a unique `referral_code`. Add a `referred_by_id` column. Update the Wallet ledger to support "REFERRAL_BONUS" transaction types.
- **Backend:** 
  - Expose user referral codes in the user profile API.
  - Update auth/registration flow to accept and process the referral code, triggering the wallet reward asynchronously.
- **Frontend:** 
  - Add Share List UI component (generates `/list/{project_id}/join` or similar).
  - Add Refer Friends UI component (generates `/?ref={user_code}`).
  - Add `ref` query parameter detection on the landing/signup page to pass to the backend during account creation.

## 4. Technical Implementation Notes
### Backend (SQLModel / FastAPI)
- Modify `models.py`:
  - `User` table: `referral_code = Field(default=None, index=True)` (auto-generate a short nanoid on creation if blank).
  - `User` table: `referred_by_id = Field(foreign_key="user.id", default=None)`.
- Update `routes/auth.py` or equivalent user creation logic:
  - If `referral_code` is present in signup payload, query the referrer user.
  - Create the new user.
  - Call the wallet service (e.g., `services/wallet.py`) to add a credit to the referrer's account.

### Frontend (React)
- Create a `ShareMenu` or `CopyLinkGroup` component.
- Use `navigator.clipboard.writeText` to copy the links.
- Provide immediate toast/toast-notification feedback upon copy.
