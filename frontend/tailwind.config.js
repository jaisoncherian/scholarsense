/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#F8F8F8',
        card: '#FFFFFF',
        ink: '#1C1C1C',
        muted: '#606060',
        subtle: '#6B7280',
        line: '#EAEAEA',
        'line-strong': '#E5E7EB',
        mint: { DEFAULT: '#B9E8B9', soft: '#EAF7EA', tint: '#E3F6E3' },
        olive: { DEFAULT: '#A1A75D', soft: '#F3F4E6', dark: '#5D6220' },
        forest: { DEFAULT: '#2E5A44', dark: '#244735' },
        risk: {
          high: '#D95D5D', 'high-text': '#A83434', 'high-soft': '#FBEAEA',
          medium: '#DCA54C', 'medium-text': '#85591A', 'medium-soft': '#FBF1E1',
          low: '#529E72', 'low-text': '#2E5A44', 'low-soft': '#EAF7EA',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        display: ['"Plus Jakarta Sans"', 'Inter', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'sans-serif'],
      },
      borderRadius: { card: '1rem' },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.02), 0 4px 12px rgba(28,28,28,0.03)',
        pop: '0 4px 6px -1px rgba(0,0,0,0.04), 0 10px 24px -3px rgba(0,0,0,0.06)',
      },
    },
  },
  plugins: [],
};
