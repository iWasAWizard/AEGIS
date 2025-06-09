// aegis/web/react_ui/src/PresetsTab.jsx
import React, { useEffect, useState } from 'react';

/**
 * A component for viewing, creating, and editing agent configuration presets.
 * It provides a list of existing presets and a form with a JSON editor
 * to modify their configurations.
 * @returns {React.Component} The preset editor component.
 */
export default function PresetsTab() {
  const [presets, setPresets] = useState([]);
  const [current, setCurrent] = useState(null);
  const [form, setForm] = useState({ id: '', name: '', description: '', config: '{}' });
  const [configError, setConfigError] = useState('');

  const fetchPresets = () => {
    fetch('/api/presets')
      .then(res => res.json())
      .then(setPresets)
      .catch(err => console.error("Failed to fetch presets:", err));
  };

  useEffect(() => {
    fetchPresets();
  }, []);

  /**
   * Validates the config text area content as valid JSON and checks for key fields.
   * @param {string} value - The JSON string from the text area.
   */
  const handleConfigChange = (value) => {
    setForm(prev => ({ ...prev, config: value }));
    try {
      const parsed = JSON.parse(value);
      if (typeof parsed !== 'object' || parsed === null) {
        setConfigError('Config must be a JSON object.');
      } else if (!parsed.entrypoint) {
        setConfigError("Config is missing required field: 'entrypoint'.");
      } else if (!Array.isArray(parsed.nodes)) {
        setConfigError("Config is missing required field: 'nodes' (must be an array).");
      } else {
        setConfigError(''); // Clear error if valid
      }
    } catch (e) {
      setConfigError('Invalid JSON format.');
    }
  };

  /**
   * Loads the full configuration for a selected preset into the editor form.
   * @param {object} p - The preset metadata object.
   */
  const loadPreset = (p) => {
    setCurrent(p.id);
    fetch(`/api/presets/${p.id}`)
      .then(res => res.json())
      .then(data => {
        // Separate metadata from the core config for the editor
        const { name, description, ...config } = data;
        setForm({
          id: p.id,
          name: name || p.name,
          description: description || '',
          config: JSON.stringify(config, null, 2)
        });
        setConfigError('');
      })
      .catch(err => console.error("Failed to load preset config:", err));
  };

  /**
   * Resets the form to create a new preset.
   */
  const createNew = () => {
    setCurrent(null);
    setForm({ id: '', name: '', description: '', config: '{\n  "state_type": "aegis.agents.task_state.TaskState",\n  "entrypoint": "",\n  "nodes": []\n}' });
    setConfigError('');
  };

  /**
   * Saves the current preset form data to the backend via a POST request.
   */
  const savePreset = async () => {
    if (configError) {
      alert(`Cannot save: ${configError}`);
      return;
    }

    try {
      const configObject = JSON.parse(form.config);
      const payload = {
        id: current || form.id || form.name.toLowerCase().replace(/\s+/g, '_'),
        name: form.name,
        description: form.description,
        config: configObject,
      };

      await fetch('/api/presets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      alert("Preset saved.");
      fetchPresets(); // Refresh the list
    } catch (e) {
        alert("Failed to save preset. Ensure config is valid JSON.");
    }
  };

  return (
    <div>
      <h2>🧠 Preset Editor</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 3fr', gap: '2rem' }}>
        <div>
          <h4>Available Presets</h4>
          <button onClick={createNew} style={{ width: '100%', marginBottom: '1rem' }}>+ New Preset</button>
          <div style={{ maxHeight: '60vh', overflowY: 'auto' }}>
            {presets.map((p) => (
              <div key={p.id} style={{ marginBottom: '0.25rem' }}>
                <button onClick={() => loadPreset(p)} style={{ width: '100%', textAlign: 'left', fontWeight: current === p.id ? 'bold' : 'normal' }}>{p.name}</button>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4>{current ? `Editing: ${current}` : "New Preset"}</h4>

          <label htmlFor="preset-name">Name</label>
          <input id="preset-name" value={form.name} onChange={e => setForm(f => ({...f, name: e.target.value}))} placeholder="Preset Name" style={{ width: '100%', marginBottom: '0.5rem' }} />

          <label htmlFor="preset-desc">Description</label>
          <textarea id="preset-desc" value={form.description} onChange={e => setForm(f => ({...f, description: e.target.value}))} placeholder="Description" rows="2" style={{ width: '100%', marginBottom: '1rem' }} />

          <label htmlFor="preset-config">Configuration (JSON)</label>
          <textarea
            id="preset-config"
            value={form.config}
            onChange={e => handleConfigChange(e.target.value)}
            placeholder="Config JSON"
            rows="15"
            style={{
                width: '100%',
                fontFamily: 'monospace',
                fontSize: '0.9em',
                border: configError ? '1px solid #dc3545' : '1px solid var(--border)'
            }}
          />
          {configError && <p style={{ color: '#ff6666', margin: '0.25rem 0 0 0', fontSize: '0.9em' }}>{configError}</p>}

          <button onClick={savePreset} disabled={!!configError} style={{ marginTop: '1rem' }}>💾 Save Preset</button>
        </div>
      </div>
    </div>
  );
}