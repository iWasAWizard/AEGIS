// aegis/web/react_ui/src/LogStreamTab.jsx
import React, { useState, useEffect, useRef } from 'react';
import Ansi from 'ansi-to-react';

/**
 * A component that establishes a WebSocket connection to the backend and
 * displays a live stream of logs from the agent.
 * @returns {React.Component} The live log stream component.
 */
export default function LogStreamTab() {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('Connecting...');
  const logsEndRef = useRef(null);

  /**
   * Scrolls the log container to the bottom.
   */
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Effect to set up and manage the WebSocket connection.
  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/logs`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setStatus('Connected');
      setLogs(prev => [...prev, { level: 'info', msg: '--- Connection established. Waiting for logs... ---' }]);
    };

    ws.onmessage = (event) => {
      // The backend sends ANSI-colored strings, which `ansi-to-react` can render.
      setLogs(prev => [...prev, { level: 'log', msg: event.data }]);
    };

    ws.onclose = () => {
      setStatus('Disconnected');
      setLogs(prev => [...prev, { level: 'error', msg: '--- Connection lost. Please refresh the page. ---' }]);
    };

    ws.onerror = (error) => {
      setStatus('Error');
      console.error('WebSocket Error:', error);
      setLogs(prev => [...prev, { level: 'error', msg: '--- A connection error occurred. ---' }]);
    };

    // Cleanup function to close the WebSocket connection when the component unmounts.
    return () => {
      ws.close();
    };
  }, []); // The empty dependency array ensures this effect runs only once on mount.

  // Effect to scroll to the bottom whenever new logs arrive.
  useEffect(() => {
    scrollToBottom();
  }, [logs]);

  /**
   * Determines the color for the status indicator.
   * @returns {string} A color string.
   */
  const getStatusColor = () => {
    switch (status) {
      case 'Connected': return 'lightgreen';
      case 'Connecting...': return 'orange';
      default: return '#ff6666'; // For Disconnected or Error
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.2em', margin: 0 }}>📡 Live Log Stream</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span style={{ color: getStatusColor() }}>● {status}</span>
            <button onClick={() => setLogs([])}>Clear Logs</button>
        </div>
      </div>
      <pre style={{
        background: '#0a0a0a',
        color: 'var(--fg)',
        fontFamily: 'monospace',
        fontSize: '0.85em',
        padding: '1rem',
        height: '65vh',
        overflowY: 'auto',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        border: '1px solid var(--border)',
        borderRadius: '4px'
      }}>
        {logs.map((log, index) => (
          <div key={index}>
            <Ansi>{log.msg}</Ansi>
          </div>
        ))}
        <div ref={logsEndRef} />
      </pre>
    </div>
  );
}