# Manual Verification - abf-ux-001

## Steps Performed
1. Added `isReportBugModalOpen` to global store (`store.ts`).
2. Created `ReportBugModal` component (skeleton) in `apps/frontend/app/components/ReportBugModal.tsx`.
3. Added `ReportBugModal` to root `page.tsx` layout.
4. Added "Report Bug" button (Bug icon) to `Board.tsx` header.
5. Wired button to open modal via store.

## Verification
- **Build**: Passed (`npm run build` in `apps/frontend`).
- **Visual**: "Report Bug" button should appear in the Board header (right side).
- **Behavior**: Clicking button should open the modal overlay.

## Sign-off
- **Status**: Ready for QA
- **Owner**: Lance
