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
                brand: {
                    void: '#040404',   // Main Background
                    surface: '#171717', // Cards / Sidebar
                    accent: '#2d8cff',  // Electric Blue
                    lighter: '#6ec0ff', // Light Blue
                    white: '#ffffff',
                    grey: '#888888',
                },
                // Mappings
                primary: {
                    DEFAULT: '#2d8cff',
                    foreground: '#ffffff',
                },
                secondary: {
                    DEFAULT: '#171717',
                    foreground: '#ffffff',
                },
                accent: {
                    DEFAULT: '#6ec0ff',
                    foreground: '#000000',
                },
                sidebar: {
                    bg: '#171717',
                    fg: '#ffffff',
                    border: '#333333',
                    active: '#2d8cff',
                }
            },
            fontFamily: {
                sans: ['"Space Grotesk"', 'sans-serif'],
                mono: ['monospace'],
            },
            boxShadow: {
                'soft': '0 10px 30px -10px rgba(0, 0, 0, 0.5)',
                'glow': '0 0 20px rgba(45, 140, 255, 0.3)',
                'sharp': 'none',
            },
        },
    },
    plugins: [
        require('@tailwindcss/typography'), // Ensure typography plugin is used if installed, otherwise remove
    ],
}
