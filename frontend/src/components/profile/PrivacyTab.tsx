import React, { useState, useEffect } from 'react';
import { apiClient } from '../../lib/api';
import './ProfileModal.css';

const SECTIONS = [
  { id: 'chronicles', label: 'Chronicles' },
  { id: 'experience', label: 'Experience' },
  { id: 'projects', label: 'Projects' },
  { id: 'skills', label: 'Expertise/Skills' },
  { id: 'education', label: 'Education' }
];

interface PrivacySettings {
    is_public: boolean;
    hidden_sections: Record<string, boolean>;
    username?: string;
    user_id: string;
}

const PrivacyTab: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [settings, setSettings] = useState<PrivacySettings | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [username, setUsername] = useState('');
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            const data = await apiClient.request('/api/v1/privacy/');
            setSettings(data);
            setUsername(data.username || '');
        } catch (err) {
            setError('Failed to load privacy settings');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            const data = await apiClient.request('/api/v1/privacy/', {
                method: 'PUT',
                body: JSON.stringify({
                    is_public: settings?.is_public,
                    hidden_sections: settings?.hidden_sections,
                    username: username
                })
            });
            setSettings(data);
            // Optionally show success toast/message
        } catch (err: any) {
            setError(err.message || 'Failed to save settings');
        } finally {
            setSaving(false);
        }
    };

    const toggleSection = (sectionId: string) => {
        if (!settings) return;
        setSettings({
            ...settings,
            hidden_sections: {
                ...settings.hidden_sections,
                [sectionId]: !settings.hidden_sections[sectionId]
            }
        });
    };
    
    const togglePublic = () => {
        if (!settings) return;
        setSettings({
            ...settings,
            is_public: !settings.is_public
        });
    }

    const publicUrl = window.location.origin + '/' + username;

    const copyLink = () => {
        navigator.clipboard.writeText(publicUrl);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    if (loading) return <div className="profile-loading">Loading settings...</div>;

    return (
        <div className="profile-tab-content">
             {/* Public Profile Section */}
             <div className="profile-section">
                <div className="profile-section-title">Public Profile Configuration</div>
                
                <div className="form-group">
                    <label className="form-label">Public Access</label>
                    <div className="privacy-toggle-group">
                        <div className="privacy-toggle-label">
                            <h3 style={{ fontSize: '1rem', margin: 0 }}>Enable Public Link</h3>
                            <p style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.5)', margin: '4px 0 0 0' }}>Allow anyone with the link to view your journey.</p>
                        </div>
                        <label className="switch">
                            <input 
                                type="checkbox" 
                                checked={settings?.is_public || false}
                                onChange={togglePublic}
                            />
                            <span className="slider round"></span>
                        </label>
                    </div>
                </div>

                <div className="form-group">
                    <label className="form-label">Username</label>
                    <div className="username-input-group">
                        <span className="domain-prefix">{window.location.host}/</span>
                        <input 
                            type="text" 
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            className="form-input"
                            style={{ border: 'none', background: 'transparent', paddingLeft: 4 }}
                            placeholder="username"
                        />
                    </div>
                </div>

                {settings?.is_public && !!username && (
                    <div className="public-link-container" style={{ marginTop: '16px' }}>
                        <a href={`/${username}`} target="_blank" rel="noopener noreferrer" className="public-link">
                            {publicUrl} 
                            <svg className="external-link-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                        </a>
                        <button onClick={copyLink} className="copy-btn">
                            {copied ? 'Copied!' : 'Copy Link'}
                        </button>
                    </div>
                )}
            </div>

            {/* Visibility Section */}
            <div className="profile-section">
                <div className="profile-section-title">Section Visibility</div>
                <p className="section-desc">Control which sections are displayed on your public profile.</p>

                <div className="sections-list">
                    {SECTIONS.map(section => (
                        <div key={section.id} className="section-item">
                            <span>{section.label}</span>
                             <div style={{ display: 'flex', alignItems: 'center' }}>
                                <span className="visibility-label" style={{ marginRight: '12px' }}>
                                    {settings?.hidden_sections?.[section.id] ? 'Hidden' : 'Visible'}
                                </span>
                                <label className="switch">
                                    <input 
                                        type="checkbox" 
                                        checked={!settings?.hidden_sections?.[section.id]} // Checked means visible
                                        onChange={() => toggleSection(section.id)}
                                    />
                                    <span className="slider round"></span>
                                </label>
                             </div>
                        </div>
                    ))}
                </div>
            </div>

            {error && <div className="profile-error" style={{ color: '#ff8a80', marginBottom: '16px' }}>{error}</div>}

            <div className="form-actions">
                <button 
                    className="btn-primary" 
                    onClick={handleSave}
                    disabled={saving}
                >
                    {saving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>
        </div>
    );
};

export default PrivacyTab;
