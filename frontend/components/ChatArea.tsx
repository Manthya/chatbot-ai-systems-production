import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { RefreshCw, Copy, ThumbsUp, ThumbsDown, Wrench } from 'lucide-react';

export interface Message {
    role: 'user' | 'assistant' | 'system' | 'tool';
    content: string;
    tool_calls?: any[];
    tool_call_id?: string;
}

interface ChatAreaProps {
    messages: Message[];
    isLoading?: boolean;
    statusMessage?: string;
}

export const ChatArea: React.FC<ChatAreaProps> = ({ messages, isLoading, statusMessage }) => {
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isLoading, statusMessage]);

    return (
        <div className="flex-1 overflow-y-auto p-4 md:p-8 space-y-8 relative bg-brand-void scroll-smooth">
            {messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
                    <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-accent to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
                        <span className="text-3xl font-bold text-white">V</span>
                    </div>
                    <div>
                        <h2 className="text-2xl font-bold text-white mb-2">How can I help you today?</h2>
                        <p className="text-brand-grey max-w-md">
                            I'm Voxa, an AI assistant capable of helping you with design, code, and creative tasks.
                        </p>
                    </div>
                </div>
            )}

            {messages.map((msg, idx) => {
                // Logic to hide content if it's purely a raw tool call or if real tool calls exist
                // We assume if tool_calls exist, the content (if any) is likely the raw JSON that initiated it, 
                // or we prioritize showing the "Using tool..." UI.
                const hasToolCalls = msg.tool_calls && msg.tool_calls.length > 0;
                // If message has tool calls, we hide the content if it looks like JSON or if we just want to be clean.
                // For now, let's auto-hide content if tool calls are present, as the "raw JSON" issue is the main complaint.
                const showContent = !hasToolCalls && msg.role !== 'tool';

                return (
                    <div
                        key={idx}
                        className={`flex items-start gap-4 max-w-4xl mx-auto ${msg.role === 'user' ? 'justify-end' : ''}`}
                    >
                        {/* Bot Avatar */}
                        {msg.role === 'assistant' && (
                            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-accent to-blue-600 flex-shrink-0 flex items-center justify-center text-xs font-bold text-white">
                                V
                            </div>
                        )}
                        {/* Tool Avatar */}
                        {msg.role === 'tool' && (
                            <div className="w-8 h-8 rounded-full bg-brand-surface border border-white/10 flex-shrink-0 flex items-center justify-center text-xs font-bold text-brand-grey">
                                <Wrench className="w-4 h-4" />
                            </div>
                        )}


                        {/* Content Bubble */}
                        <div className={`space-y-2 max-w-[85%]`}>
                            {showContent && (
                                <div className={`
                                    p-4 rounded-2xl text-[15px] leading-relaxed
                                    ${msg.role === 'user'
                                        ? 'bg-brand-surface text-white rounded-br-none border border-white/5'
                                        : 'bg-transparent text-gray-200 pl-0 pt-0'}
                                `}>
                                    <div className="prose prose-invert prose-sm max-w-none">
                                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                                    </div>
                                </div>
                            )}

                            {/* Tool Calls Status */}
                            {hasToolCalls && (
                                <div className="ml-0 bg-brand-surface rounded-lg p-3 border border-white/5 text-xs font-mono text-brand-grey space-y-2">
                                    {msg.tool_calls?.map((tool, tIdx) => (
                                        <div key={tIdx} className="flex items-center gap-2">
                                            <Wrench className="w-3 h-3 text-brand-accent" />
                                            <span className="text-brand-accent">Using {tool.function.name}...</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Tool Output (msg.role === 'tool') */}
                            {msg.role === 'tool' && (
                                <div className="ml-0 bg-brand-surface/50 rounded-lg p-3 border border-white/5 text-xs font-mono text-gray-400 overflow-x-auto">
                                    <div className="font-bold text-brand-grey mb-1">Result:</div>
                                    <pre className="whitespace-pre-wrap break-words max-h-40 overflow-y-auto">{msg.content}</pre>
                                </div>
                            )}

                            {/* Bot Actions */}
                            {msg.role === 'assistant' && !hasToolCalls && (
                                <div className="flex items-center gap-3 pl-0 pt-1">
                                    <button className="text-brand-grey hover:text-white transition-colors"><Copy className="w-4 h-4" /></button>
                                    <button className="text-brand-grey hover:text-white transition-colors"><RefreshCw className="w-4 h-4" /></button>
                                    <div className="flex-1"></div>
                                    <button className="text-brand-grey hover:text-white transition-colors"><ThumbsUp className="w-4 h-4" /></button>
                                    <button className="text-brand-grey hover:text-white transition-colors"><ThumbsDown className="w-4 h-4" /></button>
                                </div>
                            )}
                        </div>

                        {/* User Avatar */}
                        {msg.role === 'user' && (
                            <img
                                src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
                                alt="User"
                                className="w-8 h-8 rounded-full bg-brand-surface border border-white/10"
                            />
                        )}
                    </div>
                );
            })}

            {isLoading && (
                <div className="flex items-start gap-4 max-w-4xl mx-auto">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-brand-accent to-blue-600 flex-shrink-0 flex items-center justify-center text-xs font-bold text-white">
                        V
                    </div>
                    <div className="flex items-center gap-3 h-8">
                        <div className="flex items-center gap-1">
                            <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce"></div>
                            <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce delay-75"></div>
                            <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce delay-150"></div>
                        </div>
                        {statusMessage && (
                            <span className="text-sm text-brand-grey animate-pulse font-mono tracking-tight">
                                {statusMessage}
                            </span>
                        )}
                    </div>
                </div>
            )}

            <div ref={messagesEndRef} />
        </div>
    );
};
