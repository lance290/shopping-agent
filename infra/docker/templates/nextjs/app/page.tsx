export default function Home() {
  return (
    <main style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center', 
      minHeight: '100vh',
      padding: '2rem',
      fontFamily: 'system-ui, sans-serif'
    }}>
      <h1 style={{ fontSize: '3rem', marginBottom: '1rem' }}>
        Next.js 15 + TypeScript
      </h1>
      <p style={{ fontSize: '1.25rem', color: '#666' }}>
        Production-ready template from CFOI Framework
      </p>
      <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
        <a 
          href="/api/health" 
          target="_blank"
          style={{ 
            padding: '0.75rem 1.5rem', 
            background: '#0070f3', 
            color: 'white', 
            borderRadius: '0.5rem',
            textDecoration: 'none'
          }}
        >
          Check Health
        </a>
        <a 
          href="https://nextjs.org/docs" 
          target="_blank"
          style={{ 
            padding: '0.75rem 1.5rem', 
            border: '1px solid #eaeaea', 
            borderRadius: '0.5rem',
            textDecoration: 'none',
            color: '#333'
          }}
        >
          Documentation
        </a>
      </div>
    </main>
  );
}
