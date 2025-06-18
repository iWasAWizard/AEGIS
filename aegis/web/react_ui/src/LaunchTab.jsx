// aegis/web/react_ui/src/LaunchTab.jsx
import React, { useState, useEffect, useRef } from 'react';
import TaskResultViewer from './components/TaskResultViewer';
import Ansi from 'ansi-to-react';

/**
 * The main component for the "Launch" tab.
 * This component provides the primary interface for users to initiate an agent
 * task. It includes a text area for the prompt, a dropdown to select a
 * configuration preset, and a button to launch the task. It also handles
 * loading states, error display, rendering the final task result, and
 * displaying a live log stream.
 * @returns {React.Component} The launch tab component.
 */
export default function LaunchTab() {
  const [prompt, setPrompt] = useState('');
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [response, setResponse] = useState(null);

  // Log stream state
  const [logs, setLogs] = useState([]);
  const [wsStatus, setWsStatus] = useState('Connecting...');
  const logsEndRef = useRef(null);
  const wsRef = useRef(null); 

  // Fetch available presets when the component mounts.
  useEffect(() => {
    fetch('/api/presets')
      .then(res => res.json())
      .then(data => {
        setPresets(data);
        const defaultPreset = data.find(p => p.id === 'default');
        if (defaultPreset) {
          setSelectedPreset(defaultPreset.id);
        } else if (data.length > 0) {
          setSelectedPreset(data[0].id); 
        }
      })
      .catch(err => console.error("Failed to fetch presets:", err));
  }, []);

  // Effect for WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        return;
      }

      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/logs`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws; 

      ws.onopen = () => {
        setWsStatus('Connected');
        setLogs(prev => [...prev, { level: 'info', msg: '--- Log stream connected. Waiting for task logs... ---', timestamp: Date.now() }]);
      };

      ws.onmessage = (event) => {
        setLogs(prev => [...prev, { level: 'log', msg: event.data, timestamp: Date.now() }]);
      };

      ws.onclose = () => {
        setWsStatus('Disconnected');
        setLogs(prev => [...prev, { level: 'error', msg: '--- Log stream lost. Attempting to reconnect... ---', timestamp: Date.now() }]);
        setTimeout(connectWebSocket, 5000); 
      };

      ws.onerror = (error) => {
        setWsStatus('Error');
        console.error('WebSocket Error:', error);
        setLogs(prev => [...prev, { level: 'error', msg: '--- Log stream connection error. ---', timestamp: Date.now() }]);
      };
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.onclose = null; 
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []); 

  // Effect to scroll to the bottom whenever new logs arrive.
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);


  const launch = async () => {
    setIsLoading(true);
    setError('');
    setResponse(null);
    // Clear logs for the new task, but keep connection message
    setLogs(prevLogs => prevLogs.filter(log => log.msg.includes('Log stream connected') || log.msg.includes('reconnect')) 
                       .concat([{ level: 'info', msg: `--- Starting new task: ${prompt.substring(0,30)}... ---`, timestamp: Date.now() }])
    );


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

  const selectedPresetInfo = presets.find(p => p.id === selectedPreset);

  const getWsStatusColor = () => {
    switch (wsStatus) {
      case 'Connected': return 'lightgreen';
      case 'Connecting...': return 'orange';
      default: return '#ff6666';
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
      <div>
        <h2>🚀 Launch Agent</h2>
        <p style={{ opacity: 0.8, marginTop: '-0.5rem', marginBottom: '1.5rem' }}>
          This is the primary control panel for executing agent tasks. Enter a high-level goal, select an agent behavior preset, and click "Launch Task".
        </p>

        <label htmlFor="preset">Agent Behavior Preset:</label>
        <select id="preset" value={selectedPreset} onChange={e => setSelectedPreset(e.target.value)}
          style={{ marginBottom: '0.5rem', display: 'block', width: '100%' }} disabled={isLoading}>
          {presets.length === 0 && <option value="">Loading presets...</option>}
          {presets.map((p) => (<option key={p.id} value={p.id}>{p.name}</option>))}
        </select>
        
        {selectedPresetInfo && (
          <p style={{ fontSize: '0.9em', opacity: 0.7, margin: '0 0 1rem 0' }}>
            {selectedPresetInfo.description}
          </p>
        )}

        <label htmlFor="prompt">Task Prompt:</label>
        <textarea id="prompt" placeholder="Enter your task prompt here..." rows="4" value={prompt}
          onChange={e => setPrompt(e.target.value)} style={{ width: '100%', marginBottom: '1rem' }} disabled={isLoading} />

        <button onClick={launch} disabled={isLoading || !prompt || !selectedPreset}>
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
                    onClick={() => setLogs(prevLogs => prevLogs.filter(log => log.msg.includes('Log stream connected')|| log.msg.includes('reconnect')))} 
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
            height: 'calc(100vh - 220px)', 
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