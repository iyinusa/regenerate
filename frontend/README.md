# reGen Frontend (React)

Modern React frontend for reGen - AI-powered professional story generation.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Three.js** - 3D graphics and animations
- **GSAP** - Advanced animations
- **CSS3** - Styling

## Features

- ✨ Immersive 3D particle background with Three.js
- 🎨 Modern glassmorphism UI design
- 🚀 Smooth GSAP animations
- 📱 Fully responsive design
- ⚡ Fast development with Vite HMR
- 🔒 Type-safe with TypeScript
- 🎯 Client-side routing with React Router

## Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/       # Reusable React components
│   ├── Hero.tsx
│   └── ThreeBackground.tsx
├── pages/           # Page components
│   ├── Home.tsx
│   └── Regen.tsx
├── lib/             # Utilities and API client
│   └── api.ts
├── App.tsx          # Main app component with routing
├── main.tsx         # Application entry point
└── app.css          # Global styles
```

## Environment Variables

Create a `.env` file in the frontend directory:

```
VITE_API_URL=http://localhost:8000
```

## Docker Integration

This frontend is designed to work with the Docker setup. The frontend files are mounted as a volume in the Docker container, allowing for seamless integration with the FastAPI backend.

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier