/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
      },
      fontFamily: {
        sans: ["var(--font-pretendard)"],
        pretendard: ['Pretendard', 'sans-serif'], // Pretendard 폰트 추가
      },
      fontWeight: {
        'medium': '500',
        'bold': '700',
      }
    },
  },
  plugins: [],
};
