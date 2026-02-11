'use client'

interface HeaderProps {
    connectionStatus: 'connected' | 'disconnected' | 'connecting'
    onClearChat: () => void
    messageCount: number
}

export function Header({ connectionStatus, onClearChat, messageCount }: HeaderProps) {
    const statusColors = {
        connected: 'bg-emerald-500',
        disconnected: 'bg-red-500',
        connecting: 'bg-yellow-500 animate-pulse',
    }

    const statusText = {
        connected: 'Connected',
        disconnected: 'Disconnected',
        connecting: 'Connecting...',
    }

    return (
        <header className="border-b border-dark-border bg-dark-bg/80 backdrop-blur-lg sticky top-0 z-50">
            <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
                {/* Logo and title */}
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-purple-500 flex items-center justify-center shadow-lg shadow-primary-500/20">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                    </div>
                    <div>
                        <h1 className="font-bold text-lg text-dark-text">AI Chat</h1>
                        <div className="flex items-center gap-2 text-xs">
                            <span className={`w-2 h-2 rounded-full ${statusColors[connectionStatus]}`} />
                            <span className="text-dark-muted">{statusText[connectionStatus]}</span>
                        </div>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-3">
                    {messageCount > 0 && (
                        <span className="text-sm text-dark-muted">
                            {messageCount} message{messageCount !== 1 ? 's' : ''}
                        </span>
                    )}

                    <button
                        onClick={onClearChat}
                        disabled={messageCount === 0}
                        className="px-4 py-2 rounded-lg text-sm font-medium
                       bg-dark-surface border border-dark-border text-dark-text
                       hover:bg-dark-border hover:border-dark-muted
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200"
                    >
                        New Chat
                    </button>
                </div>
            </div>
        </header>
    )
}
