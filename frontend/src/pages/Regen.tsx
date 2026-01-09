import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiClient } from '@/lib/api.ts';
import './Regen.css';

const Regen: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [url, setUrl] = useState('');
  const [jobId, setJobId] = useState('');
  const [processingStep, setProcessingStep] = useState(0);
  const steps = [
    'Fetching profile data...',
    'Analyzing professional journey...',
    'Structuring timeline...',
    'Generating insights...',
    'Creating documentary segments...',
    'Finalizing your reGen story...'
  ];

  useEffect(() => {
    const urlParam = searchParams.get('url') || '';
    const jobIdParam = searchParams.get('jobId') || '';
    
    setUrl(urlParam);
    setJobId(jobIdParam);
    
    if (jobIdParam) {
      // Poll the API for job status
      pollJobStatus(jobIdParam);
    } else {
      // Fallback: simulate processing steps
      simulateProcessing();
    }
  }, [searchParams]);

  async function pollJobStatus(jobId: string) {
    const maxAttempts = 60; // 5 minutes max
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await apiClient.getProfileStatus(jobId);
        
        // Update processing step based on status
        if (status.status === 'completed') {
          setProcessingStep(steps.length - 1);
          setTimeout(() => {
            navigate(`/journey?profileId=${status.profile_id}`);
          }, 2000);
          return;
        } else if (status.status === 'failed') {
          // Handle error
          console.error('Profile generation failed:', status.error);
          setTimeout(() => {
            navigate('/?error=' + encodeURIComponent(status.error || 'Generation failed'));
          }, 2000);
          return;
        } else if (status.status === 'processing') {
          // Update step based on progress
          setProcessingStep(Math.min(Math.floor(status.progress * steps.length), steps.length - 1));
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          // Timeout
          navigate('/?error=' + encodeURIComponent('Processing timeout. Please try again.'));
        }
      } catch (err) {
        console.error('Failed to get job status:', err);
        // Fall back to simulation
        simulateProcessing();
      }
    };

    poll();
  }

  function simulateProcessing() {
    // Fallback simulation
    const interval = setInterval(() => {
      setProcessingStep((prev) => {
        if (prev < steps.length - 1) {
          return prev + 1;
        } else {
          clearInterval(interval);
          setTimeout(() => {
            navigate('/journey');
          }, 2000);
          return prev;
        }
      });
    }, 2000);
  }

  return (
    <main className="processing-page">
      <div className="processing-container">
        <div className="processing-header">
          <h1 className="gradient-text">Regenerating Your Story...</h1>
          <p>Analyzing: <strong>{url}</strong></p>
          {jobId && (
            <p className="job-id">Job ID: <code>{jobId}</code></p>
          )}
        </div>

        <div className="processing-steps">
          {steps.map((step, index) => (
            <div 
              key={index}
              className={`step ${index === processingStep ? 'active' : ''} ${index < processingStep ? 'completed' : ''}`}
            >
              <div className="step-indicator">
                {index < processingStep ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                ) : index === processingStep ? (
                  <div className="loading-spinner"></div>
                ) : (
                  <span>{index + 1}</span>
                )}
              </div>
              <span className="step-text">{step}</span>
            </div>
          ))}
        </div>

        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${((processingStep + 1) / steps.length) * 100}%` }}></div>
        </div>

        <p className="processing-note">
          This may take a few minutes as we analyze your professional journey across multiple platforms.
        </p>
      </div>
    </main>
  );
};

export default Regen;
