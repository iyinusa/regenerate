import { useNavigate } from 'react-router-dom';
import ThreeBackground from '@/components/ThreeBackground';
import Hero from '@/components/Hero';
import './Home.css';

const Home: React.FC = () => {
  const navigate = useNavigate();

  function handleGenerate(data: { url?: string; jobId?: string; status?: string }) {
    console.log('Starting profile generation:', data);
    
    if (data.jobId) {
      // Navigate to the processing page with job ID
      navigate(`/regen?jobId=${data.jobId}&url=${encodeURIComponent(data.url || '')}`);
    } else {
      // Fallback for old format (if API doesn't return jobId yet)
      navigate(`/regen?url=${encodeURIComponent(data.url || data as any)}`);
    }
  }

  return (
    <main className="app">
      <ThreeBackground />
      <div className="scroll-container">
        <Hero onGenerate={handleGenerate} />
      </div>
    </main>
  );
};

export default Home;
