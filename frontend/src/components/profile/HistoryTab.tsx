import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../lib/api';
import { useAuth } from '../../hooks/useAuth';
import './HistoryTab.css'; 

interface ProfileHistory {
  id: string;
  title?: string;
  source_url: string;
  is_default: boolean;
  created_at: string;
}

const HistoryTab: React.FC = () => {
  const navigate = useNavigate();
  const { guestId } = useAuth();
  const [histories, setHistories] = useState<ProfileHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [operationLoading, setOperationLoading] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getProfileHistory();
      setHistories(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleSetDefault = async (id: string) => {
    try {
      setOperationLoading(id);
      await apiClient.updateProfileHistory(id, { is_default: true });
      // Update local state: Set triggered ID to default=true and all others to false
      setHistories(histories.map(h => ({
        ...h,
        is_default: h.id === id
      })));
    } catch (err: any) {
      setError(err.message || 'Failed to set default');
    } finally {
      setOperationLoading(null);
    }
  };

  const handleDelete = async (id: string, isDefault: boolean) => {
    if (isDefault) {
       if (!window.confirm("This is your default profile. Are you sure you want to delete it? This might affect your public profile visibility.")) {
           return;
       }
    } else {
        if (!window.confirm("Are you sure you want to delete this profile history?")) {
            return;
        }
    }

    try {
      setOperationLoading(id);
      await apiClient.deleteProfileHistory(id);
      setHistories(histories.filter(h => h.id !== id));
    } catch (err: any) {
      setError(err.message || 'Failed to delete history');
    } finally {
      setOperationLoading(null);
    }
  };
  
  const handleLoad = async (id: string) => {
      // Reload page with query param or just direct to journey page
      if (guestId) {
        navigate(`/journey/${guestId}?history_id=${id}`);
        // We might want to reload to ensure fresh state if navigation doesn't trigger it properly
        // window.location.href = `/journey/${guestId}?history_id=${id}`;
      } else {
         console.warn("Cannot load history: No ID found");
      }
  };

  const startEditCallback = (history: ProfileHistory) => {
      setEditingId(history.id);
      setEditTitle(history.title || '');
  };

  const saveTitle = async () => {
      if (!editingId) return;
      try {
          setOperationLoading(editingId);
          await apiClient.updateProfileHistory(editingId, { title: editTitle });
          setHistories(histories.map(h => h.id === editingId ? { ...h, title: editTitle } : h));
          setEditingId(null);
      } catch (err: any) {
          setError(err.message || "Failed to update title");
      } finally {
          setOperationLoading(null);
      }
  };

  const cancelEdit = () => {
      setEditingId(null);
      setEditTitle('');
  };

  return (
    <div className="profile-tab-content">
      <div className="tab-header">
        <h3>Profile History</h3>
        <p className="tab-description">Manage your previous profile generations. Set a default profile for your public view.</p>
      </div>

      {error && <div className="error-message">{error}</div>}
      
      {loading ? (
        <div className="loading-spinner"></div>
      ) : (
        <div className="history-list">
          {histories.length === 0 ? (
            <div className="empty-state">
                <p>No history found.</p>
            </div>
          ) : (
            histories.map(history => (
              <div key={history.id} className={`history-item ${history.is_default ? 'default-history' : ''}`}>
                <div className="history-info">
                   {editingId === history.id ? (
                       <div className="edit-title-group">
                           <input 
                               type="text" 
                               value={editTitle} 
                               onChange={(e) => setEditTitle(e.target.value)}
                               className="edit-title-input"
                               autoFocus
                           />
                           <button onClick={saveTitle} className="save-btn-small" title="Save">✓</button>
                           <button onClick={cancelEdit} className="cancel-btn-small" title="Cancel">✗</button>
                       </div>
                   ) : (
                       <div className="history-title-row">
                           <span className="history-title" onClick={() => startEditCallback(history)}>
                               {history.title || 'Untitled Profile'} 
                               <span className="edit-icon-small">✎</span>
                           </span>
                           {history.is_default && <span className="default-badge">Default</span>}
                       </div>
                   )}
                   <div className="history-meta">
                       <span className="history-date">{new Date(history.created_at).toLocaleDateString()}</span>
                       <span className="history-url" title={history.source_url}>{history.source_url}</span>
                   </div>
                </div>
                <div className="history-actions">
                  <button 
                    onClick={() => handleLoad(history.id)} 
                    className="action-btn load-btn"
                    disabled={!!operationLoading}
                    title="Load this profile into the Journey view"
                  >
                    🔘 Load
                  </button>
                  {!history.is_default && (
                      <button 
                        onClick={() => handleSetDefault(history.id)} 
                        className="action-btn make-default-btn"
                        disabled={!!operationLoading}
                        title="Set as your public default profile"
                      >
                        ✓ Set Default
                      </button>
                  )}
                  <button 
                    onClick={() => handleDelete(history.id, history.is_default)} 
                    className="action-btn delete-btn"
                    disabled={!!operationLoading}
                    title="Delete this profile history"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default HistoryTab;
