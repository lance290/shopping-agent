/**
 * Safe JSON parsing utilities with type safety and validation
 *
 * These utilities replace unguarded JSON.parse calls throughout the application
 * to prevent runtime errors and provide better type safety.
 */

import type { JsonValue } from '../types';

/**
 * Safely parse JSON string with a fallback value
 *
 * @param json - JSON string to parse
 * @param fallback - Fallback value if parsing fails
 * @returns Parsed value or fallback
 *
 * @example
 * const data = safeJsonParse(row.choice_factors, []);
 * const config = safeJsonParse(userInput, { theme: 'light' });
 */
export function safeJsonParse<T>(json: string | null | undefined, fallback: T): T {
  if (!json || typeof json !== 'string' || json.trim() === '') {
    return fallback;
  }

  try {
    const parsed = JSON.parse(json);
    return parsed as T;
  } catch (error) {
    console.warn('[JSON] Failed to parse:', error instanceof Error ? error.message : 'Unknown error');
    return fallback;
  }
}

/**
 * Safely parse JSON with type validation using a validator function
 *
 * @param json - JSON string to parse
 * @param validator - Function to validate the parsed result
 * @param fallback - Fallback value if parsing or validation fails
 * @returns Validated parsed value or fallback
 *
 * @example
 * const factors = safeJsonParseWithValidator(
 *   row.choice_factors,
 *   (val): val is ChoiceFactor[] => Array.isArray(val),
 *   []
 * );
 */
export function safeJsonParseWithValidator<T>(
  json: string | null | undefined,
  validator: (value: unknown) => value is T,
  fallback: T
): T {
  if (!json || typeof json !== 'string' || json.trim() === '') {
    return fallback;
  }

  try {
    const parsed = JSON.parse(json);
    if (validator(parsed)) {
      return parsed;
    }
    console.warn('[JSON] Parsed value failed validation');
    return fallback;
  } catch (error) {
    console.warn('[JSON] Failed to parse:', error instanceof Error ? error.message : 'Unknown error');
    return fallback;
  }
}

/**
 * Safely stringify a value to JSON
 *
 * @param value - Value to stringify
 * @param fallback - Fallback string if stringification fails (default: "{}")
 * @returns JSON string or fallback
 *
 * @example
 * const json = safeJsonStringify({ name: 'test' });
 * const jsonWithCircular = safeJsonStringify(objectWithCircularRef, '{}');
 */
export function safeJsonStringify(value: unknown, fallback: string = '{}'): string {
  try {
    return JSON.stringify(value);
  } catch (error) {
    console.warn('[JSON] Failed to stringify:', error instanceof Error ? error.message : 'Unknown error');
    return fallback;
  }
}

/**
 * Type guard to check if a value is an array
 */
export function isArray(value: unknown): value is unknown[] {
  return Array.isArray(value);
}

/**
 * Type guard to check if a value is an object (not null or array)
 */
export function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * Type guard to check if a value is a string
 */
export function isString(value: unknown): value is string {
  return typeof value === 'string';
}

/**
 * Type guard to check if a value is a number
 */
export function isNumber(value: unknown): value is number {
  return typeof value === 'number' && !isNaN(value);
}

/**
 * Parse choice factors from row with validation
 */
export function parseChoiceFactors(json: string | null | undefined): Array<{
  name: string;
  type: string;
  label?: string;
  options?: string[];
  required?: boolean;
}> {
  return safeJsonParseWithValidator(
    json,
    (val): val is Array<{ name: string; type: string }> =>
      Array.isArray(val) &&
      val.every(
        (item) =>
          isObject(item) &&
          isString(item.name) &&
          isString(item.type)
      ),
    []
  );
}

/**
 * Parse choice answers from row
 */
export function parseChoiceAnswers(
  json: string | null | undefined
): Record<string, string | number | boolean | string[]> {
  return safeJsonParseWithValidator(
    json,
    (val): val is Record<string, string | number | boolean | string[]> => isObject(val),
    {}
  );
}

/**
 * Parse chat history from row with validation
 */
export function parseChatHistory(json: string | null | undefined): Array<{
  id: string;
  role: string;
  content: string;
}> {
  return safeJsonParseWithValidator(
    json,
    (val): val is Array<{ id: string; role: string; content: string }> =>
      Array.isArray(val) &&
      val.every(
        (msg) =>
          isObject(msg) &&
          isString(msg.id) &&
          isString(msg.role) &&
          isString(msg.content)
      ),
    []
  );
}
