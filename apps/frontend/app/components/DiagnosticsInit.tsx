'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { initDiagnostics, addBreadcrumb } from '../utils/diagnostics';

export default function DiagnosticsInit() {
  const pathname = usePathname();

  useEffect(() => {
    initDiagnostics();
  }, []);

  useEffect(() => {
    if (!pathname) return;
    addBreadcrumb({
      type: 'route',
      message: `Navigated to ${pathname}`,
      timestamp: new Date().toISOString(),
    });
  }, [pathname]);

  return null;
}
