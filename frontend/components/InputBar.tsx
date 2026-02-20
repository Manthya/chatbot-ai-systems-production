import React, { useState, useRef } from 'react';
import { Send, Paperclip, Mic, Image as ImageIcon, Smile, StopCircle } from 'lucide-react';

interface InputBarProps {
    onSend: (text: string) => void;
    onUpload: (file: File) => void;
    onVoiceToggle: () => void;
    isRecording: boolean;
    isLoading: boolean;
}

export const InputBar: React.FC<InputBarProps> = ({
    onSend,
    onUpload,
    onVoiceToggle,
    isRecording,
    isLoading
}) => {
    const [input, setInput] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim() && !isLoading) {
            onSend(input);
            setInput('');
        }
    };

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            onUpload(e.target.files[0]);
        }
    };

    return (
        <div className="p-6 w-full bg-brand-void/50 backdrop-blur-sm">
            <div className="max-w-3xl mx-auto">
                <form
                    onSubmit={handleSubmit}
                    className="relative flex items-center gap-2 bg-brand-surface border border-white/5 rounded-full p-2 px-4 shadow-2xl focus-within:border-brand-accent/50 focus-within:ring-1 focus-within:ring-brand-accent/20 transition-all duration-300"
                >
                    {/* Left Actions */}
                    <div className="flex items-center gap-1 border-r border-white/10 pr-2 mr-2">
                        <input
                            type="file"
                            ref={fileInputRef}
                            className="hidden"
                            onChange={handleFileChange}
                        />
                        <button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            className="p-2 text-brand-grey hover:text-white transition-colors rounded-full hover:bg-white/5"
                            disabled={isLoading}
                        >
                            <Paperclip className="w-4 h-4" />
                        </button>
                        <button
                            type="button"
                            className="p-2 text-brand-grey hover:text-white transition-colors rounded-full hover:bg-white/5"
                        >
                            <ImageIcon className="w-4 h-4" />
                        </button>
                    </div>

                    {/* Input */}
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Send a message..."
                        className="flex-1 bg-transparent border-none focus:ring-0 text-white placeholder-brand-grey/50 py-2 text-sm font-medium"
                        disabled={isLoading}
                    />

                    {/* Right Actions */}
                    <button
                        type="button"
                        onClick={onVoiceToggle}
                        className={`p-2 transition-colors rounded-full ${isRecording
                                ? 'text-red-500 bg-red-500/10'
                                : 'text-brand-grey hover:text-white hover:bg-white/5'
                            }`}
                        title={isRecording ? "Stop Recording" : "Start Voice"}
                        disabled={isLoading}
                    >
                        {isRecording ? <StopCircle className="w-4 h-4 fill-current" /> : <Mic className="w-4 h-4" />}
                    </button>

                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="ml-1 p-2 bg-brand-accent hover:bg-blue-500 text-white rounded-full transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed transform hover:scale-105 active:scale-95"
                    >
                        <Send className="w-4 h-4 ml-0.5" />
                    </button>
                </form>

                <div className="mt-3 text-center">
                    <p className="text-[10px] text-brand-grey/60">
                        Voxa AI can make mistakes. Consider checking important information.
                    </p>
                </div>
            </div>
        </div>
    );
};
