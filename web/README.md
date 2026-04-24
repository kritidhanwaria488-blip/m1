# MF FAQ Assistant - Next.js Frontend

Modern dark-themed React frontend for the Mutual Fund FAQ Assistant.

## Features

- **Dark Theme**: Sleek dark UI with gradient accents
- **Multi-Thread Chat**: Create, manage, and switch between conversation threads
- **Real-time Messaging**: Send messages and receive AI responses
- **Responsive Design**: Works on desktop and mobile
- **TypeScript**: Full type safety
- **Tailwind CSS**: Utility-first styling

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Heroicons
- **HTTP Client**: Axios
- **Utilities**: clsx, tailwind-merge, date-fns

## Getting Started

### Prerequisites

- Node.js 18+
- API server running on http://localhost:8000

### Installation

```bash
cd web
npm install
```

### Development

```bash
npm run dev
```

Open http://localhost:3000

### Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
web/
├── app/
│   ├── globals.css      # Global styles + Tailwind
│   ├── layout.tsx       # Root layout with metadata
│   └── page.tsx         # Main page (ChatInterface)
├── components/
│   ├── chat/
│   │   ├── chat-interface.tsx    # Main chat component
│   │   ├── message-bubble.tsx    # Individual message
│   │   ├── thread-sidebar.tsx    # Thread list sidebar
│   │   └── typing-indicator.tsx  # Typing animation
│   └── ui/
│       ├── button.tsx   # Reusable button component
│       └── input.tsx    # Reusable input component
├── lib/
│   ├── api.ts          # API client functions
│   └── utils.ts        # Utility functions
├── types/
│   └── index.ts        # TypeScript interfaces
├── tailwind.config.ts  # Tailwind configuration
├── next.config.js      # Next.js config (API proxy)
└── package.json        # Dependencies
```

## Components

### ChatInterface
Main chat interface with:
- Thread sidebar with create/delete
- Message list with auto-scroll
- Input area with send button
- Example question suggestions
- Error handling

### ThreadSidebar
Thread management sidebar:
- List all threads
- Active thread highlighting
- Create new thread button
- Delete thread with confirmation

### MessageBubble
Message display component:
- User messages (purple gradient)
- Assistant messages (dark card)
- Error indicators
- Refusal indicators
- Debug info toggle
- URL auto-linking

### TypingIndicator
Animated dots for "typing" state

## API Integration

The frontend connects to the FastAPI backend at http://localhost:8000.

Configured in `next.config.js`:
```javascript
async rewrites() {
  return [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8000/:path*',
    },
  ];
}
```

## Design System

### Colors
- Background: `#0f172a` (dark slate)
- Background Secondary: `#1e293b`
- Primary: `#6366f1` (indigo)
- Accent: `#8b5cf6` (purple)
- Success: `#10b981`
- Error: `#ef4444`

### Typography
- Font: Inter (sans-serif)
- Mono: JetBrains Mono

### Effects
- Glow: Box shadows with primary color
- Glass: Backdrop blur with transparency
- Gradient Text: Purple-to-pink gradient

## Edge Cases Handled

- Empty states (no threads, no messages)
- Loading states (typing indicator, disabled inputs)
- Error states (error banner, error messages)
- Network errors (retry handling)
- Long messages (auto-scroll, max-height textarea)
- Mobile responsive (hidden sidebar on mobile)

## Accessibility

- Keyboard navigation (Enter to send)
- Focus rings on interactive elements
- ARIA labels on buttons
- Color contrast compliance
- Screen reader friendly structure
