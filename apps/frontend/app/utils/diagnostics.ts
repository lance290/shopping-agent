export interface LogEntry {
  type: 'console' | 'network' | 'error';
  level: 'info' | 'warn' | 'error';
  message: string;
  details?: any;
  timestamp: string;
}

export interface BreadcrumbEntry {
  type: 'route' | 'ui' | 'system';
  message: string;
  details?: any;
  timestamp: string;
}

class RingBuffer<T> {
  private buffer: T[];
  private size: number;
  private pointer: number = 0;

  constructor(size: number = 50) {
    this.size = size;
    this.buffer = [];
  }

  add(item: T) {
    if (this.buffer.length < this.size) {
      this.buffer.push(item);
    } else {
      this.buffer[this.pointer] = item;
      this.pointer = (this.pointer + 1) % this.size;
    }
  }

  getAll(): T[] {
    if (this.buffer.length < this.size) {
      return [...this.buffer].sort((a: any, b: any) => 
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );
    }
    // Reconstruct order: from pointer to end, then 0 to pointer
    const ordered = [
      ...this.buffer.slice(this.pointer),
      ...this.buffer.slice(0, this.pointer)
    ];
    return ordered.sort((a: any, b: any) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }
}

// Singletons
const consoleBuffer = new RingBuffer<LogEntry>(50);
const networkBuffer = new RingBuffer<LogEntry>(20);
const breadcrumbBuffer = new RingBuffer<BreadcrumbEntry>(30);

// Initialization flag
let isInitialized = false;

export const initDiagnostics = () => {
  if (typeof window === 'undefined' || isInitialized) return;
  isInitialized = true;

  // 1. Console Capture
  const originalConsoleError = console.error;
  const originalConsoleWarn = console.warn;
  const originalConsoleLog = console.log;

  console.error = (...args) => {
    consoleBuffer.add({
      type: 'console',
      level: 'error',
      message: args.map(a => String(a)).join(' '),
      timestamp: new Date().toISOString()
    });
    originalConsoleError.apply(console, args);
  };

  console.warn = (...args) => {
    consoleBuffer.add({
      type: 'console',
      level: 'warn',
      message: args.map(a => String(a)).join(' '),
      timestamp: new Date().toISOString()
    });
    originalConsoleWarn.apply(console, args);
  };

  console.log = (...args) => {
    consoleBuffer.add({
      type: 'console',
      level: 'info',
      message: args.map(a => String(a)).join(' '),
      timestamp: new Date().toISOString()
    });
    originalConsoleLog.apply(console, args);
  };

  // 2. Global Error Capture
  window.addEventListener('error', (event) => {
    consoleBuffer.add({
      type: 'error',
      level: 'error',
      message: event.message,
      details: {
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno,
        stack: event.error?.stack
      },
      timestamp: new Date().toISOString()
    });
  });

  window.addEventListener('unhandledrejection', (event) => {
    consoleBuffer.add({
      type: 'error',
      level: 'error',
      message: `Unhandled Rejection: ${event.reason}`,
      timestamp: new Date().toISOString()
    });
  });

  // 3. Network Capture (Fetch Interceptor)
  const originalFetch = window.fetch;
  window.fetch = async (...args) => {
    const url = args[0].toString();
    // Skip diagnostics reporting calls to avoid loops
    if (url.includes('/api/bugs')) {
      return originalFetch(...args);
    }

    const startTime = performance.now();
    try {
      const response = await originalFetch(...args);
      
      if (!response.ok) {
        networkBuffer.add({
          type: 'network',
          level: 'error',
          message: `Fetch failed: ${response.status} ${response.statusText}`,
          details: {
            url,
            status: response.status,
            duration: Math.round(performance.now() - startTime)
          },
          timestamp: new Date().toISOString()
        });
      }
      return response;
    } catch (error) {
      networkBuffer.add({
        type: 'network',
        level: 'error',
        message: `Network error: ${String(error)}`,
        details: {
          url,
          duration: Math.round(performance.now() - startTime)
        },
        timestamp: new Date().toISOString()
      });
      throw error;
    }
  };
};

export const addBreadcrumb = (entry: BreadcrumbEntry) => {
  breadcrumbBuffer.add(entry);
};

const REDACT_KEYS = ['authorization', 'token', 'cookie', 'password', 'secret', 'api_key', 'apikey'];

const redactValue = (value: string) => {
  if (value.length <= 6) return '[REDACTED]';
  return `${value.slice(0, 3)}***${value.slice(-2)}`;
};

const redactObject = (obj: any, depth: number = 0): any => {
  if (obj === null || obj === undefined) return obj;
  if (depth > 4) return '[TRUNCATED]';

  if (typeof obj === 'string') {
    return obj.length > 200 ? `${obj.slice(0, 200)}...` : obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(item => redactObject(item, depth + 1));
  }

  if (typeof obj === 'object') {
    const redacted: Record<string, any> = {};
    for (const key of Object.keys(obj)) {
      const lowerKey = key.toLowerCase();
      if (REDACT_KEYS.some(k => lowerKey.includes(k))) {
        redacted[key] = '[REDACTED]';
      } else {
        redacted[key] = redactObject(obj[key], depth + 1);
      }
    }
    return redacted;
  }

  return obj;
};

export const redactDiagnostics = (payload: Record<string, any>) => {
  return redactObject(payload);
};

export const getDiagnostics = () => {
  return {
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'unknown',
    url: typeof window !== 'undefined' ? window.location.href : 'unknown',
    timestamp: new Date().toISOString(),
    logs: consoleBuffer.getAll(),
    network: networkBuffer.getAll(),
    breadcrumbs: breadcrumbBuffer.getAll(),
  };
};
