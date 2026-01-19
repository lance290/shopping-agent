import { Row, Offer } from '../store';

// Helper: Persist row to database
export const persistRowToDb = async (rowId: number, title: string) => {
  console.log('[API] Persisting to DB:', rowId, title);
  try {
    const res = await fetch(`/api/rows?id=${rowId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (res.ok) {
      console.log('[API] DB persist success');
      return true;
    } else {
      console.error('[API] DB persist failed:', res.status);
      return false;
    }
  } catch (err) {
    console.error('[API] DB persist error:', err);
    return false;
  }
};

// Helper: Run search
export const runSearchApi = async (query: string, rowId?: number | null): Promise<Offer[]> => {
  console.log('[API] Running search:', query, 'for rowId:', rowId);
  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(rowId ? { query, rowId } : { query }),
    });
    const data = await res.json();
    return data.results || [];
  } catch (err) {
    console.error('[API] Search error:', err);
    return [];
  }
};

// Helper: Create a new row in database
export const createRowInDb = async (title: string): Promise<Row | null> => {
  console.log('[API] Creating row in DB:', title);
  try {
    const res = await fetch('/api/rows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        title, 
        status: 'sourcing',
        request_spec: {
          item_name: title,
          constraints: '{}'
        }
      }),
    });
    if (res.ok) {
      const newRow = await res.json();
      console.log('[API] Row created:', newRow);
      return newRow;
    } else {
      console.error('[API] Create row failed:', res.status, await res.text());
    }
  } catch (err) {
    console.error('[API] Create row error:', err);
  }
  return null;
};

// Helper: Fetch all rows from DB
export const fetchRowsFromDb = async (): Promise<Row[]> => {
  try {
    const res = await fetch('/api/rows');
    if (res.ok) {
      const rows = await res.json();
      return Array.isArray(rows) ? rows : [];
    } else {
      console.error('[API] fetchRowsFromDb failed:', res.status);
    }
  } catch (err) {
    console.error('[API] Fetch rows error:', err);
  }
  return [];
};

// Helper: Save choice answer
export const saveChoiceAnswerToDb = async (
  rowId: number,
  factorName: string,
  answer: string | number | boolean,
  existingAnswers?: Record<string, any>
): Promise<boolean> => {
  try {
    const answers: Record<string, any> = { ...(existingAnswers || {}) };
    answers[factorName] = answer;

    const res = await fetch(`/api/rows?id=${rowId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ choice_answers: JSON.stringify(answers) }),
    });
    
    return res.ok;
  } catch (err) {
    console.error('[API] Save answer error:', err);
    return false;
  }
};
