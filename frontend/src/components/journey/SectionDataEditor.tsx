import React, { useState, useEffect, KeyboardEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { SectionEditorConfig } from './sectionEditorConfig';
import { apiClient } from '@/lib/api';
import './SectionDataEditor.css';

interface SectionDataEditorProps {
  isOpen: boolean;
  onClose: () => void;
  config: SectionEditorConfig;
  items: any[];
  historyId: string;
  onItemsUpdate: (updatedItems: any[]) => void;
}

const SectionDataEditor: React.FC<SectionDataEditorProps> = ({
  isOpen,
  onClose,
  config,
  items: initialItems,
  historyId,
  onItemsUpdate
}) => {
  const [items, setItems] = useState<any[]>([]);
  const [editingItem, setEditingItem] = useState<any | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Ensure all items have IDs for proper tracking
  const ensureItemIds = (itemsList: any[]) => {
    // Ensure itemsList is actually an array
    if (!Array.isArray(itemsList)) {
      console.warn('Items is not an array:', itemsList);
      return [];
    }
    return itemsList.map((item, index) => {
      if (!item.id) {
        return {
          ...item,
          id: `${config.itemName}_${Date.now()}_${index}_${Math.random().toString(36).substr(2, 9)}`
        };
      }
      return item;
    });
  };

  // Update items when prop changes
  useEffect(() => {
    const itemsWithIds = ensureItemIds(initialItems || []);
    setItems(itemsWithIds);
  }, [initialItems, config.itemName]);

  // Handle save items to backend
  const saveItems = async () => {
    if (!historyId) {
      setError('Missing history ID');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      // Use apiClient to handle authentication properly
      const endpoint = `/api/v1/profile/${config.apiPath}/${historyId}`;
      await apiClient.put(endpoint, items);

      setSuccess(`${config.displayName} saved successfully!`);
      onItemsUpdate(items);
      
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      console.error(`Failed to save ${config.itemNamePlural}:`, err);
      setError(err instanceof Error ? err.message : `Failed to save ${config.itemNamePlural}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle item edit
  const handleEditItem = (item: any) => {
    // Ensure tags fields are arrays
    const normalizedItem = { ...item };
    config.fields.forEach(field => {
      if (field.type === 'tags' && !Array.isArray(normalizedItem[field.name])) {
        normalizedItem[field.name] = normalizedItem[field.name] ? [normalizedItem[field.name]] : [];
      }
    });
    setEditingItem(normalizedItem);
    setIsCreating(false);
  };

  // Handle item creation
  const handleCreateItem = () => {
    const newItem = config.createEmptyItem();
    setEditingItem(newItem);
    setIsCreating(true);
  };

  // Handle item save
  const handleSaveItem = () => {
    if (!editingItem) return;

    // Validate required fields
    const missingFields = config.fields
      .filter(field => field.required && !editingItem[field.name])
      .map(field => field.label);

    if (missingFields.length > 0) {
      setError(`Missing required fields: ${missingFields.join(', ')}`);
      return;
    }

    if (isCreating) {
      const newItem = { 
        ...editingItem, 
        id: `${config.itemName}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}` 
      };
      setItems([...items, newItem]);
    } else {
      setItems(items.map(item => item.id === editingItem.id ? editingItem : item));
    }

    setEditingItem(null);
    setIsCreating(false);
    setError(null);
  };

  // Handle item delete
  const handleDeleteItem = (itemId: string) => {
    setItems(items.filter(item => (item.id || item) !== itemId));
  };

  // Handle field change with special handling for category and tags
  const handleFieldChange = (fieldName: string, value: any) => {
    if (!editingItem) return;

    const field = config.fields.find(f => f.name === fieldName);
    
    if (field?.type === 'select') {
      const option = field.options?.find(opt => opt.value === value);
      if (option?.metadata) {
        // Update related fields from metadata (e.g., color, icon for category)
        setEditingItem({
          ...editingItem,
          [fieldName]: value,
          ...option.metadata
        });
        return;
      }
    }

    setEditingItem({
      ...editingItem,
      [fieldName]: value
    });
  };

  // Close modal and reset state
  const handleClose = () => {
    setEditingItem(null);
    setIsCreating(false);
    setError(null);
    setSuccess(null);
    onClose();
  };

  if (!isOpen) return null;

  const displayItems = config.sortItems ? config.sortItems(items) : items;

  return (
    <AnimatePresence>
      <motion.div
        className="section-editor-overlay"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={handleClose}
      >
        <motion.div
          className="section-editor-modal"
          initial={{ opacity: 0, scale: 0.5, y: 50 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.5, y: 20 }}
          transition={{ type: "spring", damping: 15, stiffness: 100 }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Modal Header */}
          <div className="section-editor-header">
            <h2 className="modal-title gradient-text">Edit {config.displayName}</h2>
            <p className="modal-subtitle">Manage your {config.itemNamePlural}</p>
            <button 
              onClick={handleClose}
              className="modal-close-btn"
              aria-label="Close modal"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          {/* Status Messages */}
          {error && (
            <div className="status-message error-message">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
              </svg>
              {error}
            </div>
          )}

          {success && (
            <div className="status-message success-message">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
              </svg>
              {success}
            </div>
          )}

          {/* Modal Content */}
          <div className="section-editor-content">
            {!editingItem ? (
              <>
                {/* Items List */}
                <div className="items-list">
                  <div className="items-header">
                    <h3>{config.displayName} ({items.length})</h3>
                    <button 
                      onClick={handleCreateItem}
                      className="primary-btn create-item-btn"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                      </svg>
                    </button>
                  </div>

                  <div className="items-grid">
                    {displayItems.map((item) => {
                      const badge = config.getItemBadge?.(item);
                      const title = config.getItemTitle(item);
                      const subtitle = config.getItemSubtitle?.(item);
                      const description = config.getItemDescription?.(item);

                      return (
                        <div key={item.id || item} className="item-card">
                          <div className="item-card-header">
                            {badge && (
                              <div 
                                className="item-category-badge"
                                style={{ backgroundColor: badge.color }}
                              >
                                {badge.text}
                              </div>
                            )}
                            {item.date && <div className="item-date">{item.date}</div>}
                            <div className="item-actions">
                              <button 
                                onClick={() => handleEditItem(item)}
                                className="item-action-btn edit-btn"
                                title={`Edit ${config.itemName}`}
                              >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <path d="m18 2 4 4-5.5 5.5-4-4L18 2z"></path>
                                  <path d="M11.5 6.5 6 12v4h4l5.5-5.5"></path>
                                </svg>
                              </button>
                              <button 
                                onClick={() => handleDeleteItem(item.id || item)}
                                className="item-action-btn delete-btn"
                                title={`Delete ${config.itemName}`}
                              >
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <polyline points="3,6 5,6 21,6"></polyline>
                                  <path d="m19,6v14a2,2 0 0,1-2,2H7a2,2 0 0,1-2-2V6m3,0V4a2,2 0 0,1,2-2h4a2,2 0 0,1,2,2v2"></path>
                                </svg>
                              </button>
                            </div>
                          </div>

                          <div className="item-card-content">
                            <h4 className="item-title">{title}</h4>
                            {subtitle && <p className="item-subtitle">{subtitle}</p>}
                            {description && (
                              <p className="item-description">
                                {description.length > 100 
                                  ? `${description.substring(0, 100)}...` 
                                  : description}
                              </p>
                            )}
                            {item.tags && item.tags.length > 0 && (
                              <div className="item-tags">
                                {item.tags.map((tag: string, idx: number) => (
                                  <span key={idx} className="item-tag">{tag}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Action Buttons */}
                <div className='section-editor-footer'>
                  <div className="modal-actions">
                    <button 
                      onClick={handleClose} 
                      className="secondary-btn"
                      disabled={loading}
                    >
                      Cancel
                    </button>
                    <button 
                      onClick={saveItems} 
                      className="primary-btn"
                      disabled={loading}
                    >
                      {loading ? 'Saving...' : 'Save Changes'}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              /* Item Edit Form */
              <ItemEditForm
                item={editingItem}
                config={config}
                isCreating={isCreating}
                onFieldChange={handleFieldChange}
                onSave={handleSaveItem}
                onCancel={() => {
                  setEditingItem(null);
                  setIsCreating(false);
                  setError(null);
                }}
              />
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

// Separate component for the edit form
interface ItemEditFormProps {
  item: any;
  config: SectionEditorConfig;
  isCreating: boolean;
  onFieldChange: (fieldName: string, value: any) => void;
  onSave: () => void;
  onCancel: () => void;
}

const ItemEditForm: React.FC<ItemEditFormProps> = ({
  item,
  config,
  isCreating,
  onFieldChange,
  onSave,
  onCancel
}) => {
  const [tagInput, setTagInput] = useState('');

  const handleTagKeyDown = (e: KeyboardEvent<HTMLInputElement>, fieldName: string) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const value = tagInput.trim();
      if (value) {
        const currentTags = item[fieldName] || [];
        if (!currentTags.includes(value)) {
          onFieldChange(fieldName, [...currentTags, value]);
        }
        setTagInput('');
      }
    } else if (e.key === 'Backspace' && !tagInput && item[fieldName]?.length > 0) {
      // Remove last tag on backspace when input is empty
      const currentTags = item[fieldName];
      onFieldChange(fieldName, currentTags.slice(0, -1));
    }
  };

  const removeTag = (fieldName: string, tagToRemove: string) => {
    const currentTags = item[fieldName] || [];
    onFieldChange(fieldName, currentTags.filter((tag: string) => tag !== tagToRemove));
  };

  const canSave = config.fields
    .filter(field => field.required)
    .every(field => item[field.name]);

  return (
    <div className="item-edit-form">
      <h3 className="form-title">
        {isCreating ? `Create New ${config.itemName}` : `Edit ${config.itemName}`}
      </h3>

      <div className="form-grid">
        {config.fields.map((field) => {
          // For tags fields, ensure default is an array, not a string
          const defaultValue = field.type === 'tags' ? [] : (field.defaultValue || '');
          const value = item[field.name] !== undefined && item[field.name] !== null 
            ? item[field.name] 
            : defaultValue;

          return (
            <div key={field.name} className={`form-group ${field.type === 'textarea' ? 'full-width' : ''}`}>
              <label htmlFor={`field-${field.name}`}>
                {field.label} {field.required && '*'}
              </label>

              {field.type === 'text' || field.type === 'date' || field.type === 'number' ? (
                <input
                  id={`field-${field.name}`}
                  type={field.type === 'number' ? 'number' : 'text'}
                  value={value}
                  onChange={(e) => onFieldChange(field.name, e.target.value)}
                  placeholder={field.placeholder}
                  required={field.required}
                />
              ) : field.type === 'textarea' ? (
                <textarea
                  id={`field-${field.name}`}
                  value={value}
                  onChange={(e) => onFieldChange(field.name, e.target.value)}
                  placeholder={field.placeholder}
                  rows={field.rows || 3}
                />
              ) : field.type === 'select' ? (
                <select
                  id={`field-${field.name}`}
                  value={value}
                  onChange={(e) => onFieldChange(field.name, e.target.value)}
                >
                  {field.options?.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              ) : field.type === 'tags' ? (
                <div className="tags-input-container">
                  <div className="tags-display">
                    {Array.isArray(value) && value.map((tag, idx) => (
                      <span key={idx} className="tag-chip">
                        {tag}
                        <button
                          type="button"
                          onClick={() => removeTag(field.name, tag)}
                          className="tag-remove"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                    <input
                      type="text"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyDown={(e) => handleTagKeyDown(e, field.name)}
                      placeholder={field.placeholder}
                      className="tag-input"
                    />
                  </div>
                  <p className="field-hint">Press Enter or comma to add tags</p>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      {/* Form Actions */}
      <div className="form-actions">
        <button onClick={onCancel} className="secondary-btn">
          Cancel
        </button>
        <button 
          onClick={onSave}
          className="primary-btn"
          disabled={!canSave}
        >
          {isCreating ? `Create ${config.itemName}` : 'Save Changes'}
        </button>
      </div>
    </div>
  );
};

export default SectionDataEditor;
