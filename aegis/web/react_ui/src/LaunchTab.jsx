// aegis/web/react_ui/src/LaunchTab.jsx
import React, { useState, useEffect } from 'react';

export default function LaunchTab() {
  const [prompt, setPrompt] = useState('');
  const [response, setResponse] = useState('');
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);

  useEffect(() => {
    fetch('/api/presets')
      .then(res => res.json())
      .then(setPresets);
  }, []);

  const launch = async () => {
    const body = {
      task: {
        prompt: prompt,
      },
      config: selectedPreset ? selectedPreset.id : 'default'
    };

    const res = await fetch('/api/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    const json = await res.json();
    setResponse(JSON.stringify(json, null, 2));
  };

  return (
    <div>
      <h2>🚀 Launch Agent</h2>

      <label htmlFor="preset">Preset:</label>
      <select
        id="preset"
        onChange={e =>
          setSelectedPreset(presets.find(p => p.id === e.target.value))
        }
        style={{ marginBottom: '1rem', display: 'block' }}
      >
        <option value="">-- Choose a preset --</option>
        {presets.map((p, i) => (
          <option key={i} value={p.id}>{p.name}</option>
        ))}
      </select>

      {selectedPreset && (
        <p style={{ fontSize: '0.9em', opacity: 0.7 }}>{selectedPreset.description}</p>
      )}

      <textarea
        placeholder="Enter your task prompt here..."
        rows="4"
        value={prompt}
        onChange={e => setPrompt(e.target.value)}
        style={{ width: '100%', marginBottom: '1rem' }}
      />

      <button onClick={launch}>Launch Task</button>

      {response && (
        <pre style={{ marginTop: '1rem', background: '#111', padding: '0.5rem', fontSize: '0.85em', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
          {response}
        </pre>
      )}
    </div>
  );
}