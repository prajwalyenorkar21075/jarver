import { useState } from 'react'

interface SearchResult {
  title: string
  link: string
  snippet: string
}

export function WebSearchPanel() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const search = async () => {
    if (!query.trim()) return

    setIsSearching(true)
    setError(null)

    try {
      const res = await fetch(`/api/google/search?q=${encodeURIComponent(query)}`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResults(data.results || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed')
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 p-6 bg-black/40 backdrop-blur-xl border border-cyan-500/20 rounded-lg">
      <h2 className="text-2xl font-bold text-cyan-400 font-mono">WEB SEARCH</h2>

      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
          placeholder="Search the web..."
          className="flex-1 px-4 py-2 bg-black/60 border border-cyan-500/30 rounded text-white placeholder-gray-500 font-mono text-sm focus:outline-none focus:border-cyan-400"
        />
        <button
          onClick={search}
          disabled={isSearching}
          className="px-6 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 rounded text-cyan-300 font-mono text-sm disabled:opacity-50 transition-all"
        >
          {isSearching ? 'SEARCHING...' : 'SEARCH'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-400/30 rounded text-red-300 text-sm">
          Error: {error}
        </div>
      )}

      <div className="flex flex-col gap-3 max-h-96 overflow-y-auto">
        {results.map((result, idx) => (
          <div key={idx} className="p-3 bg-black/40 border border-cyan-500/20 rounded hover:border-cyan-400/40 transition-all">
            <a
              href={result.link}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:text-cyan-300 font-mono text-sm font-bold"
            >
              {result.title}
            </a>
            <div className="text-xs text-gray-400 mt-1">{result.link}</div>
            <div className="text-sm text-gray-300 mt-2">{result.snippet}</div>
          </div>
        ))}

        {results.length === 0 && !isSearching && !error && (
          <div className="text-center py-8 text-gray-500 font-mono">
            Enter a query to search the web
          </div>
        )}
      </div>
    </div>
  )
}
