import { useState } from 'react'

interface AnalysisResult {
  summary: string
  key_points: string[]
  entities: string[]
  sentiment?: string
}

export function DocumentAnalysisPanel() {
  const [file, setFile] = useState<File | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (selected) {
      setFile(selected)
      setResult(null)
      setError(null)
    }
  }

  const analyze = async () => {
    if (!file) return

    setIsAnalyzing(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/document/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResult(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 p-6 bg-black/40 backdrop-blur-xl border border-cyan-500/20 rounded-lg">
      <h2 className="text-2xl font-bold text-cyan-400 font-mono">DOCUMENT ANALYSIS</h2>

      <div className="flex flex-col gap-2">
        <input
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.txt,.doc,.docx,.md"
          className="px-4 py-2 bg-black/60 border border-cyan-500/30 rounded text-white font-mono text-sm file:mr-4 file:py-1 file:px-4 file:border-0 file:bg-cyan-500/20 file:text-cyan-300 file:font-mono file:text-sm hover:file:bg-cyan-500/30"
        />
        {file && (
          <div className="text-xs text-gray-400 font-mono">
            Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
          </div>
        )}
        <button
          onClick={analyze}
          disabled={!file || isAnalyzing}
          className="px-6 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 rounded text-cyan-300 font-mono text-sm disabled:opacity-50 transition-all"
        >
          {isAnalyzing ? 'ANALYZING...' : 'ANALYZE DOCUMENT'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-400/30 rounded text-red-300 text-sm">
          Error: {error}
        </div>
      )}

      {result && (
        <div className="flex flex-col gap-4">
          <div className="p-3 bg-black/40 border border-cyan-500/20 rounded">
            <div className="text-sm text-cyan-400 font-mono font-bold mb-2">SUMMARY</div>
            <div className="text-sm text-gray-300">{result.summary}</div>
          </div>

          {result.key_points.length > 0 && (
            <div className="p-3 bg-black/40 border border-cyan-500/20 rounded">
              <div className="text-sm text-cyan-400 font-mono font-bold mb-2">KEY POINTS</div>
              <ul className="list-disc list-inside text-sm text-gray-300 space-y-1">
                {result.key_points.map((point, idx) => (
                  <li key={idx}>{point}</li>
                ))}
              </ul>
            </div>
          )}

          {result.entities.length > 0 && (
            <div className="p-3 bg-black/40 border border-cyan-500/20 rounded">
              <div className="text-sm text-cyan-400 font-mono font-bold mb-2">ENTITIES</div>
              <div className="flex flex-wrap gap-2">
                {result.entities.map((entity, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-1 bg-cyan-500/10 border border-cyan-400/30 rounded text-xs text-cyan-300 font-mono"
                  >
                    {entity}
                  </span>
                ))}
              </div>
            </div>
          )}

          {result.sentiment && (
            <div className="p-3 bg-black/40 border border-cyan-500/20 rounded">
              <div className="text-sm text-cyan-400 font-mono font-bold mb-2">SENTIMENT</div>
              <div className="text-sm text-gray-300 capitalize">{result.sentiment}</div>
            </div>
          )}
        </div>
      )}

      {!result && !isAnalyzing && !error && (
        <div className="text-center py-8 text-gray-500 font-mono">
          Select a document to analyze
        </div>
      )}
    </div>
  )
}
