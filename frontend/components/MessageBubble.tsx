'use client'

import ReactMarkdown from 'react-markdown'

interface Message {
    id: string
    role: 'user' | 'assistant' | 'system' | 'tool'
    content: string
    tool_calls?: any[]
    tool_call_id?: string
    timestamp: Date
}

interface MessageBubbleProps {
    message: Message
    isStreaming?: boolean
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
    // Don't render empty messages unless streaming or having tool calls
    if (!message.content?.trim() && (!message.tool_calls || message.tool_calls.length === 0) && !isStreaming) {
        return null
    }

    const isUser = message.role === 'user'

    return (
        <div className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser
                ? 'bg-gradient-to-br from-emerald-500 to-teal-500'
                : 'bg-gradient-to-br from-primary-500 to-purple-500'
                }`}>
                <span className="text-white text-sm font-medium">
                    {isUser ? 'U' : 'AI'}
                </span>
            </div>

            {/* Message bubble */}
            <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
                <div className={`rounded-2xl px-4 py-3 ${isUser
                    ? 'bg-gradient-to-r from-primary-600 to-primary-500 text-white'
                    : 'glass-card text-dark-text'
                    }`}>
                    {isUser ? (
                        <p className="whitespace-pre-wrap break-words">{message.content}</p>
                    ) : (
                        <div className="prose prose-invert prose-sm max-w-none">
                            <ReactMarkdown
                                components={{
                                    code: ({ className, children, ...props }) => {
                                        const match = /language-(\w+)/.exec(className || '')
                                        const isInline = !match
                                        return isInline ? (
                                            <code className="bg-dark-surface px-1.5 py-0.5 rounded text-primary-400" {...props}>
                                                {children}
                                            </code>
                                        ) : (
                                            <code className={className} {...props}>
                                                {children}
                                            </code>
                                        )
                                    },
                                    pre: ({ children }) => (
                                        <pre className="bg-dark-surface rounded-lg p-4 overflow-x-auto my-2">
                                            {children}
                                        </pre>
                                    ),
                                    p: ({ children }) => (
                                        <p className="mb-2 last:mb-0">{children}</p>
                                    ),
                                    ul: ({ children }) => (
                                        <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>
                                    ),
                                    ol: ({ children }) => (
                                        <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>
                                    ),
                                }}
                            >
                                {message.content}
                            </ReactMarkdown>
                        </div>
                    )}

                    {/* Streaming cursor */}
                    {isStreaming && (
                        <span className="inline-block w-2 h-4 bg-primary-400 ml-1 animate-pulse" />
                    )}
                </div>

                {/* Timestamp */}
                <div className={`text-xs text-dark-muted mt-1 ${isUser ? 'text-right' : ''}`}>
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </div>
            </div>
        </div>
    )
}
