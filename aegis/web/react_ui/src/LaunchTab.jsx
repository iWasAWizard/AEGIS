// aegis/web/react_ui/src/LaunchTab.jsx
import React, { useEffect, useRef } from 'react';
import TaskResultViewer from './components/TaskResultViewer';
import Ansi from 'ansi-to-react';

/**
 * The main component for the "Launch" tab.
 * This component provides the primary interface for users to initiate an agent task.
 * @param {object} props - The component props.
 * @returns {React.Component} The launch tab component.
 */
export default function LaunchTab({
  // Config state and setters
  prompt, setPrompt,
  presets, selectedPreset, setSelectedPreset,
  backends, selectedBackend, setSelectedBackend,
  models, selectedModel, setSelectedModel,
  // Execution state and functions
  isLoading, error, response, launch,
  isSafeMode, setIsSafeMode,
  executionOverrides, setExecutionOverrides,
  // Log state and functions
  logs, setLogs, wsStatus
}) {
  const logsEndRef = useRef(null);

  // Effect to scroll to the bottom whenever new logs arrive.
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);


  const getWsStatusColor = () => {
    switch (wsStatus) {
      case 'Connected': return 'lightgreen';
      case 'Connecting...': return 'orange';
      default: return '#ff6666';
    }
  };

  const isLaunchDisabled = isLoading || !prompt || !selectedPreset || !selectedBackend || !selectedModel;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
      <div>
        <h2>🚀 Launch Agent</h2>
        <p style={{ opacity: 0.8, marginTop: '-0.5rem', marginBottom: '1.5rem' }}>
          This is the primary control panel for executing agent tasks. Enter a high-level goal, select a configuration, and click "Launch Task".
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
                <label htmlFor="preset">Agent Preset:</label>
                <select id="preset" value={selectedPreset} onChange={e => setSelectedPreset(e.target.value)} disabled={isLoading}>
                  {Array.isArray(presets) && presets.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}
                </select>
            </div>
            <div>
                <label htmlFor="backend">Backend Profile:</label>
                <select id="backend" value={selectedBackend} onChange={e => setSelectedBackend(e.target.value)} disabled={isLoading}>
                    {Array.isArray(backends) && backends.map((b) => (<option key={b.profile_name} value={b.profile_name}>{b.profile_name} ({b.type})</option>))}
                </select>
            </div>
            <div>
                <label htmlFor="model">Agent Model:</label>
                <select id="model" value={selectedModel} onChange={e => setSelectedModel(e.target.value)} disabled={isLoading} style={{ minWidth: '200px' }}>
                    {Array.isArray(models) && models.map((m) => (<option key={m.key} value={m.key}>{m.name}</option>))}
                </select>
            </div>
        </div>

        <label htmlFor="prompt">Task Prompt:</label>
        <textarea id="prompt" placeholder="Enter your task prompt here..." rows="4" value={prompt}
          onChange={e => setPrompt(e.target.value)} style={{ width: '100%', marginBottom: '1rem' }} disabled={isLoading} />

        <div style={{ marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                    type="checkbox"
                    id="safe-mode-toggle"
                    checked={isSafeMode}
                    onChange={(e) => setIsSafeMode(e.target.checked)}
                    disabled={isLoading}
                />
                <label htmlFor="safe-mode-toggle">Enable Safe Mode (blocks dangerous tools)</label>
            </div>

            <details>
                <summary style={{ cursor: 'pointer', opacity: 0.8 }}>Advanced: Execution Overrides</summary>
                <textarea
                    placeholder='{ "iterations": 5, "safe_mode": false }'
                    rows="3"
                    value={executionOverrides}
                    onChange={(e) => setExecutionOverrides(e.target.value)}
                    style={{ width: '100%', marginTop: '0.5rem', fontFamily: 'monospace' }}
                    disabled={isLoading}
                />
            </details>
        </div>


        <button onClick={launch} disabled={isLaunchDisabled} style={{ cursor: isLaunchDisabled ? 'not-allowed' : 'pointer', fontWeight: 'bold', padding: '0.75rem 1.5rem'}}>
          {isLoading ? 'Launching...' : 'Launch Task'}
        </button>

        {error && (
          <div style={{ marginTop: '1rem', background: '#4d0000', color: '#ffb3b3', padding: '1rem', borderRadius: '6px' }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {response && <TaskResultViewer taskResult={response} />}
      </div>

      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0 }}>📡 Live Task Logs</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ color: getWsStatusColor(), fontSize: '0.9em' }}>● {wsStatus}</span>
                <button
                    onClick={() => setLogs([])}
                    style={{fontSize: '0.9em', padding: '0.3rem 0.6rem'}}
                >
                    Clear Task Logs
                </button>
            </div>
        </div>
        <pre style={{
            background: '#0a0a0a',
            color: 'var(--fg)',
            fontFamily: 'monospace',
            fontSize: '0.85em',
            padding: '1rem',
            height: 'calc(100vh - 250px)',
            minHeight: '300px',
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            border: '1px solid var(--border)',
            borderRadius: '4px'
        }}>
            {logs.slice(-500).map((log, index) => (
            <div key={log.timestamp + '-' + index}>
                <Ansi>{log.msg}</Ansi>
            </div>
            ))}
            <div ref={logsEndRef} />
        </pre>
      </div>
    </div>
  );
}