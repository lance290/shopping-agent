# Task 05: Choice Factors + RFP System

**Priority:** P1  
**Estimated Time:** 2 days  
**Dependencies:** Task 01 (frontend), Task 04 (normalized offers)  
**Outcome:** LLM-driven requirements gathering, structured RFP display

---

## Objective

Implement the "choice factors" system from the PRD:
1. LLM identifies relevant decision criteria for a product category
2. Agent asks clarifying questions in chat
3. Answers stored as row-level FAQ/RFP
4. Request Tile shows choice factor highlights

---

## What Are Choice Factors?

For "laptop":
- **Budget** (number, required)
- **Primary Use** (select: gaming/work/school/general)
- **Screen Size** (select: 13"/15"/17")
- **Brand Preference** (text, optional)

For "wedding venue":
- **Guest Count** (number, required)
- **Indoor/Outdoor** (select)
- **Budget** (number)
- **Date Flexibility** (boolean)

The LLM determines these dynamically based on the product category.

---

## Implementation Steps

### Step 5.1: Add Choice Factor Fields to Row Model

**File:** `apps/backend/models.py`

```python
class RowBase(SQLModel):
    title: str
    status: str = "sourcing"
    budget_max: Optional[float] = None
    currency: str = "USD"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # NEW: Choice factors as JSON strings for MVP simplicity
    choice_factors: Optional[str] = None  # JSON array of ChoiceFactor objects
    choice_answers: Optional[str] = None  # JSON object of factor_name -> answer
```

**Choice Factor Schema (stored as JSON):**
```json
[
  {
    "name": "budget",
    "label": "What's your budget?",
    "type": "number",
    "required": true
  },
  {
    "name": "primary_use",
    "label": "Primary use case?",
    "type": "select",
    "options": ["gaming", "work", "school", "general"],
    "required": true
  }
]
```

- [ ] Add `choice_factors` column to Row
- [ ] Add `choice_answers` column to Row
- [ ] Create Alembic migration

**Test:** Can store and retrieve JSON in these columns

---

### Step 5.2: Create Alembic Migration

```bash
cd apps/backend
alembic revision --autogenerate -m "add_choice_factors_to_row"
alembic upgrade head
```

- [ ] Generate migration
- [ ] Verify columns added
- [ ] Test with sample data

---

### Step 5.3: Add getChoiceFactors LLM Tool

**File:** `apps/bff/src/llm.ts`

```typescript
getChoiceFactors: {
  description: 'Get relevant choice factors for a product category. Call this after creating a row to determine what questions to ask the user.',
  inputSchema: z.object({
    category: z.string().describe('The product category, e.g., "laptop", "wedding venue", "car"'),
    rowId: z.number().describe('The row ID to associate factors with'),
  }),
  execute: async (input: { category: string; rowId: number }) => {
    // Use LLM to generate choice factors (meta-prompting)
    const factorPrompt = `You are determining the key decision factors for purchasing: "${input.category}"

Return a JSON array of 3-6 choice factors. Each factor should have:
- name: lowercase_snake_case identifier
- label: Human-readable question
- type: "number" | "select" | "text" | "boolean"
- options: array of strings (only for "select" type)
- required: boolean

Example for "laptop":
[
  {"name": "budget", "label": "What's your maximum budget?", "type": "number", "required": true},
  {"name": "primary_use", "label": "Primary use?", "type": "select", "options": ["gaming", "work", "school", "general"], "required": true},
  {"name": "screen_size", "label": "Preferred screen size?", "type": "select", "options": ["13 inch", "15 inch", "17 inch"], "required": false}
]

Return ONLY the JSON array, no explanation.`;

    try {
      // Call LLM for factor generation
      const { text } = await generateText({
        model,
        prompt: factorPrompt,
      });
      
      const factors = JSON.parse(text);
      
      // Store factors on the row
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (authorization) {
        headers['Authorization'] = authorization;
      }
      
      await fetch(`${BACKEND_URL}/rows/${input.rowId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ choice_factors: JSON.stringify(factors) }),
      });
      
      return { 
        status: 'factors_generated', 
        row_id: input.rowId, 
        factors,
        next_action: 'Ask the user about these factors one at a time'
      };
    } catch (e) {
      return { status: 'error', error: String(e) };
    }
  },
},
```

- [ ] Add `getChoiceFactors` tool
- [ ] Import `generateText` from AI SDK
- [ ] Test with various product categories

**Test:** Tool generates sensible factors for "laptop", "shoes", "car"

---

### Step 5.4: Add saveChoiceAnswer LLM Tool

**File:** `apps/bff/src/llm.ts`

```typescript
saveChoiceAnswer: {
  description: 'Save a user\'s answer to a choice factor question. Call this when the user answers a question about their requirements.',
  inputSchema: z.object({
    rowId: z.number().describe('The row ID'),
    factorName: z.string().describe('The factor name (e.g., "budget", "primary_use")'),
    answer: z.union([z.string(), z.number(), z.boolean()]).describe('The user\'s answer'),
  }),
  execute: async (input: { rowId: number; factorName: string; answer: string | number | boolean }) => {
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (authorization) {
        headers['Authorization'] = authorization;
      }
      
      // Fetch current answers
      const rowRes = await fetch(`${BACKEND_URL}/rows/${input.rowId}`, { headers });
      const row = await rowRes.json() as any;
      
      // Parse existing answers or start fresh
      let answers: Record<string, any> = {};
      if (row.choice_answers) {
        try {
          answers = JSON.parse(row.choice_answers);
        } catch {}
      }
      
      // Add new answer
      answers[input.factorName] = input.answer;
      
      // Save back
      await fetch(`${BACKEND_URL}/rows/${input.rowId}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ choice_answers: JSON.stringify(answers) }),
      });
      
      return { 
        status: 'answer_saved', 
        row_id: input.rowId, 
        factor: input.factorName,
        answers 
      };
    } catch (e) {
      return { status: 'error', error: String(e) };
    }
  },
},
```

- [ ] Add `saveChoiceAnswer` tool
- [ ] Handle merge with existing answers

**Test:** Answers accumulate correctly on row

---

### Step 5.5: Update System Prompt for Factor Collection

**File:** `apps/bff/src/llm.ts`

Update the system prompt:

```typescript
system: `You are a procurement agent. Help users find items and manage their procurement board.

WORKFLOW FOR NEW REQUESTS:
1. When user asks for a new item, call createRow first
2. Then call getChoiceFactors to identify relevant decision criteria
3. Ask the user about EACH required factor, one at a time
4. After each answer, call saveChoiceAnswer
5. Once you have enough info (or user says "just search"), call searchListings

WORKFLOW FOR REFINEMENTS:
1. If user changes requirements, call updateRow then searchListings
2. If user answers a choice factor question, call saveChoiceAnswer

Be conversational but efficient. Don't ask too many questions before showing results.
${activeRowInstruction}`,
```

- [ ] Update system prompt
- [ ] Add workflow guidance for factor collection

**Test:** Agent asks questions before searching (when appropriate)

---

### Step 5.6: Update Row Interface in Frontend

**File:** `apps/frontend/app/store.ts`

```typescript
export interface Row {
  id: number;
  title: string;
  status: string;
  budget_max: number | null;
  currency: string;
  choice_factors?: string;   // JSON string
  choice_answers?: string;   // JSON string
}

// Helper to parse factors
export function parseChoiceFactors(row: Row): ChoiceFactor[] {
  if (!row.choice_factors) return [];
  try {
    return JSON.parse(row.choice_factors);
  } catch {
    return [];
  }
}

export function parseChoiceAnswers(row: Row): Record<string, any> {
  if (!row.choice_answers) return {};
  try {
    return JSON.parse(row.choice_answers);
  } catch {
    return {};
  }
}

export interface ChoiceFactor {
  name: string;
  label: string;
  type: 'number' | 'select' | 'text' | 'boolean';
  options?: string[];
  required: boolean;
}
```

- [ ] Add fields to Row interface
- [ ] Add parser helpers
- [ ] Add ChoiceFactor interface

**Test:** TypeScript compiles

---

### Step 5.7: Update RequestTile to Show Choice Factors

**File:** `apps/frontend/app/components/RequestTile.tsx`

```tsx
import { parseChoiceFactors, parseChoiceAnswers, Row, ChoiceFactor } from '../store';

interface RequestTileProps {
  row: Row;
  onClick?: () => void;
}

export default function RequestTile({ row, onClick }: RequestTileProps) {
  const factors = parseChoiceFactors(row);
  const answers = parseChoiceAnswers(row);
  
  // Show answered factors as highlights
  const answeredFactors = factors.filter(f => answers[f.name] !== undefined);
  
  return (
    <div 
      className="min-w-[200px] bg-blue-50 border-2 border-blue-200 rounded-lg p-3 flex-shrink-0 cursor-pointer hover:border-blue-400"
      onClick={onClick}
    >
      <div className="text-xs text-blue-600 font-medium mb-1">LOOKING FOR</div>
      <div className="font-medium text-sm">{row.title}</div>
      
      {answeredFactors.length > 0 && (
        <div className="mt-2 space-y-1">
          {answeredFactors.slice(0, 3).map(factor => (
            <div key={factor.name} className="text-xs text-gray-600">
              <span className="font-medium">{factor.name}:</span>{' '}
              {String(answers[factor.name])}
            </div>
          ))}
          {answeredFactors.length > 3 && (
            <div className="text-xs text-gray-400">
              +{answeredFactors.length - 3} more
            </div>
          )}
        </div>
      )}
      
      {answeredFactors.length === 0 && factors.length > 0 && (
        <div className="text-xs text-orange-500 mt-2">
          {factors.filter(f => f.required).length} questions pending
        </div>
      )}
      
      <div className="text-xs text-gray-400 mt-2">
        Click to refine
      </div>
    </div>
  );
}
```

- [ ] Parse and display choice factors
- [ ] Show answered factors as highlights
- [ ] Show pending required factors count

**Test:** RequestTile shows factor answers

---

### Step 5.8: Add Choice Factor Detail Panel (Optional)

**File:** `apps/frontend/app/components/ChoiceFactorPanel.tsx` (New)

A slide-out or modal panel showing all factors for a row:

```tsx
interface ChoiceFactorPanelProps {
  row: Row;
  isOpen: boolean;
  onClose: () => void;
}

export default function ChoiceFactorPanel({ row, isOpen, onClose }: ChoiceFactorPanelProps) {
  const factors = parseChoiceFactors(row);
  const answers = parseChoiceAnswers(row);
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full max-h-[80vh] overflow-y-auto">
        <h2 className="text-lg font-semibold mb-4">Requirements: {row.title}</h2>
        
        {factors.length === 0 ? (
          <p className="text-gray-500">No choice factors defined yet.</p>
        ) : (
          <div className="space-y-3">
            {factors.map(factor => (
              <div key={factor.name} className="border-b pb-2">
                <div className="font-medium text-sm">{factor.label}</div>
                <div className="text-sm text-gray-600">
                  {answers[factor.name] !== undefined 
                    ? String(answers[factor.name])
                    : <span className="text-orange-500">Not answered</span>
                  }
                </div>
              </div>
            ))}
          </div>
        )}
        
        <button
          onClick={onClose}
          className="mt-4 w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Close
        </button>
      </div>
    </div>
  );
}
```

- [ ] Create panel component (optional for MVP)
- [ ] Wire to RequestTile click

---

## Acceptance Criteria

- [ ] `choice_factors` and `choice_answers` columns on Row
- [ ] `getChoiceFactors` tool generates relevant factors from LLM
- [ ] `saveChoiceAnswer` tool stores user answers
- [ ] Agent asks clarifying questions before searching (configurable)
- [ ] RequestTile shows choice factor highlights
- [ ] Factors persist across sessions

---

## Example Flow

```
User: I need a laptop

Agent: ✅ Adding "laptop" to your procurement board...
       Let me understand your needs better.
       
       What's your maximum budget?

User: Around $1500

Agent: Got it - budget up to $1500.
       What will you primarily use it for?
       - Gaming
       - Work
       - School
       - General use

User: Work - I'm a software developer

Agent: Perfect - a developer workstation.
       🔍 Searching for laptops for developers under $1500...
       
       Found 12 results! [tiles appear]
```

---

## Files Changed

| File | Action |
|------|--------|
| `apps/backend/models.py` | Add choice_factors, choice_answers to Row |
| `apps/bff/src/llm.ts` | Add getChoiceFactors, saveChoiceAnswer tools |
| `apps/frontend/app/store.ts` | Add Row fields, parser helpers |
| `apps/frontend/app/components/RequestTile.tsx` | Show factor highlights |
| `apps/frontend/app/components/ChoiceFactorPanel.tsx` | **New** (optional) |
| `alembic/versions/` | New migration |
