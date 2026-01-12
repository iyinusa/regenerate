import { useEffect, useState, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiClient } from '@/lib/api.ts';
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
  const [jobId, setJobId] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [overallProgress, setOverallProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Initializing...');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Default task structure (shown before WebSocket updates)
  const defaultTasks: Task[] = [
    {
      task_id: 'task_001',
      task_type: 'fetch_profile',
      name: 'Extracting Profile Data',
      description: 'Using Gemini 3 to fetch and analyze profile data',
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
      description: 'Creating interactive timeline visualization',
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
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = import.meta.env.VITE_API_URL 
      ? new URL(import.meta.env.VITE_API_URL).host 
      : window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/ws/tasks/${jobId}`;
    
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setStatusMessage('Connected to task stream...');
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleWebSocketMessage(message);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        
        // Attempt reconnection after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          if (jobId) {
            connectWebSocket(jobId);
          }
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
        // Fall back to polling
        startPolling(jobId);
      };

    } catch (e) {
      console.error('Failed to connect WebSocket:', e);
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
          navigate(`/journey?jobId=${message.job_id}`);
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
            navigate(`/journey?jobId=${jobId}`);
          }, 2000);
          return;
        } else if (status.status === 'failed') {
          setError(status.error || 'Generation failed');
          return;
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 2000);
        } else {
          setError('Processing timeout. Please try again.');
        }
      } catch (err) {
        console.error('Polling error:', err);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 3000);
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
    };
  }, [searchParams, connectWebSocket]);

  // Get task status icon
  const getTaskIcon = (task: Task) => {
    switch (task.status) {
      case 'completed':
        return (
          <svg className="task-icon completed" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <path d="M8 12l2.5 2.5L16 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        );
      case 'running':
        return <div className="task-icon running"><div className="spinner"></div></div>;
      case 'failed':
        return (
          <svg className="task-icon failed" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <path d="M15 9l-6 6M9 9l6 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        );
      case 'skipped':
        return (
          <svg className="task-icon skipped" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <path d="M8 12h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        );
      default:
        return (
          <div className="task-icon pending">
            <span>{task.order}</span>
          </div>
        );
    }
  };

  if (error) {
    return (
      <main className="processing-page">
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
      <div className="processing-container">
        {/* Header */}
        <div className="processing-header">
          <div className="header-glow"></div>
          <h1 className="gradient-text">Regenerating Your Story</h1>
          <p className="url-display">
            Analyzing: <span className="url-highlight">{url}</span>
          </p>
          <div className="connection-status">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
            <span className="status-text">{isConnected ? 'Live updates' : 'Reconnecting...'}</span>
          </div>
        </div>

        {/* Current Status */}
        <div className="current-status">
          <div className="status-pulse"></div>
          <span className="status-message">{statusMessage}</span>
        </div>

        {/* Task List */}
        <div className="tasks-container">
          {tasks.map((task, index) => (
            <div 
              key={task.task_id}
              className={`task-item ${task.status} ${task.task_id === currentTaskId ? 'current' : ''}`}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div className="task-icon-wrapper">
                {getTaskIcon(task)}
              </div>
              
              <div className="task-content">
                <div className="task-header">
                  <span className="task-name">{task.name}</span>
                  {task.status === 'running' && task.progress > 0 && (
                    <span className="task-percentage">{task.progress}%</span>
                  )}
                </div>
                
                <div className="task-description">
                  {task.status === 'running' && task.message ? task.message : task.description}
                </div>
                
                {task.status === 'running' && (
                  <div className="task-progress-bar">
                    <div 
                      className="task-progress-fill" 
                      style={{ width: `${task.progress}%` }}
                    ></div>
                  </div>
                )}
                
                {task.status === 'failed' && task.error && (
                  <div className="task-error">{task.error}</div>
                )}
              </div>
              
              {task.status === 'completed' && (
                <div className="task-checkmark">
                  <svg viewBox="0 0 24 24" fill="none">
                    <path d="M5 12l5 5L20 7" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Overall Progress */}
        <div className="overall-progress">
          <div className="progress-header">
            <span>Overall Progress</span>
            <span className="progress-percentage">{overallProgress}%</span>
          </div>
          <div className="progress-bar-container">
            <div 
              className="progress-bar-fill" 
              style={{ width: `${overallProgress}%` }}
            >
              <div className="progress-bar-glow"></div>
            </div>
          </div>
        </div>

        {/* Footer Note */}
        <p className="processing-note">
          <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
            <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
          </svg>
          Gemini 3 is analyzing your professional journey across multiple platforms.
        </p>
      </div>
    </main>
  );
};

export default Regen;
