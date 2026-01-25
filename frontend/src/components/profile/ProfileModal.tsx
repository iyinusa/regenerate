import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import ProfileTab from './ProfileTab';
import PrivacyTab from './PrivacyTab';
import HistoryTab from './HistoryTab';
import './ProfileModal.css';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const ProfileModal: React.FC<ProfileModalProps> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('profile');

  if (!isOpen) return null;

  const tabs = [
    { id: 'profile', label: 'Profile' },
    { id: 'privacy', label: 'Privacy' },
    { id: 'history', label: 'History' },
    { id: 'subscription', label: 'Subscription' }
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'profile':
        return <ProfileTab />;
      case 'privacy':
        return <PrivacyTab />;
      case 'history':
        return <HistoryTab />;
      case 'subscription':
        return (
          <div className="placeholder-tab">
            <div className="placeholder-icon">💎</div>
            <h3>Subscription</h3>
            <p>Manage your plan and billing details.</p>
            <p style={{ fontSize: '0.8rem', marginTop: '8px' }}>(Coming Soon)</p>
          </div>
        );
      default:
        return null;
    }
  };

  return createPortal(
    <div className="profile-modal-overlay">
      <div className="profile-modal glass" onClick={(e) => e.stopPropagation()}>
        <div className="profile-modal-header">
          <div className="profile-modal-title-bar">
            <h2 className="profile-modal-title">Manage Account</h2>
            <button className="profile-close-btn" onClick={onClose} aria-label="Close">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <div className="profile-tabs">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                className={`profile-tab ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        <div className="profile-content">
          {renderContent()}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default ProfileModal;
