'use client'

import { useState, useRef, FormEvent, KeyboardEvent } from 'react'

interface ChatInputProps {
    onSend: (message: string) => void
    isLoading: boolean
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
    const [input, setInput] = useState('')
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault()
        if (input.trim() && !isLoading) {
            onSend(input.trim())
            setInput('')
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto'
            }
        }
    }

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit(e as any)
        }
    }

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setInput(e.target.value)
        // Auto-resize textarea
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
        }
    }

    return (
        <div className="border-t border-dark-border bg-dark-bg/80 backdrop-blur-lg px-4 py-4">
            <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
                <div className="relative flex items-end gap-3">
                    <div className="flex-1 relative">
                        <textarea
                            ref={textareaRef}
                            value={input}
                            onChange={handleInputChange}
                            onKeyDown={handleKeyDown}
                            placeholder="Type your message... (Press Enter to send, Shift+Enter for new line)"
                            disabled={isLoading}
                            rows={1}
                            className="w-full resize-none rounded-xl border border-dark-border bg-dark-surface 
                         px-4 py-3 pr-12 text-dark-text placeholder-dark-muted
                         focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500
                         disabled:opacity-50 disabled:cursor-not-allowed
                         transition-all duration-200"
                            style={{ minHeight: '48px', maxHeight: '200px' }}
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="flex-shrink-0 w-12 h-12 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600
                       flex items-center justify-center
                       hover:from-primary-600 hover:to-primary-700 
                       disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200 transform hover:scale-105 active:scale-95"
                    >
                        {isLoading ? (
                            <svg className="w-5 h-5 text-white animate-spin" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                            </svg>
                        ) : (
                            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        )}
                    </button>
                </div>

                <p className="text-xs text-dark-muted text-center mt-2">
                    Powered by Open Source AI • Messages are processed locally
                </p>
            </form>
        </div>
    )
}
