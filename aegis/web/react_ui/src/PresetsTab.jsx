// aegis/web/react_ui/src/PresetsTab.jsx
import React, { useEffect } from 'react';

/**
 * A component for viewing, creating, and editing agent configuration presets.
 * It provides a list of existing presets and a form with a JSON editor
 * to modify their configurations.
 * @returns {React.Component} The preset editor component.
 */
export default function PresetsTab({
  presetList,
  currentPresetId,
  presetForm,
  setPresetForm,
  presetConfigError,
  setPresetConfigError,
  loadPreset,
  savePreset,
  fetchPresets
}) {

  /**
   * Validates the config text area content as valid JSON and checks for key fields.
   * @param {string} value - The JSON string from the text area.
   */
  const handleConfigChange = (value) => {
    setPresetForm(prev => ({ ...prev, config: value }));
    try {
      const parsed = JSON.parse(value);
      let newError = '';
      if (typeof parsed !== 'object' || parsed === null) {
        newError = 'Config must be a JSON object.';
      } else if (!parsed.entrypoint) {
        newError = "Config is missing required field: 'entrypoint'.";
      } else if (!Array.isArray(parsed.nodes)) {
        newError = "Config is missing required field: 'nodes' (must be an array).";
      }
      setPresetConfigError(newError);
    } catch (e) {
      setPresetConfigError('Invalid JSON format.');
    }
  };

  /**
   * Resets the form to create a new preset.
   */
  const createNew = () => {
    loadPreset({ id: null, name: 'New Preset' }); // A bit of a hack to reset state
    setPresetForm({ id: '', name: '', description: '', config: '{\n  "state_type": "aegis.agents.task_state.TaskState",\n  "entrypoint": "",\n  "nodes": []\n}' });
    setPresetConfigError('');
  };

  return (
    <div>
      <h2>🧠 Preset Editor</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: '2rem' }}>
        <div>
          <h4>Available Presets</h4>
          <button onClick={createNew} style={{ width: '100%', marginBottom: '1rem' }}>+ New Preset</button>
          <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
            {presetList.map((p) => (
              <div key={p.id} style={{ marginBottom: '0.25rem' }}>
                <button onClick={() => loadPreset(p)} style={{ width: '100%', textAlign: 'left', fontWeight: currentPresetId === p.id ? 'bold' : 'normal' }}>{p.name}</button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4>{currentPresetId ? `Editing: ${currentPresetId}` : "New Preset"}</h4>

          <label htmlFor="preset-name">Name</label>
          <input id="preset-name" value={presetForm.name} onChange={e => setPresetForm(f => ({...f, name: e.target.value}))} placeholder="Preset Name" style={{ width: '100%', marginBottom: '0.5rem' }} />

          <label htmlFor="preset-desc">Description</label>
          <textarea id="preset-desc" value={presetForm.description} onChange={e => setPresetForm(f => ({...f, description: e.target.value}))} placeholder="Description" rows="2" style={{ width: '100%', marginBottom: '1rem' }} />

          <label htmlFor="preset-config">Configuration (JSON)</label>
          <textarea
            id="preset-config"
            value={presetForm.config}
            onChange={e => handleConfigChange(e.target.value)}
            placeholder="Config JSON"
            rows="15"
            style={{
                width: '100%',
                fontFamily: 'monospace',
                fontSize: '0.9em',
                border: presetConfigError ? '1px solid #dc3545' : '1px solid var(--border)'
            }}
          />
          {presetConfigError && <p style={{ color: '#ff6666', margin: '0.25rem 0 0 0', fontSize: '0.9em' }}>{presetConfigError}</p>}

          <button onClick={savePreset} disabled={!!presetConfigError} style={{ marginTop: '1rem' }}>💾 Save Preset</button>
        </div>
      </div>
    </div>
  );
}