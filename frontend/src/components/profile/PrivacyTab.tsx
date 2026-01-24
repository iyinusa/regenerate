import React, { useState, useEffect } from 'react';
import { apiClient } from '../../lib/api';
import './ProfileModal.css';

const SECTIONS = [
  { id: 'chronicles', label: 'Chronicles' },
  { id: 'experience', label: 'Experience' },
  { id: 'skills', label: 'Expertise/Skills' },
  { id: 'projects', label: 'Projects' },
  { id: 'education', label: 'Academics' },
  { id: 'certifications', label: 'Certifications' }
];

interface PrivacySettings {
    is_public: boolean;
    hidden_sections: Record<string, boolean>;
    username?: string;
    user_id: string;
    guest_id: string;
}

interface ProfileData {
    experiences?: any[];
    education?: any[];
    skills?: string[];
    projects?: any[];
    certifications?: any[];
    timeline?: { events?: any[] };
}

const PrivacyTab: React.FC = () => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [settings, setSettings] = useState<PrivacySettings | null>(null);
    const [profileData, setProfileData] = useState<ProfileData | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [username, setUsername] = useState('');
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        fetchSettings();
    }, []);

    const fetchSettings = async () => {
        try {
            // Fetch privacy settings
            const privacyData = await apiClient.request('/api/v1/privacy/');
            setSettings(privacyData);
            setUsername(privacyData.username || '');
            
    // Fetch profile data to check what sections have content
            try {
                // Fetch complete journey data using the guest_id from privacy settings
                const journeyResponse = await apiClient.getJourneyByGuestId(privacyData.guest_id);
                
                setProfileData({
                    ...journeyResponse.profile,
                    timeline: journeyResponse.timeline
                });
            } catch (profileErr) {
                console.warn('Could not fetch profile data:', profileErr);
                // Continue with just privacy settings if profile fetch fails
            }
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

    // Get sections that actually have data
    const getAvailableSections = () => {
        if (!profileData) return [];
        
        return SECTIONS.filter(section => {
            switch (section.id) {
                case 'chronicles':
                    return profileData.timeline?.events && profileData.timeline.events.length > 0;
                case 'experience':
                    return profileData.experiences && profileData.experiences.length > 0;
                case 'education':
                    return profileData.education && profileData.education.length > 0;
                case 'skills':
                    return profileData.skills && profileData.skills.length > 0;
                case 'projects':
                    return profileData.projects && profileData.projects.length > 0;
                case 'certifications':
                    return profileData.certifications && profileData.certifications.length > 0;
                default:
                    return false;
            }
        });
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
                    {getAvailableSections().map(section => (
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
                    {getAvailableSections().length === 0 && (
                        <div style={{ textAlign: 'center', color: 'rgba(255,255,255,0.5)', padding: '2rem' }}>
                            No sections available. Complete your profile to see privacy options.
                        </div>
                    )}
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
