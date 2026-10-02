import { useJarvisStore } from '../../store/useJarvisStore'

interface VoiceStatusIndicatorProps {
  className?: string
}

export function VoiceStatusIndicator({ className = '' }: VoiceStatusIndicatorProps) {
  const voiceState = useJarvisStore((state) => state.voiceStatus)
  const speechLanguage = useJarvisStore((state) => state.speechLanguage)
  const detectedLanguage = useJarvisStore((state) => state.detectedLanguage)
  const currentTranscript = useJarvisStore((state) => state.currentTranscript)
  const audioLevel = useJarvisStore((state) => state.audioLevel)

  const getStateColor = () => {
    switch (voiceState) {
      case 'speaking':
        return 'text-blue-400'
      case 'listening_wakeword':
      case 'listening_command':
        return 'text-green-400'
      case 'processing':
        return 'text-orange-400'
      case 'cooldown':
        return 'text-yellow-400'
      default:
        return 'text-gray-400'
    }
  }

  const getStateLabel = () => {
    switch (voiceState) {
      case 'idle':
        return 'IDLE'
      case 'listening_wakeword':
        return 'AWAITING WAKE WORD'
      case 'listening_command':
        return 'LISTENING'
      case 'processing':
        return 'PROCESSING'
      case 'speaking':
        return 'SPEAKING'
      case 'cooldown':
        return 'COOLDOWN'
      default:
        return 'UNKNOWN'
    }
  }

  const getLanguageLabel = () => {
    if (detectedLanguage) {
      const langMap: Record<string, string> = {
        'en': 'EN',
        'hi': 'HI',
        'mr': 'MR',
      }
      return langMap[detectedLanguage] || detectedLanguage.toUpperCase()
    }
    if (speechLanguage && speechLanguage !== 'auto') {
      const langMap: Record<string, string> = {
        'en-US': 'EN',
        'en-IN': 'EN',
        'hi-IN': 'HI',
        'mr-IN': 'MR',
      }
      return langMap[speechLanguage] || speechLanguage.split('-')[0].toUpperCase()
    }
    return 'AUTO'
  }

  return (
    <div className={`flex items-center gap-4 font-mono text-xs ${className}`}>
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          voiceState === 'idle' ? 'bg-gray-500' :
          voiceState === 'listening_wakeword' || voiceState === 'listening_command' ? 'bg-green-500 animate-pulse' :
          voiceState === 'processing' ? 'bg-orange-500 animate-pulse' :
          voiceState === 'speaking' ? 'bg-blue-500 animate-pulse' :
          'bg-yellow-500'
        }`} />
        <span className={getStateColor()}>{getStateLabel()}</span>
      </div>

      <div className="flex items-center gap-2 text-gray-400">
        <span>LANG:</span>
        <span className="text-cyan-400">{getLanguageLabel()}</span>
      </div>

      <div className="flex items-center gap-2 text-gray-400">
        <span>LEVEL:</span>
        <div className="w-16 h-2 bg-gray-700 rounded overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-green-500 to-blue-500 transition-all duration-100"
            style={{ width: `${audioLevel * 100}%` }}
          />
        </div>
      </div>

      {currentTranscript && (
        <div className="flex-1 text-gray-300 truncate max-w-xs">
          "{currentTranscript}"
        </div>
      )}
    </div>
  )
}
