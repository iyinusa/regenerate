import { useEffect, useState, useRef, useCallback, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { apiClient } from '@/lib/api.ts';
import GlobeBackground from '../components/GlobeBackground';
import './Regen.css';

// Task status types
type TaskStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'skipped';

interface Task {
  task_id: string;
  task_type: string;
  name: string;
  description: string;
  order: number;
  status: TaskStatus;
  progress: number;
  message: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
  estimated_seconds: number;
  critical: boolean;
}

interface WebSocketMessage {
  event: string;
  job_id: string;
  timestamp: string;
  task?: Task;
  plan?: {
    status: string;
    progress: number;
    tasks: Task[];
  };
  plan_progress?: number;
  data?: any;
}

const Regen: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const [url, setUrl] = useState('');
  const [, setJobId] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [overallProgress, setOverallProgress] = useState(0);
  const [, setStatusMessage] = useState('Initializing...');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Track active task for display
  const activeTask = useMemo(() => {
     return tasks.find(t => t.task_id === currentTaskId) || 
            tasks.find(t => t.status === 'running') || 
            tasks.find(t => t.status === 'pending') || 
            tasks[tasks.length - 1]; // Fallback to last if all completed
  }, [tasks, currentTaskId]);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pollTimeoutRef = useRef<number | null>(null);

  // Default task structure (shown before WebSocket updates)
  const defaultTasks: Task[] = [
    {
      task_id: 'task_001',
      task_type: 'fetch_profile',
      name: 'Extracting Profile Data',
      description: 'AI fetch and analyse profile data',
      order: 1,
      status: 'pending',
      progress: 0,
      message: '',
      estimated_seconds: 45,
      critical: true,
    },
    {
      task_id: 'task_002',
      task_type: 'enrich_profile',
      name: 'Enriching Profile',
      description: 'Discovering and aggregating data from related sources',
      order: 2,
      status: 'pending',
      progress: 0,
      message: '',
      estimated_seconds: 30,
      critical: false,
    },
    {
      task_id: 'task_003',
      task_type: 'aggregate_history',
      name: 'Aggregating History',
      description: 'Merging with existing profile history',
      order: 3,
      status: 'pending',
      progress: 0,
      message: '',
      estimated_seconds: 15,
      critical: false,
    },
    {
      task_id: 'task_004',
      task_type: 'structure_journey',
      name: 'Structuring Journey',
      description: 'Transforming profile into narrative structure',
      order: 4,
      status: 'pending',
      progress: 0,
      message: '',
      estimated_seconds: 35,
      critical: true,
    },
    {
      task_id: 'task_005',
      task_type: 'generate_timeline',
      name: 'Generating Timeline',
      description: 'Creating interactive timeline visualisation',
      order: 5,
      status: 'pending',
      progress: 0,
      message: '',
      estimated_seconds: 20,
      critical: true,
    },
    {
      task_id: 'task_006',
      task_type: 'generate_documentary',
      name: 'Creating Documentary',
      description: 'Crafting documentary narrative and video segments',
      order: 6,
      status: 'pending',
      progress: 0,
      message: '',
      estimated_seconds: 40,
      critical: true,
    },
  ];

  // Connect to WebSocket for real-time updates
  const connectWebSocket = useCallback((jobId: string) => {
    // Use the apiClient's WebSocket URL helper for consistent URL construction
    const wsUrl = apiClient.getWebSocketUrl(jobId);
    console.log('Connecting to WebSocket:', wsUrl);
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected successfully');
        setIsConnected(true);
        setStatusMessage('Connected to task stream...');
        setError(null); // Clear any previous errors
        
        // Send a ping to verify connection
        ws.send('ping');
      };

      ws.onmessage = (event) => {
        try {
          // Handle pong responses
          if (event.data === 'pong') {
            console.log('WebSocket ping-pong successful');
            return;
          }
          
          const message: WebSocketMessage = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e, 'Raw data:', event.data);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setIsConnected(false);
        
        // Handle specific close codes
        if (event.code === 4004) {
          // Job not found
          setError('Job session not found. This may be due to a server restart. Please try generating again.');
          return;
        }
        
        // Only attempt reconnection if the close was not intentional
        if (event.code !== 1000 && jobId) {
          setStatusMessage('Connection lost, attempting to reconnect...');
          // Attempt reconnection after 3 seconds
          reconnectTimeoutRef.current = window.setTimeout(() => {
            connectWebSocket(jobId);
          }, 3000);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        setError('WebSocket connection failed');
        // Fall back to polling
        startPolling(jobId);
      };

    } catch (e) {
      console.error('Failed to create WebSocket connection:', e);
      setError('Failed to establish real-time connection');
      // Fall back to polling
      startPolling(jobId);
    }
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = (message: WebSocketMessage) => {
    const { event, task, plan, plan_progress } = message;

    switch (event) {
      case 'connected':
        setStatusMessage('Preparing task execution...');
        break;

      case 'initial_status':
      case 'status_response':
        if (plan) {
          setTasks(plan.tasks);
          setOverallProgress(plan.progress);
        }
        break;

      case 'plan_started':
        setStatusMessage('Task plan execution started');
        if (plan) {
          setTasks(plan.tasks);
        }
        break;

      case 'task_started':
        if (task) {
          setCurrentTaskId(task.task_id);
          setStatusMessage(task.name);
          updateTask(task);
        }
        if (plan_progress !== undefined) {
          setOverallProgress(plan_progress);
        }
        break;

      case 'task_progress':
        if (task) {
          setStatusMessage(task.message || task.name);
          updateTask(task);
        }
        if (plan_progress !== undefined) {
          setOverallProgress(plan_progress);
        }
        break;

      case 'task_completed':
        if (task) {
          updateTask(task);
        }
        if (plan_progress !== undefined) {
          setOverallProgress(plan_progress);
        }
        break;

      case 'task_failed':
        if (task) {
          updateTask(task);
          if (task.critical) {
            setError(task.error || 'Critical task failed');
          }
        }
        break;

      case 'task_retrying':
        if (task) {
          setStatusMessage(`Retrying: ${task.name}`);
          updateTask(task);
        }
        break;

      case 'plan_completed':
        setOverallProgress(100);
        setStatusMessage('Story generation complete!');
        setTimeout(() => {
          const guestId = localStorage.getItem('rg_guest_id');
          if (guestId) {
            navigate(`/journey/${guestId}`);
          } else {
            navigate(`/journey?jobId=${message.job_id}`);
          }
        }, 2000);
        break;

      case 'plan_failed':
        setError(message.data?.error || 'Generation failed');
        break;
    }
  };

  // Update a single task in the tasks array
  const updateTask = (updatedTask: Task) => {
    setTasks(prevTasks => 
      prevTasks.map(t => 
        t.task_id === updatedTask.task_id ? { ...t, ...updatedTask } : t
      )
    );
  };

  // Fallback polling for when WebSocket is not available
  const startPolling = useCallback(async (jobId: string) => {
    const maxAttempts = 120;
    let attempts = 0;

    const poll = async () => {
      try {
        const status = await apiClient.getProfileStatus(jobId);
        
        if (status.tasks) {
          setTasks(status.tasks);
        }
        setOverallProgress(status.progress || 0);
        setStatusMessage(status.message || 'Processing...');
        
        if (status.current_task) {
          const currentTask = status.tasks?.find((t: Task) => t.name === status.current_task);
          if (currentTask) {
            setCurrentTaskId(currentTask.task_id);
          }
        }

        if (status.status === 'completed') {
          setOverallProgress(100);
          setTimeout(() => {
            const guestId = localStorage.getItem('rg_guest_id');
            if (guestId) {
              navigate(`/journey/${guestId}`);
            } else {
              navigate(`/journey?jobId=${jobId}`);
            }
          }, 2000);
          return;
        } else if (status.status === 'failed') {
          setError(status.error || 'Generation failed');
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          pollTimeoutRef.current = setTimeout(poll, 2000) as any;
        } else {
          setError('Processing timeout. Please try again.');
        }
      } catch (err: any) {
        console.error('Polling error:', err);
        
        // Handle specific HTTP errors
        if (err.message && err.message.includes('404')) {
          setError('Job session not found. This may be due to a server restart. Please try generating again.');
          return;
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          pollTimeoutRef.current = setTimeout(poll, 3000) as any;
        } else {
          setError('Connection lost. Please try again.');
        }
      }
    };

    poll();
  }, [navigate]);

  // Initialize on mount
  useEffect(() => {
    const urlParam = searchParams.get('url') || '';
    const jobIdParam = searchParams.get('jobId') || '';
    
    setUrl(urlParam);
    setJobId(jobIdParam);
    setTasks(defaultTasks);
    
    if (jobIdParam) {
      connectWebSocket(jobIdParam);
    } else {
      setError('No job ID provided');
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, [searchParams, connectWebSocket]);

  if (error) {
    return (
      <main className="processing-page">
        <GlobeBackground taskTrigger={0} />
        <div className="processing-container error-state">
          <div className="error-icon">
            <svg viewBox="0 0 24 24" fill="none" width="64" height="64">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <h1>Something went wrong</h1>
          <p className="error-message">{error}</p>
          <button className="retry-button" onClick={() => navigate('/')}>
            Try Again
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="processing-page">
      <GlobeBackground taskTrigger={activeTask ? activeTask.order : 0} />
      
      <div className="processing-container" style={{ position: 'relative', zIndex: 1 }}>
        {/* Header */}
        <div className="processing-header">
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h1 className="gradient-text">Regenerating Your Story</h1>
            <p className="url-display">
              Analysing: <span className="url-highlight">{url}</span>
            </p>
            <div className="connection-status-pill">
              <span className={`status-dot-pill ${isConnected ? 'connected' : 'disconnected'}`}></span>
              <span className="status-text-pill">{isConnected ? 'Live Connection' : 'Connecting...'}</span>
            </div>
          </motion.div>
        </div>

        {/* Center Active Task Display */}
        <div className="active-task-display glass card-glow">
            <AnimatePresence mode="wait">
                {activeTask ? (
                    <motion.div
                        key={activeTask.task_id}
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 1.1, filter: "blur(10px)" }}
                        transition={{ duration: 0.5 }}
                        className="active-task-card"
                    >
                        <div className="active-task-icon-container">
                             {/* Large Icon / Spinner */}
                             {activeTask.status === 'running' || activeTask.status === 'pending' ? (
                                <div className="spinner-large">
                                    <div className="spinner-ring-ping"></div>
                                    <div className="spinner-ring-spin"></div>
                                    <div className="spinner-text">
                                        <span>{activeTask.order}</span>
                                    </div>
                                </div>
                             ) : (
                                <div className="icon-completed-large">
                                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                </div>
                             )}
                        </div>

                        <h2 className="active-task-title">{activeTask.name}</h2>
                        <p className="active-task-description">
                            {activeTask.status === 'running' && activeTask.message ? activeTask.message : activeTask.description}
                        </p>
                        
                        <div className="active-task-step">
                            <span>Step {activeTask.order} of {tasks.length}</span>
                        </div>
                    </motion.div>
                ) : (
                    <motion.div 
                        initial={{ opacity: 0 }} 
                        animate={{ opacity: 1 }}
                        className="initializing-text"
                    >
                        Initializing journey...
                    </motion.div>
                )}
            </AnimatePresence>
        </div>

        {/* Overall Progress Footer */}
        <div className="progress-footer">
          <div className="progress-footer-content">
            <div className="progress-labels">
                <span className="progress-label-text">Total Completion</span>
                <span className="progress-label-value">{Math.round(overallProgress)}%</span>
            </div>
            <div className="progress-track">
                <motion.div 
                    className="progress-fill-animated"
                    initial={{ width: 0 }}
                    animate={{ width: `${overallProgress}%` }}
                    transition={{ type: "spring", stiffness: 50, damping: 20 }}
                />
            </div>
             <p className="progress-footer-note">
              reGen is analysing your professional journey across multiple platforms.<br />
              <span className="disclaimer">reGen can make mistakes, so double-check. You can amend or regenerate journey.</span>
            </p>
          </div>
        </div>

      </div>
    </main>
  );
};

export default Regen;
