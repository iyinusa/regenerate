import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Regen from './pages/Regen';
import Journey from './pages/Journey';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/regen" element={<Regen />} />
      <Route path="/journey" element={<Journey />} />
      <Route path="/journey/:guestId" element={<Journey />} />
    </Routes>
  );
}

export default App;
