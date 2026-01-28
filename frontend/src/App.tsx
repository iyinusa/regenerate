
import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import { ThemeProvider } from './hooks/useTheme';
import Home from './pages/Home';
import Regen from './pages/Regen';
import Journey from './pages/Journey';


function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/regen" element={<Regen />} />
          <Route path="/journey" element={<Journey />} />
          <Route path="/journey/:guestId" element={<Journey />} />
          <Route path="/:username" element={<Journey />} />
        </Routes>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
