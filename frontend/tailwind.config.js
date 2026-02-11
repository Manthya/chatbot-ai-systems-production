/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './pages/**/*.{js,ts,jsx,tsx,mdx}',
        './components/**/*.{js,ts,jsx,tsx,mdx}',
        './app/**/*.{js,ts,jsx,tsx,mdx}',
    ],
    darkMode: 'class',
    theme: {
        extend: {
            colors: {
                primary: {
                    50: '#f0f9ff',
                    100: '#e0f2fe',
                    200: '#bae6fd',
                    300: '#7dd3fc',
                    400: '#38bdf8',
                    500: '#0ea5e9',
                    600: '#0284c7',
                    700: '#0369a1',
                    800: '#075985',
                    900: '#0c4a6e',
                },
                dark: {
                    bg: '#0f0f0f',
                    surface: '#1a1a1a',
                    border: '#2a2a2a',
                    text: '#e5e5e5',
                    muted: '#a3a3a3',
                }
            },
            animation: {
                'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'typing': 'typing 1s ease-in-out infinite',
            },
            keyframes: {
                typing: {
                    '0%, 100%': { opacity: 1 },
                    '50%': { opacity: 0.5 },
                }
            }
        },
    },
    plugins: [],
}
