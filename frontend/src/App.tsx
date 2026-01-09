import { Routes, Route } from 'react-router-dom';
import Home from './pages/Home';
import Regen from './pages/Regen';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/regen" element={<Regen />} />
    </Routes>
  );
}

export default App;
