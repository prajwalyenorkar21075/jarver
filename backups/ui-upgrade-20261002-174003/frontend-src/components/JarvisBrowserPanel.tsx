import { useEffect, useRef, useState, useCallback } from 'react'
import gsap from 'gsap'
import { useJarvisStore } from '../store/useJarvisStore'

interface GoogleResult {
  title: string
  snippet: string
  url: string
  display_url?: string
}

interface KnowledgeCard {
  title: string
  description: string
  extract: string
  thumbnail?: string
}

interface YouTubeVideo {
  id: string
  title: string
  channel: string
  thumbnail: string
  url?: string
  views?: string
  duration?: string
}

const YOUTUBE_PRESETS: YouTubeVideo[] = [
  {
    id: 'Ke1Y3P9D0Bc',
    title: 'Marvel’s Iron Man 3 — Official Trailer',
    channel: 'Marvel UK',
    views: '88M views',
    duration: '02:32',
    thumbnail: 'https://img.youtube.com/vi/Ke1Y3P9D0Bc/hqdefault.jpg',
  },
  {
    id: '8hYlB38asDY',
    title: 'Marvel’s Iron Man — Official Trailer',
    channel: 'Marvel Entertainment',
    views: '45M views',
    duration: '02:30',
    thumbnail: 'https://img.youtube.com/vi/8hYlB38asDY/hqdefault.jpg',
  },
  {
    id: 'TcMBFSGVi1c',
    title: 'Avengers: Endgame — Official Trailer',
    channel: 'Marvel Studios',
    views: '150M views',
    duration: '02:26',
    thumbnail: 'https://img.youtube.com/vi/TcMBFSGVi1c/hqdefault.jpg',
  },
  {
    id: 'jfKfPfyJRdk',
    title: 'Lofi Hip Hop Radio — Beats to Relax/Study',
    channel: 'Lofi Girl',
    views: 'Live Stream',
    duration: 'LIVE',
    thumbnail: 'https://img.youtube.com/vi/jfKfPfyJRdk/hqdefault.jpg',
  },
  {
    id: '4xDzrJKXOOY',
    title: 'Synthwave Radio — Cyberpunk Chill',
    channel: 'Lofi Boy',
    views: '1.8M views',
    duration: 'LIVE',
    thumbnail: 'https://img.youtube.com/vi/4xDzrJKXOOY/hqdefault.jpg',
  },
]

const QUICK_LINKS = [
  { name: 'Google', target: 'https://www.google.com', color: '#4285f4', desc: 'Google Search & Intelligence' },
  { name: 'YouTube', target: 'https://www.youtube.com', color: '#ff0000', desc: 'Streaming Video & Audio' },
  { name: 'Wikipedia', target: 'https://www.wikipedia.org', color: '#00e5ff', desc: 'Neural Article Dossiers' },
  { name: 'GitHub', target: 'https://github.com', color: '#ffffff', desc: 'Code Repositories' },
  { name: 'ChatGPT', target: 'https://chatgpt.com', color: '#10a37f', desc: 'OpenAI Intelligence' },
  { name: 'Reddit', target: 'https://reddit.com', color: '#ff4500', desc: 'Community Discussions' },
  { name: 'Instagram', target: 'https://instagram.com', color: '#e1306c', desc: 'Meta Social Platform' },
  { name: 'X / Twitter', target: 'https://x.com', color: '#38bdf8', desc: 'Real-time Feeds' },
]

export default function JarvisBrowserPanel() {
  const panelRef = useRef<HTMLDivElement | null>(null)

  const panelOpen = useJarvisStore((s) => s.panelOpen)
  const panelPosition = useJarvisStore((s) => s.panelPosition)
  const panelContent = useJarvisStore((s) => s.panelContent)
  const setPanelPosition = useJarvisStore((s) => s.setPanelPosition)
  const closePanel = useJarvisStore((s) => s.closePanel)
  const togglePanelZoom = useJarvisStore((s) => s.togglePanelZoom)

  const [activeTab, setActiveTab] = useState<'google' | 'youtube' | 'web' | 'live' | 'quick'>('google')
  const [googleViewMode, setGoogleViewMode] = useState<'cards' | 'chromium'>('cards')

  // Search state
  const [urlInput, setUrlInput] = useState('https://www.google.com/search?q=Iron%20Man%20Jarvis%20AI')
  const [googleQuery, setGoogleQuery] = useState('Iron Man Jarvis AI')
  const [activeQuery, setActiveQuery] = useState('Iron Man Jarvis AI')
  const [googleResults, setGoogleResults] = useState<GoogleResult[]>([])
  const [knowledgeCard, setKnowledgeCard] = useState<KnowledgeCard | null>(null)
  const [aiBriefing, setAiBriefing] = useState<string>('')
  const [isSearchingGoogle, setIsSearchingGoogle] = useState(false)
  const searchReqIdRef = useRef(0)
  const resultsContainerRef = useRef<HTMLDivElement | null>(null)

  // YouTube state
  const [youtubeVideos, setYouTubeVideos] = useState<YouTubeVideo[]>(YOUTUBE_PRESETS)
  const [currentVideoId, setCurrentVideoId] = useState(panelContent.videoId || 'Ke1Y3P9D0Bc')
  const [youtubeSearchInput, setYoutubeSearchInput] = useState('Iron Man 3')
  const [isSearchingYoutube, setIsSearchingYoutube] = useState(false)

  // Live preview state
  const [livePreviewUrl, setLivePreviewUrl] = useState('https://www.google.com/search?q=Iron%20Man%20Jarvis%20AI')
  const [previewTimestamp, setPreviewTimestamp] = useState(Date.now())
  const [isLiveLoading, setIsLiveLoading] = useState(false)

  // Article state
  const [selectedArticle, setSelectedArticle] = useState<{ title: string; extract: string } | null>(null)

  // Helper to open links directly in a new browser tab and ping system launcher
  const openInNewTab = useCallback((targetUrl: string) => {
    let clean = targetUrl.trim()
    if (!clean) return
    if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
      if (clean.includes('.') && !clean.includes(' ')) {
        clean = `https://${clean}`
      } else {
        clean = `https://www.google.com/search?q=${encodeURIComponent(clean)}`
      }
    }
    try {
      window.open(clean, '_blank', 'noopener,noreferrer')
    } catch (e) {
      console.warn('Direct window.open blocked:', e)
    }
    try {
      fetch('/api/system/open', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: clean, type: 'url' }),
      })
    } catch {
      // Ignored
    }
  }, [])

  // Robust Search Engine with Sequence Lock & Immediate Scroll-To-Top
  const performGoogleSearch = useCallback(async (query: string) => {
    const cleanQ = query.trim()
    if (!cleanQ) return
    const thisReqId = ++searchReqIdRef.current
    setIsSearchingGoogle(true)
    setActiveQuery(cleanQ)
    setUrlInput(`https://www.google.com/search?q=${encodeURIComponent(cleanQ)}`)

    // Scroll results to top immediately so user sees new header & output
    if (resultsContainerRef.current) {
      resultsContainerRef.current.scrollTop = 0
    }

    try {
      const res = await fetch(`/api/google/search?q=${encodeURIComponent(cleanQ)}`)
      if (searchReqIdRef.current !== thisReqId) return // discard stale response

      if (res.ok) {
        const data = await res.json()
        setGoogleResults(data.results || [])
        setKnowledgeCard(data.knowledge_card || null)
        setAiBriefing(data.ai_briefing || '')
        setLivePreviewUrl(`https://www.google.com/search?q=${encodeURIComponent(cleanQ)}`)
        setPreviewTimestamp(Date.now())
      } else {
        // Fallback to direct Wikipedia API if backend search fails
        const url = `https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(
          cleanQ
        )}&utf8=&format=json&origin=*`
        const wikiRes = await fetch(url)
        const wikiData = await wikiRes.json()
        if (searchReqIdRef.current !== thisReqId) return
        const list = (wikiData?.query?.search || []).map((it: { title: string; snippet: string }) => ({
          title: it.title,
          snippet: it.snippet,
          url: `https://en.wikipedia.org/wiki/${encodeURIComponent(it.title.replace(/ /g, '_'))}`,
          display_url: `https://www.google.com/search?q=${encodeURIComponent(it.title)}`,
        }))
        setGoogleResults(list)
      }
    } catch (err) {
      console.error('Google search error:', err)
      if (searchReqIdRef.current === thisReqId) {
        setGoogleResults([])
      }
    } finally {
      if (searchReqIdRef.current === thisReqId) {
        setIsSearchingGoogle(false)
        requestAnimationFrame(() => {
          if (resultsContainerRef.current) {
            resultsContainerRef.current.scrollTop = 0
          }
        })
      }
    }
  }, [])

  // Execute initial search once on mount
  useEffect(() => {
    performGoogleSearch('Iron Man Jarvis AI')
  }, [performGoogleSearch])

  // Sync store content when voice or quick actions trigger
  useEffect(() => {
    if (panelContent.videoId) {
      setCurrentVideoId(panelContent.videoId)
      setActiveTab('youtube')
    } else if (panelContent.type === 'youtube') {
      setActiveTab('youtube')
    } else if (panelContent.query) {
      setGoogleQuery(panelContent.query)
      setActiveTab('google')
      performGoogleSearch(panelContent.query)
    }
  }, [panelContent, performGoogleSearch])

  // Real YouTube Search via Backend API
  const performYoutubeSearch = useCallback(async (query: string) => {
    if (!query.trim()) return
    setIsSearchingYoutube(true)
    try {
      const res = await fetch(`/api/youtube/search?q=${encodeURIComponent(query)}`)
      if (res.ok) {
        const data = await res.json()
        const list: YouTubeVideo[] = data.results || []
        if (list.length > 0) {
          setYouTubeVideos(list)
          setCurrentVideoId(list[0].id)
        }
      }
    } catch (err) {
      console.error('YouTube search error:', err)
    } finally {
      setIsSearchingYoutube(false)
    }
  }, [])

  // Fetch article details for Dossier view
  const fetchArticleDetails = async (title: string) => {
    try {
      const url = `https://en.wikipedia.org/api/rest_v1/page/summary/${encodeURIComponent(title)}`
      const res = await fetch(url)
      const data = await res.json()
      if (data?.extract) {
        setSelectedArticle({ title: data.title, extract: data.extract })
      }
    } catch (err) {
      console.error('Failed to load article:', err)
    }
  }

  // Handle URL navigation bar
  const handleNavigate = (targetUrl: string, openExternal = false) => {
    const clean = targetUrl.trim()
    if (!clean) return

    if (openExternal) {
      openInNewTab(clean)
      return
    }

    const lower = clean.toLowerCase()

    // 1. Google search URL format
    if (lower.includes('google.com/search?') || lower.includes('google.com/search')) {
      try {
        const full = clean.startsWith('http') ? clean : `https://${clean}`
        const urlObj = new URL(full)
        const q = urlObj.searchParams.get('q') || 'Iron Man Jarvis AI'
        const decodedQ = decodeURIComponent(q)
        setGoogleQuery(decodedQ)
        setUrlInput(full)
        setActiveTab('google')
        performGoogleSearch(decodedQ)
        return
      } catch {
        // Continue
      }
    }

    if (lower.startsWith('g:') || lower.startsWith('search:')) {
      const q = clean.replace(/^(g:|search:)/i, '').trim()
      setGoogleQuery(q)
      setUrlInput(`https://www.google.com/search?q=${encodeURIComponent(q)}`)
      setActiveTab('google')
      performGoogleSearch(q)
      return
    }

    if (lower.includes('youtube.com') || lower.includes('youtu.be') || lower.startsWith('yt:')) {
      setActiveTab('youtube')
      setUrlInput(clean.startsWith('http') ? clean : 'https://www.youtube.com')
      return
    }

    if (lower.includes('wikipedia.org')) {
      setActiveTab('web')
      setUrlInput(clean.startsWith('http') ? clean : 'https://www.wikipedia.org')
      return
    }

    // If user typed a search query with spaces and not a URL
    if (!clean.includes('.') || (clean.includes(' ') && !clean.startsWith('http'))) {
      setGoogleQuery(clean)
      setUrlInput(`https://www.google.com/search?q=${encodeURIComponent(clean)}`)
      setActiveTab('google')
      performGoogleSearch(clean)
      return
    }

    // Direct Web URL Preview via Chromium
    const validUrl = clean.startsWith('http://') || clean.startsWith('https://') ? clean : `https://${clean}`
    setLivePreviewUrl(validUrl)
    setUrlInput(validUrl)
    setActiveTab('live')
    setIsLiveLoading(true)
    setPreviewTimestamp(Date.now())
  }

  // GSAP Choreography Animation Engine (Clean aerodynamic modal, zero wings)
  useEffect(() => {
    const el = panelRef.current
    if (!el) return

    if (!panelOpen || panelPosition === 'closed') {
      gsap.to(el, {
        opacity: 0,
        scale: 0.9,
        duration: 0.3,
        ease: 'power3.in',
        pointerEvents: 'none',
      })
      return
    }

    const vw = window.innerWidth
    const vh = window.innerHeight

    let targetProps = {}

    switch (panelPosition) {
      case 'center':
        targetProps = {
          top: vh / 2,
          left: vw / 2,
          xPercent: -50,
          yPercent: -50,
          width: Math.min(vw * 0.88, 1080),
          height: Math.min(vh * 0.85, 680),
          scale: 1,
          opacity: 1,
          rotate: 0,
        }
        break

      case 'docked-tr':
        targetProps = {
          top: 70,
          left: vw - 36,
          xPercent: -100,
          yPercent: 0,
          width: Math.min(vw * 0.45, 580),
          height: Math.min(vh * 0.65, 500),
          scale: 1,
          opacity: 1,
          rotate: 0,
        }
        break

      case 'docked-tl':
        targetProps = {
          top: 70,
          left: 36,
          xPercent: 0,
          yPercent: 0,
          width: Math.min(vw * 0.45, 580),
          height: Math.min(vh * 0.65, 500),
          scale: 1,
          opacity: 1,
          rotate: 0,
        }
        break

      case 'docked-br':
        targetProps = {
          top: vh - 40,
          left: vw - 36,
          xPercent: -100,
          yPercent: -100,
          width: Math.min(vw * 0.42, 540),
          height: Math.min(vh * 0.6, 460),
          scale: 1,
          opacity: 1,
          rotate: 0,
        }
        break

      case 'minimized':
        targetProps = {
          top: 70,
          left: vw - 36,
          xPercent: -100,
          yPercent: 0,
          width: 360,
          height: 52,
          scale: 1,
          opacity: 1,
          rotate: 0,
        }
        break
    }

    gsap.to(el, {
      ...targetProps,
      duration: 0.5,
      ease: 'expo.out',
      pointerEvents: 'auto',
    })
  }, [panelOpen, panelPosition])

  if (!panelOpen && panelPosition === 'closed') return null

  const isCenter = panelPosition === 'center'
  const isMinimized = panelPosition === 'minimized'

  const cleanSnippet = (html: string) => {
    const doc = new DOMParser().parseFromString(html, 'text/html')
    return doc.body.textContent || ''
  }

  return (
    <div
      ref={panelRef}
      className="fixed z-40 flex flex-col rounded-xl border border-cyan-500/50 bg-[#040a18] text-white shadow-[0_0_35px_rgba(0,229,255,0.15)] overflow-hidden select-none"
    >
      {/* 1. COCKPIT HEADER BAR */}
      <div className="flex h-11 shrink-0 items-center justify-between border-b border-cyan-500/40 bg-[#060e22] px-3 font-mono text-xs text-white">
        {/* Left: Console Title & Engine Active Badge */}
        <div className="flex items-center gap-2">
          <div className="flex h-5 w-5 items-center justify-center rounded border border-[#00e5ff] bg-cyan-500/20 text-[#00e5ff]">
            <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2" />
            </svg>
          </div>
          <span className="font-extrabold tracking-widest text-[#00e5ff] text-xs">
            AERO HUD CONSOLE
          </span>
          <span className="hidden sm:inline-block rounded border border-cyan-500/30 bg-black/60 px-1.5 py-0.5 text-[9px] text-[#00e5ff]">
            CHROMIUM ENGINE ACTIVE
          </span>
        </div>

        {/* Center: Interactive Tabs */}
        {!isMinimized && (
          <div className="hidden md:flex items-center gap-1 rounded border border-cyan-500/30 bg-black/70 p-1 text-[11px]">
            {/* Google Search Tab (Active Blue as shown in user's image) */}
            <button
              type="button"
              onClick={() => setActiveTab('google')}
              className={`cursor-pointer flex items-center gap-1.5 rounded px-3 py-0.5 transition-all ${
                activeTab === 'google' ? 'bg-[#3b82f6] text-white font-bold shadow-md' : 'text-white/60 hover:text-white'
              }`}
            >
              <span>Google</span>
            </button>

            {/* YouTube Stream Tab */}
            <button
              type="button"
              onClick={() => setActiveTab('youtube')}
              className={`cursor-pointer flex items-center gap-1.5 rounded px-2.5 py-0.5 transition-colors ${
                activeTab === 'youtube' ? 'bg-[#ff0000] text-white font-bold shadow-md' : 'text-white/60 hover:text-white'
              }`}
            >
              <span>YouTube</span>
            </button>

            {/* Live Chromium Web View Tab */}
            <button
              type="button"
              onClick={() => setActiveTab('live')}
              className={`cursor-pointer flex items-center gap-1.5 rounded px-2.5 py-0.5 transition-colors ${
                activeTab === 'live' ? 'bg-emerald-500 text-black font-bold shadow-md' : 'text-white/60 hover:text-white'
              }`}
            >
              <span>Live Web</span>
            </button>

            {/* Web Intel Tab */}
            <button
              type="button"
              onClick={() => setActiveTab('web')}
              className={`cursor-pointer flex items-center gap-1.5 rounded px-2.5 py-0.5 transition-colors ${
                activeTab === 'web' ? 'bg-[#00e5ff] text-black font-bold shadow-md' : 'text-white/60 hover:text-white'
              }`}
            >
              <span>Dossiers</span>
            </button>

            {/* Quick Links Tab */}
            <button
              type="button"
              onClick={() => setActiveTab('quick')}
              className={`cursor-pointer flex items-center gap-1.5 rounded px-2.5 py-0.5 transition-colors ${
                activeTab === 'quick' ? 'bg-[#3b82f6] text-white font-bold shadow-md' : 'text-white/60 hover:text-white'
              }`}
            >
              <span>Quick Links</span>
            </button>
          </div>
        )}

        {/* Right: Window Controls */}
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded border border-cyan-500/30 bg-black/60 p-0.5">
            <button
              type="button"
              onClick={() => setPanelPosition('docked-tl')}
              className={`px-1.5 py-0.5 text-[10px] font-mono transition-colors rounded ${
                panelPosition === 'docked-tl' ? 'bg-[#00e5ff] text-black font-bold' : 'text-white/50 hover:text-white'
              }`}
              title="Dock Top-Left"
            >
              TL
            </button>
            <button
              type="button"
              onClick={() => setPanelPosition('docked-tr')}
              className={`px-1.5 py-0.5 text-[10px] font-mono transition-colors rounded ${
                panelPosition === 'docked-tr' ? 'bg-[#00e5ff] text-black font-bold' : 'text-white/50 hover:text-white'
              }`}
              title="Dock Top-Right"
            >
              TR
            </button>
            <button
              type="button"
              onClick={togglePanelZoom}
              className={`px-1.5 py-0.5 text-[10px] font-mono transition-colors rounded ${
                isCenter ? 'bg-[#00e5ff] text-black font-bold' : 'text-white/50 hover:text-white'
              }`}
              title="Expand Center"
            >
              CTR
            </button>
            <button
              type="button"
              onClick={() => setPanelPosition(isMinimized ? 'center' : 'minimized')}
              className="px-1.5 py-0.5 text-[10px] font-mono text-white/50 hover:text-white"
              title="Minimize"
            >
              _
            </button>
            <button
              type="button"
              onClick={closePanel}
              className="px-1.5 py-0.5 text-[10px] font-mono text-red-400 hover:bg-red-500 hover:text-white rounded"
              title="Close Panel"
            >
              ✕
            </button>
          </div>
        </div>
      </div>

      {/* 2. REAL URL NAVIGATION BAR */}
      {!isMinimized && (
        <div className="flex items-center gap-2 border-b border-cyan-500/25 bg-[#030712] px-3 py-2 font-mono text-xs">
          <div className="flex items-center gap-1 text-white/60">
            <button
              type="button"
              onClick={() => {
                setPreviewTimestamp(Date.now())
                handleNavigate(urlInput, false)
              }}
              className="cursor-pointer p-1 rounded hover:bg-white/10 hover:text-white"
              title="Reload"
            >
              ⟳
            </button>
          </div>

          {/* URL Input Box */}
          <div className="relative flex-1">
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleNavigate(urlInput, false)
              }}
              placeholder="Enter URL or search query..."
              className="w-full rounded border border-cyan-500/35 bg-[#040a18] px-3 py-1.5 font-mono text-xs text-white placeholder-white/30 focus:border-[#00e5ff] focus:outline-none"
            />
          </div>

          {/* SEARCH HUD BUTTON */}
          <button
            type="button"
            onClick={() => handleNavigate(urlInput, false)}
            className="cursor-pointer rounded bg-[#071530] border border-cyan-500/50 px-3 py-1.5 font-mono text-xs font-bold text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-colors"
            title="Search inside HUD Console"
          >
            NAVIGATE
          </button>

          {/* OPEN IN NEW TAB BUTTON (Prominent Solid Laser Cyan) */}
          <button
            type="button"
            onClick={() =>
              openInNewTab(
                activeTab === 'google'
                  ? `https://www.google.com/search?q=${encodeURIComponent(googleQuery)}`
                  : activeTab === 'youtube'
                  ? `https://www.youtube.com/watch?v=${currentVideoId}`
                  : activeTab === 'live'
                  ? livePreviewUrl
                  : urlInput
              )
            }
            className="cursor-pointer flex items-center gap-1 rounded bg-[#00e5ff] px-3 py-1.5 font-mono text-xs font-extrabold text-black hover:bg-cyan-300 transition-all shadow-[0_0_10px_rgba(0,229,255,0.3)] active:scale-95"
            title="Open directly in a new browser tab"
          >
            <span>Open in New Tab</span>
            <span>↗</span>
          </button>
        </div>
      )}

      {/* 3. MAIN CONTENT SURFACES */}
      {!isMinimized && (
        <div className="relative flex-1 flex flex-col bg-[#020612] overflow-hidden">
          {/* TAB 1: GOOGLE SEARCH & INTELLIGENCE DOSSIER */}
          {activeTab === 'google' && (
            <div className="flex-1 flex flex-col overflow-hidden bg-[#040a18] p-4 font-sans text-white">
              {/* Google Header Logo, Search Box & Mode Switcher */}
              <div className="flex flex-col items-center justify-center pb-3 border-b border-cyan-500/20 shrink-0">
                <div className="flex items-center justify-between w-full max-w-2xl mb-2.5">
                  <div className="text-2xl font-bold tracking-tight select-none flex items-center">
                    <span className="text-[#4285F4]">G</span>
                    <span className="text-[#EA4335]">o</span>
                    <span className="text-[#FBBC05]">o</span>
                    <span className="text-[#4285F4]">g</span>
                    <span className="text-[#34A853]">l</span>
                    <span className="text-[#EA4335]">e</span>
                    <span className="ml-2.5 font-mono text-[10px] text-[#00e5ff] border border-cyan-500/40 rounded px-1.5 py-0.5 bg-[#071530]">
                      INTELLIGENCE
                    </span>
                  </div>

                  {/* Mode Switcher: Intel Dossier vs Live Chromium View */}
                  <div className="flex items-center gap-1 rounded border border-cyan-500/40 bg-[#020612] p-0.5 font-mono text-[10px]">
                    <button
                      type="button"
                      onClick={() => setGoogleViewMode('cards')}
                      className={`cursor-pointer px-2.5 py-1 rounded transition-all ${
                        googleViewMode === 'cards' ? 'bg-[#3b82f6] text-white font-bold shadow-md' : 'text-white/60 hover:text-white'
                      }`}
                    >
                      INTEL DOSSIER
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setGoogleViewMode('chromium')
                        setLivePreviewUrl(`https://www.google.com/search?q=${encodeURIComponent(googleQuery)}`)
                        setPreviewTimestamp(Date.now())
                      }}
                      className={`cursor-pointer px-2.5 py-1 rounded transition-all ${
                        googleViewMode === 'chromium' ? 'bg-[#00e5ff] text-black font-extrabold shadow-md' : 'text-white/60 hover:text-white'
                      }`}
                    >
                      LIVE CHROMIUM VIEW
                    </button>
                  </div>
                </div>

                {/* Google Search Bar with Instant "Open in New Tab" option */}
                <div className="flex w-full max-w-2xl items-center rounded-full border border-cyan-500/50 bg-[#020612] px-3.5 py-1.5 text-sm shadow-[0_0_15px_rgba(0,229,255,0.12)]">
                  <svg className="h-4 w-4 text-[#00e5ff] mr-2 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                  <input
                    type="text"
                    value={googleQuery}
                    onChange={(e) => setGoogleQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') performGoogleSearch(googleQuery)
                    }}
                    placeholder="Search Google Intelligence..."
                    className="flex-1 bg-transparent text-white placeholder-white/40 focus:outline-none font-mono text-xs"
                  />
                  <div className="flex items-center gap-1.5 ml-2">
                    <button
                      type="button"
                      onClick={() => performGoogleSearch(googleQuery)}
                      className="cursor-pointer rounded-full bg-[#3b82f6] px-3.5 py-1 font-mono text-[11px] font-bold text-white hover:bg-blue-600 transition-colors shadow"
                      title="Search inside HUD"
                    >
                      Google Search
                    </button>
                    <button
                      type="button"
                      onClick={() => openInNewTab(`https://www.google.com/search?q=${encodeURIComponent(googleQuery)}`)}
                      className="cursor-pointer rounded-full bg-[#071530] border border-cyan-400/50 px-2.5 py-1 font-mono text-[11px] font-semibold text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-all"
                      title="Open Google in a new browser tab"
                    >
                      New Tab ↗
                    </button>
                  </div>
                </div>
              </div>

              {/* View 1: Live Headless Chromium Rendering */}
              {googleViewMode === 'chromium' && (
                <div className="relative flex-1 bg-black overflow-hidden flex flex-col items-center justify-center rounded-lg mt-2 border border-cyan-500/30">
                  <div className="absolute top-2 right-3 z-10 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setIsLiveLoading(true)
                        setPreviewTimestamp(Date.now())
                      }}
                      className="cursor-pointer rounded bg-[#071530] border border-cyan-400/40 px-2.5 py-1 font-mono text-[10px] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-colors"
                    >
                      Refresh Snapshot ⟳
                    </button>
                    <button
                      type="button"
                      onClick={() => openInNewTab(`https://www.google.com/search?q=${encodeURIComponent(googleQuery)}`)}
                      className="cursor-pointer rounded bg-[#00e5ff] px-2.5 py-1 font-mono text-[10px] font-bold text-black hover:bg-cyan-300 transition-colors"
                    >
                      Open in New Tab ↗
                    </button>
                  </div>

                  {isLiveLoading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 z-10 font-mono text-xs text-[#00e5ff] space-y-2">
                      <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#00e5ff] border-t-transparent" />
                      <span>Rendering live Chromium preview...</span>
                    </div>
                  )}

                  <img
                    key={`google-preview-${previewTimestamp}`}
                    src={`/api/browser/preview?url=${encodeURIComponent(`https://www.google.com/search?q=${encodeURIComponent(googleQuery)}`)}&t=${previewTimestamp}`}
                    alt="Google Live Preview"
                    onLoad={() => setIsLiveLoading(false)}
                    onError={() => setIsLiveLoading(false)}
                    className="h-full w-full object-contain"
                  />
                </div>
              )}

              {/* View 2: Structured Google Search Results & Knowledge Dossier */}
              {googleViewMode === 'cards' && (
                <div
                  ref={resultsContainerRef}
                  className="flex-1 overflow-y-auto pt-3 space-y-3 font-mono pr-1"
                >
                  {/* Active Search & Query Banner */}
                  <div className="flex items-center justify-between px-1 py-1 text-[11px] text-cyan-300/80 border-b border-cyan-500/20">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-[#00e5ff] animate-pulse" />
                      <span className="font-bold text-[#00e5ff] tracking-wider">
                        INTEL NODES RETRIEVED: {googleResults.length}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-white/50 truncate max-w-[240px]">QUERY: &quot;{activeQuery}&quot;</span>
                      <button
                        type="button"
                        onClick={() => openInNewTab(`https://www.google.com/search?q=${encodeURIComponent(activeQuery)}`)}
                        className="cursor-pointer text-[#00e5ff] hover:underline text-[10px] font-bold"
                      >
                        Open Search in New Tab ↗
                      </button>
                    </div>
                  </div>

                  {/* Active Searching HUD Banner */}
                  {isSearchingGoogle && (
                    <div className="rounded-xl border border-cyan-400 bg-[#071530] p-4 text-center text-[#00e5ff] text-xs font-mono animate-pulse shadow-[0_0_15px_rgba(0,229,255,0.2)]">
                      <div className="flex items-center justify-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-[#00e5ff] animate-ping" />
                        <span className="font-bold tracking-wider">
                          [ SCANNING QUANTUM REPOSITORY FOR: &quot;{activeQuery}&quot; ]
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] text-white/70">
                        Synthesizing executive briefing and indexing verified global satellite telemetry...
                      </p>
                    </div>
                  )}

                  {/* AI Executive Intelligence Briefing */}
                  {!isSearchingGoogle && aiBriefing && (
                    <div className="rounded-xl border border-cyan-400/80 bg-[#071530] p-4 text-white shadow-xl relative overflow-hidden">
                      <div className="absolute top-0 right-0 px-2.5 py-0.5 bg-cyan-500/20 border-b border-l border-cyan-400/40 text-[9px] font-mono text-[#00e5ff] font-bold uppercase tracking-wider">
                        // STARK NEURAL BRIEF
                      </div>
                      <div className="flex items-start gap-3">
                        <div className="h-8 w-8 rounded-lg bg-cyan-500/20 border border-[#00e5ff] flex items-center justify-center shrink-0 text-[#00e5ff] font-bold">
                          AI
                        </div>
                        <div className="flex-1">
                          <h4 className="font-mono text-xs font-bold text-[#00e5ff] tracking-wider">
                            STARK EXECUTIVE INTELLIGENCE SUMMARY:
                          </h4>
                          <p className="mt-1 text-sm text-white/95 leading-relaxed font-sans font-medium">
                            {aiBriefing}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Knowledge Summary Card */}
                  {!isSearchingGoogle && knowledgeCard && (
                    <div className="rounded-xl border border-cyan-400/60 bg-[#071530] p-4 text-white shadow-lg">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <span className="font-mono text-[9px] uppercase tracking-wider text-[#00e5ff] font-bold">
                            // SUBJECT INTELLIGENCE DOSSIER
                          </span>
                          <h3 className="text-base font-bold text-white mt-0.5">{knowledgeCard.title}</h3>
                          <p className="text-xs text-cyan-300 italic mt-0.5 font-sans">{knowledgeCard.description}</p>
                          <p className="text-xs text-slate-200 font-sans mt-2 leading-relaxed">
                            {knowledgeCard.extract}
                          </p>
                        </div>
                        {knowledgeCard.thumbnail && (
                          <img
                            src={knowledgeCard.thumbnail}
                            alt={knowledgeCard.title}
                            className="h-24 w-24 rounded-lg border border-cyan-500/40 object-cover shrink-0"
                          />
                        )}
                      </div>
                      <div className="mt-3 flex items-center justify-between border-t border-cyan-500/20 pt-2 text-[10px] text-[#00e5ff]">
                        <button
                          type="button"
                          onClick={() => {
                            fetchArticleDetails(knowledgeCard.title)
                            setActiveTab('web')
                          }}
                          className="hover:underline font-bold cursor-pointer"
                        >
                          View Full Dossier in HUD →
                        </button>
                        <button
                          type="button"
                          onClick={() => openInNewTab(`https://www.google.com/search?q=${encodeURIComponent(knowledgeCard.title)}`)}
                          className="hover:underline text-cyan-200 font-bold cursor-pointer"
                        >
                          Open in New Tab ↗
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Search Results Stream (Exact UI from user's image) */}
                  {!isSearchingGoogle && googleResults.length > 0 ? (
                    googleResults.map((r, i) => (
                      <div
                        key={i}
                        className="group rounded-xl border border-cyan-500/25 bg-[#071530] p-3.5 hover:border-[#00e5ff] hover:bg-[#0b2149] transition-all"
                      >
                        {/* URL Line & Open in New Tab Button */}
                        <div className="flex items-center justify-between text-[11px] text-[#00e5ff]">
                          <span className="truncate max-w-[80%] font-mono">{r.display_url || r.url}</span>
                          <button
                            type="button"
                            onClick={() => openInNewTab(r.url)}
                            className="cursor-pointer text-[11px] text-white/70 hover:text-[#00e5ff] hover:underline font-mono font-semibold"
                          >
                            Open in New Tab ↗
                          </button>
                        </div>

                        {/* Title (Clicking opens in new tab) */}
                        <h3
                          onClick={() => openInNewTab(r.url)}
                          className="cursor-pointer text-sm font-bold text-[#8ab4f8] hover:text-[#00e5ff] hover:underline mt-1"
                        >
                          {r.title}
                        </h3>

                        {/* Snippet */}
                        <p className="text-xs text-[#cbd5e1] mt-1 font-sans leading-relaxed line-clamp-2">
                          {cleanSnippet(r.snippet)}
                        </p>

                        {/* Bottom action row with verified source */}
                        <div className="mt-2.5 flex items-center justify-between text-[10px] text-[#00e5ff]">
                          <button
                            type="button"
                            onClick={() => {
                              fetchArticleDetails(r.title)
                              setActiveTab('web')
                            }}
                            className="cursor-pointer hover:underline font-semibold"
                          >
                            Click to view dossier in HUD →
                          </button>
                          <span className="text-[#64748b] font-mono tracking-wider font-semibold">
                            VERIFIED SOURCE
                          </span>
                        </div>
                      </div>
                    ))
                  ) : !isSearchingGoogle ? (
                    <div className="flex flex-col items-center justify-center py-12 text-white/40 text-xs font-mono">
                      <span>No results found. Type a query above to search.</span>
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: FUNCTIONAL YOUTUBE VIDEO STREAM PREVIEW */}
          {activeTab === 'youtube' && (
            <div className="flex-1 flex flex-col h-full w-full bg-black overflow-hidden">
              {/* YouTube Search Bar */}
              <div className="flex shrink-0 items-center justify-between border-b border-cyan-500/30 bg-[#071530] px-3 py-2 text-xs font-mono">
                <div className="flex items-center gap-2">
                  <span className="rounded bg-[#ff0000] px-2 py-0.5 font-bold text-white text-[10px]">
                    YOUTUBE
                  </span>
                  <span className="text-white/80 text-[11px] font-semibold truncate max-w-[220px]">
                    ID: {currentVideoId}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={youtubeSearchInput}
                    onChange={(e) => setYoutubeSearchInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') performYoutubeSearch(youtubeSearchInput)
                    }}
                    placeholder="Search YouTube videos..."
                    className="rounded border border-cyan-500/40 bg-[#040a18] px-2.5 py-1 text-[11px] font-mono text-white placeholder-white/30 focus:border-[#00e5ff] focus:outline-none w-[180px]"
                  />
                  <button
                    type="button"
                    onClick={() => performYoutubeSearch(youtubeSearchInput)}
                    disabled={isSearchingYoutube}
                    className="cursor-pointer rounded bg-[#ff0000] px-2.5 py-1 font-mono text-[10px] font-bold text-white hover:bg-red-600 transition-colors disabled:opacity-50"
                  >
                    {isSearchingYoutube ? 'Searching...' : 'Search'}
                  </button>
                  <button
                    type="button"
                    onClick={() => openInNewTab(`https://www.youtube.com/watch?v=${currentVideoId}`)}
                    className="cursor-pointer rounded bg-[#00e5ff] px-2.5 py-1 font-mono text-[10px] font-bold text-black hover:bg-cyan-300 transition-colors"
                    title="Watch in YouTube in new tab"
                  >
                    Watch in New Tab ↗
                  </button>
                </div>
              </div>

              {/* Working Embedded Video Player */}
              <div className="relative flex-1 bg-black flex flex-col">
                <div className="relative flex-1">
                  <iframe
                    key={currentVideoId}
                    src={`https://www.youtube.com/embed/${currentVideoId}?autoplay=1${
                      panelContent.autoplaySound ? '' : '&mute=1'
                    }&playsinline=1&enablejsapi=1`}
                    title="YouTube Preview Stream"
                    className="h-full w-full border-0"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                    referrerPolicy="strict-origin-when-cross-origin"
                    allowFullScreen
                  />
                </div>
                {/* Audio Status Strip */}
                <div className="flex items-center justify-between px-3 py-1 bg-[#040a18] text-[10px] font-mono text-[#00e5ff] border-t border-cyan-500/20">
                  <span>AUDIO STATUS: Muted by default for browser security. Unmute in player or open in tab 🔊</span>
                  <button
                    type="button"
                    onClick={() => openInNewTab(`https://www.youtube.com/watch?v=${currentVideoId}`)}
                    className="cursor-pointer text-[#00e5ff] hover:underline font-bold"
                  >
                    Full Screen in New Tab ↗
                  </button>
                </div>
              </div>

              {/* Playable Video Carousel Cards Below */}
              <div className="flex shrink-0 items-center gap-2.5 border-t border-cyan-500/30 bg-[#071530] p-2 overflow-x-auto scrollbar-none font-mono">
                <span className="text-[10px] font-bold text-[#00e5ff] shrink-0">SELECT VIDEO:</span>
                {youtubeVideos.map((v) => (
                  <button
                    key={v.id}
                    type="button"
                    onClick={() => {
                      setCurrentVideoId(v.id)
                    }}
                    className={`cursor-pointer flex items-center gap-2 rounded-lg border p-1 text-left transition-all shrink-0 w-[220px] ${
                      currentVideoId === v.id
                        ? 'border-[#00e5ff] bg-cyan-500/20 text-white'
                        : 'border-white/10 bg-[#040a18] text-white/60 hover:text-white hover:border-cyan-500/40'
                    }`}
                  >
                    <img
                      src={v.thumbnail}
                      alt={v.title}
                      className="h-10 w-16 rounded object-cover border border-cyan-500/30 shrink-0"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] font-bold text-[#00e5ff] truncate">{v.title}</div>
                      <div className="text-[9px] text-white/40 truncate">{v.channel}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: LIVE CHROMIUM WEB VIEW */}
          {activeTab === 'live' && (
            <div className="flex-1 flex flex-col h-full w-full bg-black overflow-hidden font-mono">
              <div className="flex shrink-0 items-center justify-between border-b border-cyan-500/30 bg-[#071530] px-3 py-1.5 text-xs">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-bold text-emerald-400 text-[11px]">
                    CHROMIUM HEADLESS ENGINE
                  </span>
                  <span className="text-white/60 text-[10px] truncate max-w-[280px]">
                    {livePreviewUrl}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setIsLiveLoading(true)
                      setPreviewTimestamp(Date.now())
                    }}
                    className="cursor-pointer rounded bg-cyan-500/20 border border-cyan-400/40 px-2.5 py-1 text-[10px] text-[#00e5ff] hover:bg-[#00e5ff] hover:text-black transition-colors"
                  >
                    Refresh Snapshot ⟳
                  </button>
                  <button
                    type="button"
                    onClick={() => openInNewTab(livePreviewUrl)}
                    className="cursor-pointer rounded bg-[#00e5ff] px-2.5 py-1 text-[10px] font-bold text-black hover:bg-cyan-300 transition-colors"
                  >
                    Open in New Tab ↗
                  </button>
                </div>
              </div>

              <div className="relative flex-1 bg-black flex items-center justify-center overflow-hidden">
                {isLiveLoading && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 z-10 font-mono text-xs text-[#00e5ff] space-y-2">
                    <div className="h-6 w-6 animate-spin rounded-full border-2 border-[#00e5ff] border-t-transparent" />
                    <span>Rendering live Chromium webpage snapshot...</span>
                  </div>
                )}
                <img
                  key={`live-preview-${previewTimestamp}`}
                  src={`/api/browser/preview?url=${encodeURIComponent(livePreviewUrl)}&t=${previewTimestamp}`}
                  alt="Live Chromium Web Snapshot"
                  onLoad={() => setIsLiveLoading(false)}
                  onError={() => setIsLiveLoading(false)}
                  className="h-full w-full object-contain"
                />
              </div>
            </div>
          )}

          {/* TAB 4: WEB INTEL ARTICLE DOSSIER */}
          {activeTab === 'web' && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3 font-mono">
              {selectedArticle ? (
                <div className="rounded-xl border border-[#00e5ff]/50 bg-[#071530] p-4 text-white">
                  <div className="flex items-center justify-between border-b border-cyan-500/30 pb-2">
                    <h3 className="font-mono text-sm font-bold text-[#00e5ff]">
                      {selectedArticle.title}
                    </h3>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => openInNewTab(`https://en.wikipedia.org/wiki/${encodeURIComponent(selectedArticle.title)}`)}
                        className="cursor-pointer text-[10px] text-[#00e5ff] hover:underline font-bold"
                      >
                        Open in New Tab ↗
                      </button>
                      <button
                        type="button"
                        onClick={() => setSelectedArticle(null)}
                        className="cursor-pointer text-xs text-white/50 hover:text-white"
                      >
                        ✕ Close
                      </button>
                    </div>
                  </div>
                  <p className="mt-2.5 text-xs text-slate-200 leading-relaxed font-sans">
                    {selectedArticle.extract}
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-xs font-bold text-[#00e5ff]">
                    // NEURAL KNOWLEDGE DOSSIERS:
                  </div>
                  {googleResults.map((res, idx) => (
                    <div
                      key={idx}
                      onClick={() => fetchArticleDetails(res.title)}
                      className="group cursor-pointer rounded-xl border border-cyan-500/20 bg-[#071530] p-3 hover:border-[#00e5ff] hover:bg-[#0b2149] transition-all"
                    >
                      <h4 className="font-mono text-xs font-bold text-white group-hover:text-[#00e5ff]">
                        {res.title}
                      </h4>
                      <p className="mt-1 text-xs text-slate-300 leading-relaxed font-sans line-clamp-2">
                        {cleanSnippet(res.snippet)}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 5: QUICK LINKS MATRIX (Instant New Tab Launchers) */}
          {activeTab === 'quick' && (
            <div className="flex-1 overflow-y-auto p-4 font-mono">
              <div className="mb-3 text-xs font-bold tracking-wider text-[#00e5ff]">
                // SATELLITE QUICK LAUNCH MATRIX:
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {QUICK_LINKS.map((link) => (
                  <div
                    key={link.name}
                    className="flex flex-col justify-between rounded-xl border border-cyan-500/30 bg-[#071530] p-3 hover:border-[#00e5ff] hover:bg-[#0b2149] transition-all"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-white">{link.name}</span>
                        <span className="h-2 w-2 rounded-full" style={{ backgroundColor: link.color }} />
                      </div>
                      <div className="mt-1 text-[10px] text-white/50">{link.desc}</div>
                    </div>

                    <div className="mt-3 flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={() => openInNewTab(link.target)}
                        className="cursor-pointer flex-1 rounded bg-[#00e5ff] py-1 text-[10px] font-extrabold text-black hover:bg-cyan-300 transition-colors text-center"
                      >
                        Open in New Tab ↗
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
