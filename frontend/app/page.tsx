'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { MessageBubble } from '@/components/MessageBubble'
import { ChatInput } from '@/components/ChatInput'
import { Header } from '@/components/Header'

interface Message {
    id: string
    role: 'user' | 'assistant' | 'system' | 'tool'
    content: string
    tool_calls?: any[]
    tool_call_id?: string
    timestamp: Date
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export default function Home() {
    const [messages, setMessages] = useState<Message[]>([])
    const [isLoading, setIsLoading] = useState(false)
    const [conversationId, setConversationId] = useState<string | null>(null)
    const [streamingContent, setStreamingContent] = useState('')
    const [status, setStatus] = useState<string | null>(null)
    const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected')
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const wsRef = useRef<WebSocket | null>(null)
    const fullContentRef = useRef('')

    // Scroll to bottom on new messages
    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [])

    useEffect(() => {
        scrollToBottom()
    }, [messages, streamingContent, status, scrollToBottom])

    // WebSocket connection for streaming
    const connectWebSocket = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return

        setConnectionStatus('connecting')
        const ws = new WebSocket(`${WS_URL}/api/chat/stream`)

        ws.onopen = () => {
            setConnectionStatus('connected')
            console.log('WebSocket connected')
        }

        ws.onclose = () => {
            setConnectionStatus('disconnected')
            console.log('WebSocket disconnected')
            // Attempt to reconnect after 3 seconds
            setTimeout(() => {
                if (wsRef.current?.readyState !== WebSocket.OPEN) {
                    connectWebSocket()
                }
            }, 3000)
        }

        ws.onerror = (error) => {
            console.error('WebSocket error:', error)
            setConnectionStatus('disconnected')
        }

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)

            if (data.error) {
                console.error('Server error:', data.error)
                setIsLoading(false)
                setStatus(null)
                return
            }

            if (data.status) {
                setStatus(data.status)
            }

            if (data.content) {
                fullContentRef.current += data.content
                setStreamingContent(fullContentRef.current)
            }

            if (data.done) {
                // Finalize the message
                const finalContent = fullContentRef.current + (data.content || '')

                // Only add message if it has content or tool calls
                if (finalContent.trim() || (data.tool_calls && data.tool_calls.length > 0)) {
                    setMessages(prev => [
                        ...prev,
                        {
                            id: `msg-${Date.now()}`,
                            role: 'assistant',
                            content: finalContent,
                            tool_calls: data.tool_calls,
                            timestamp: new Date(),
                        }
                    ])
                }

                setStreamingContent('')
                fullContentRef.current = ''
                setStatus(null)
                setIsLoading(false)
                if (data.conversation_id) {
                    setConversationId(data.conversation_id)
                }
            }
        }

        wsRef.current = ws
    }, [])

    useEffect(() => {
        connectWebSocket()
        return () => {
            wsRef.current?.close()
        }
    }, [connectWebSocket])

    const sendMessage = async (content: string) => {
        if (!content.trim() || isLoading) return

        const userMessage: Message = {
            id: `msg-${Date.now()}`,
            role: 'user',
            content,
            timestamp: new Date(),
        }

        setMessages(prev => [...prev, userMessage])
        setIsLoading(true)
        setStreamingContent('')
        setStatus('Preparing...')

        // Format messages for API
        const apiMessages = [...messages, userMessage].map(m => ({
            role: m.role,
            content: m.content,
            tool_calls: m.tool_calls,
            tool_call_id: m.tool_call_id,
        }))

        // Send via WebSocket
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({
                messages: apiMessages,
                conversation_id: conversationId,
            }))
        } else {
            console.error('WebSocket not connected')
            setIsLoading(false)
            setStatus(null)
            setMessages(prev => [
                ...prev,
                {
                    id: `msg-${Date.now()}-error`,
                    role: 'assistant',
                    content: 'WebSocket not connected. Reconnecting...',
                    timestamp: new Date(),
                }
            ])
            connectWebSocket()
        }
    }

    const clearChat = () => {
        setMessages([])
        setConversationId(null)
        setStreamingContent('')
    }

    return (
        <main className="flex min-h-screen flex-col bg-dark-bg">
            <Header
                connectionStatus={connectionStatus}
                onClearChat={clearChat}
                messageCount={messages.length}
            />

            <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full">
                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
                    {messages.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full text-center px-4">
                            <div className="w-16 h-16 mb-6 rounded-full bg-gradient-to-br from-primary-500 to-purple-500 flex items-center justify-center">
                                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                                </svg>
                            </div>
                            <h2 className="text-2xl font-bold gradient-text mb-2">Welcome to AI Chat</h2>
                            <p className="text-dark-muted max-w-md">
                                Start a conversation with the AI assistant. Ask questions, get help with coding, or just chat!
                            </p>
                        </div>
                    )}

                    {messages.map((message) => (
                        <MessageBubble key={message.id} message={message} />
                    ))}

                    {/* Streaming message */}
                    {streamingContent && (
                        <MessageBubble
                            message={{
                                id: 'streaming',
                                role: 'assistant',
                                content: streamingContent,
                                timestamp: new Date(),
                            }}
                            isStreaming
                        />
                    )}

                    {/* Loading indicator */}
                    {(isLoading || status) && !streamingContent && (
                        <div className="flex items-start gap-3">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                                <span className="text-white text-sm font-medium">AI</span>
                            </div>
                            <div className="glass-card rounded-2xl p-4 flex flex-col gap-2">
                                {status && (
                                    <div className="text-xs text-primary-400 font-medium animate-pulse">
                                        {status}
                                    </div>
                                )}
                                <div className="typing-indicator">
                                    <span></span>
                                    <span></span>
                                    <span></span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <ChatInput onSend={sendMessage} isLoading={isLoading} />
            </div>
        </main>
    )
}
