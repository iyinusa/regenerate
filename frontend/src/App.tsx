import { Routes, Route } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import Home from './pages/Home';
import Regen from './pages/Regen';
import Journey from './pages/Journey';

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/regen" element={<Regen />} />
        <Route path="/journey" element={<Journey />} />
        <Route path="/journey/:guestId" element={<Journey />} />
        <Route path="/:username" element={<Journey />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
