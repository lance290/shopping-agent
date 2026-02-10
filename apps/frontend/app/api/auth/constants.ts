export const BACKEND_URL = process.env.BACKEND_URL || process.env.BFF_URL || 'http://localhost:8000';
/** @deprecated Use BACKEND_URL instead */
export const BFF_URL = BACKEND_URL;
export const COOKIE_NAME = 'sa_session';
