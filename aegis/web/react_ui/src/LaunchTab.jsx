// aegis/web/react_ui/src/LaunchTab.jsx
import React, { useState, useEffect } from 'react';
import TaskResultViewer from './components/TaskResultViewer';

/**
 * The main component for the "Launch" tab.
 * This component provides the primary interface for users to initiate an agent
 * task. It includes a text area for the prompt, a dropdown to select a
 * configuration preset, and a button to launch the task. It also handles
 * loading states, error display, and rendering the final task result.
 * @returns {React.Component} The launch tab component.
 */
export default function LaunchTab() {
  const [prompt, setPrompt] = useState('');
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [response, setResponse] = useState(null);

  // Fetch available presets when the component mounts.
  useEffect(() => {
    fetch('/api/presets')
      .then(res => res.json())
      .then(data => {
        setPresets(data);
        // Set the default preset if it exists
        const defaultPreset = data.find(p => p.id === 'default');
        if (defaultPreset) {
          setSelectedPreset(defaultPreset.id);
        }
      })
      .catch(err => console.error("Failed to fetch presets:", err));
  }, []);

  /**
   * Handles the task launch by sending a POST request to the /api/launch endpoint.
   */
  const launch = async () => {
    setIsLoading(true);
    setError('');
    setResponse(null);

    const body = {
      task: { prompt },
      config: selectedPreset || 'default'
    };

    try {
      const res = await fetch('/api/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || `HTTP Error: ${res.status}`);
      }
      setResponse(json);
    } catch (err) {
      console.error("Launch error:", err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h2>🚀 Launch Agent</h2>

      <label htmlFor="preset">Preset:</label>
      <select id="preset" value={selectedPreset} onChange={e => setSelectedPreset(e.target.value)}
        style={{ marginBottom: '1rem', display: 'block' }} disabled={isLoading}>
        <option value="">-- Use Default --</option>
        {presets.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}
      </select>

      <textarea placeholder="Enter your task prompt here..." rows="4" value={prompt}
        onChange={e => setPrompt(e.target.value)} style={{ width: '100%', marginBottom: '1rem' }} disabled={isLoading} />

      <button onClick={launch} disabled={isLoading || !prompt}>
        {isLoading ? 'Launching...' : 'Launch Task'}
      </button>

      {error && (
        <div style={{ marginTop: '1rem', background: '#4d0000', color: '#ffb3b3', padding: '1rem', borderRadius: '6px' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {response && <TaskResultViewer taskResult={response} />}
    </div>
  );
}