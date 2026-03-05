/**
 * Barrel re-export — all API functions and types.
 * Implementations live in api-*.ts sub-modules.
 * Existing imports from '../utils/api' continue to work unchanged.
 */

// Core utilities (also re-exported for any direct consumers)
export { AUTH_REQUIRED, fetchWithAuth, backendUrl, getAuthToken, readResponseBodySafe } from './api-core';

// Row / Project / Search
export type { SearchApiResponse } from './api-rows';
export {
  runSearchApiWithStatus,
  persistRowToDb,
  selectOfferForRow,
  createRowInDb,
  fetchSingleRowFromDb,
  fetchRowsFromDb,
  claimGuestRows,
  fetchProjectsFromDb,
  createProjectInDb,
  deleteProjectFromDb,
  duplicateProjectInDb,
  saveChoiceAnswerToDb,
  saveChatHistory,
} from './api-rows';

// Comments
export type { CommentDto } from './api-comments';
export { createCommentApi, fetchCommentsApi } from './api-comments';

// Likes
export { toggleLikeApi, fetchLikesApi } from './api-likes';

// Outreach
export type { CampaignDetails, CampaignMessage } from './api-outreach';
export {
  generateOutreachEmail,
  sendOutreachEmail,
  fetchContactStatuses,
  createQuoteLink,
  saveOutreachToDb,
  createOutreachCampaign,
  approveAndSendCampaign,
} from './api-outreach';

// Bugs
export type { BugReportResponse } from './api-bugs';
export { submitBugReport, fetchBugReport } from './api-bugs';

// Bids / Provenance
export type { ProvenanceData, ProductInfo, ChatExcerpt, BidWithProvenance } from './api-bids';
export { fetchBidWithProvenance } from './api-bids';

// Share Links
export type { ShareLinkCreate, ShareLinkResponse, ShareContentResponse, ShareMetricsResponse } from './api-shares';
export { createShareLink, resolveShareLink, getShareMetrics } from './api-shares';
