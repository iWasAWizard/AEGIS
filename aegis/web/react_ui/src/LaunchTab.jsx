// aegis/web/react_ui/src/LaunchTab.jsx
import React, { useEffect, useRef, useState } from 'react';
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
  isLoading, setIsLoading,
  error, setError,
  response, setResponse,
  launch, // This is the function from App.jsx
  // Log state and functions
  logs, setLogs, wsStatus
}) {
  const logsEndRef = useRef(null);

  // --- New State for Human-in-the-Loop ---
  const [isPaused, setIsPaused] = useState(false);
  const [agentQuestion, setAgentQuestion] = useState('');
  const [humanFeedback, setHumanFeedback] = useState('');
  const [pausedTaskId, setPausedTaskId] = useState(null);

  // --- New State for Execution Overrides ---
  const [executionOverrides, setExecutionOverrides] = useState('');
  const [isSafeMode, setIsSafeMode] = useState(true);


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

  const handleLaunch = async () => {
    if (isLoading || !prompt || !selectedPreset || !selectedBackend) {
        return;
    }
    setIsLoading(true);
    setError('');
    setResponse(null);
    setLogs([]);
    setIsPaused(false); // Reset pause state on new launch

    try {
      // Pass the local state for overrides and safe mode to the lifted launch function
      const res = await launch(executionOverrides, isSafeMode);
      if (res.status === 'PAUSED') {
        setIsPaused(true);
        setPausedTaskId(res.task_id);
        // A bit brittle, but we parse the question from the summary string.
        const question = res.summary.split("question: '")[1]?.slice(0, -1) || "The agent is waiting for input.";
        setAgentQuestion(question);
      } else {
        setResponse(res);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResume = async () => {
    if (isLoading || !pausedTaskId || !humanFeedback) {
      return;
    }
    setIsLoading(true);
    setError('');
    setResponse(null);
    // Don't clear logs on resume

    try {
      const res = await fetch('/api/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: pausedTaskId, human_feedback: humanFeedback })
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP Error: ${res.status}`);

      setResponse(json);
      // Task is no longer paused
      setIsPaused(false);
      setPausedTaskId(null);
      setAgentQuestion('');
      setHumanFeedback('');

    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };


  const isLaunchDisabled = isLoading || isPaused || !prompt || !selectedPreset || !selectedBackend;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', alignItems: 'start' }}>
      <div style={{ display: 'flex', flexDirection: 'column', maxHeight: 'calc(100vh - 120px)'}}>
        <div style={{ flexShrink: 0 }}>
            {!isPaused ? (
              <>
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
                            placeholder='{ "iterations": 5 }'
                            rows="3"
                            value={executionOverrides}
                            onChange={(e) => setExecutionOverrides(e.target.value)}
                            style={{ width: '100%', marginTop: '0.5rem', fontFamily: 'monospace' }}
                            disabled={isLoading}
                        />
                    </details>
                </div>

                <button onClick={handleLaunch} disabled={isLaunchDisabled} style={{ cursor: isLaunchDisabled ? 'not-allowed' : 'pointer', fontWeight: 'bold', padding: '0.75rem 1.5rem'}}>
                  {isLoading ? 'Launching...' : 'Launch Task'}
                </button>
              </>
            ) : (
              <div style={{ border: '1px solid var(--accent)', borderRadius: '6px', padding: '1.5rem', background: 'rgba(59, 130, 246, 0.1)' }}>
                <h2>⏸️ Task Paused - Human Input Required</h2>
                <p style={{ opacity: 0.9 }}>The agent has paused its execution and is waiting for your feedback to continue.</p>

                <div style={{ marginBottom: '1rem' }}>
                  <strong>Agent's Question:</strong>
                  <p style={{ background: 'var(--input-bg)', padding: '0.75rem', borderRadius: '4px', border: '1px solid var(--border)' }}>{agentQuestion}</p>
                </div>

                <label htmlFor="human-feedback">Your Response:</label>
                <textarea
                  id="human-feedback"
                  rows="4"
                  value={humanFeedback}
                  onChange={e => setHumanFeedback(e.target.value)}
                  placeholder="Provide instructions, information, or confirmation here..."
                  style={{ width: '100%', marginBottom: '1rem' }}
                  disabled={isLoading}
                />

                <button onClick={handleResume} disabled={isLoading || !humanFeedback} style={{ fontWeight: 'bold', padding: '0.75rem 1.5rem'}}>
                  {isLoading ? 'Resuming...' : 'Resume Task'}
                </button>
              </div>
            )}
        </div>

        {error && (
          <div style={{ marginTop: '1rem', background: '#4d0000', color: '#ffb3b3', padding: '1rem', borderRadius: '6px', flexShrink: 0 }}>
            <strong>Error:</strong> {error}
          </div>
        )}

        {response && (
            <div style={{ flexGrow: 1, overflowY: 'auto', marginTop: '1rem', border: '1px solid var(--border)', borderRadius: '6px', display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 1rem', borderBottom: '1px solid var(--border)', background: 'var(--input-bg)', flexShrink: 0 }}>
                    <h3 style={{ margin: 0, fontSize: '1em' }}>✅ Task Complete</h3>
                    <button onClick={() => setResponse(null)} style={{fontSize: '0.9em', padding: '0.3rem 0.6rem'}}>Dismiss</button>
                </div>
                <div style={{ padding: '0 1rem 1rem 1rem', overflowY: 'auto' }}>
                    <TaskResultViewer taskResult={response} />
                </div>
            </div>
        )}
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
            height: 'calc(100vh - 160px)',
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