import { useState } from 'react'

export function ImageGenerationPanel() {
  const [prompt, setPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const generate = async () => {
    if (!prompt.trim()) return

    setIsGenerating(true)
    setError(null)
    setImageUrl(null)

    try {
      const res = await fetch('/api/image/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      })

      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setImageUrl(data.image_url || data.url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="flex flex-col gap-4 p-6 bg-black/40 backdrop-blur-xl border border-cyan-500/20 rounded-lg">
      <h2 className="text-2xl font-bold text-cyan-400 font-mono">IMAGE GENERATION</h2>

      <div className="flex flex-col gap-2">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the image you want to generate..."
          rows={3}
          className="px-4 py-2 bg-black/60 border border-cyan-500/30 rounded text-white placeholder-gray-500 font-mono text-sm focus:outline-none focus:border-cyan-400 resize-none"
        />
        <button
          onClick={generate}
          disabled={isGenerating}
          className="px-6 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-400/50 rounded text-cyan-300 font-mono text-sm disabled:opacity-50 transition-all"
        >
          {isGenerating ? 'GENERATING...' : 'GENERATE IMAGE'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-400/30 rounded text-red-300 text-sm">
          Error: {error}
        </div>
      )}

      {imageUrl && (
        <div className="flex flex-col gap-2">
          <img
            src={imageUrl}
            alt="Generated"
            className="w-full rounded border border-cyan-500/30"
          />
          <a
            href={imageUrl}
            download="generated-image.png"
            className="px-4 py-2 bg-green-500/20 hover:bg-green-500/30 border border-green-400/50 rounded text-green-300 font-mono text-sm text-center transition-all"
          >
            DOWNLOAD IMAGE
          </a>
        </div>
      )}

      {!imageUrl && !isGenerating && !error && (
        <div className="text-center py-8 text-gray-500 font-mono">
          Enter a prompt to generate an image
        </div>
      )}
    </div>
  )
}
