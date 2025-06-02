import React, { useEffect, useRef, useState } from 'react';

export default function LogViewer() {
  const [logs, setLogs] = useState([]);
  const logBoxRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://${window.location.host}/ws/logs`);
    ws.onmessage = (event) => {
      setLogs((prevLogs) => [...prevLogs, event.data]);
    };
    ws.onerror = (error) => {
      setLogs((prevLogs) => [...prevLogs, `❌ WebSocket error: ${error.message}`]);
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    if (logBoxRef.current) {
      logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="mb-6">
      <h2 className="text-xl font-semibold mb-2">📡 Live Agent Logs</h2>
      <div
        ref={logBoxRef}
        className="bg-black text-white border p-3 rounded h-48 overflow-y-scroll font-mono text-sm"
      >
        {logs.length === 0 ? (
          <em>Waiting for logs...</em>
        ) : (
          logs.map((line, idx) => <div key={idx}>{line}</div>)
        )}
      </div>
    </div>
  );
}
