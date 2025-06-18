// aegis/web/react_ui/src/DashboardTab.jsx
import React, { useState, useEffect } from 'react';

/**
 * A small component to render each task item in the recent activity list.
 * @param {object} props - The component props.
 * @param {object} props.task - The task metadata object.
 * @returns {React.Component} A single row in the task list.
 */
const TaskItem = ({ task }) => {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', borderBottom: '1px solid var(--border)' }}>
      <code style={{ fontFamily: 'monospace' }}>{task.task_id}</code>
      <span>{new Date(task.timestamp * 1000).toLocaleString()}</span>
      <div>
        {task.has_summary ? '✅' : '❌'} Summary
      </div>
    </div>
  );
};

/**
 * A component to display the system status by fetching from the `/api/status` endpoint.
 * @returns {React.Component} The system status panel.
 */
const StatusPanel = () => {
    const [status, setStatus] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        fetch('/api/status')
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error ${res.status}`);
                return res.json();
            })
            .then(setStatus)
            .catch(err => {
                console.error("Failed to fetch status:", err);
                setError(err.message);
                setStatus({}); 
            });
    }, []);

    if (error) return <p style={{color: 'var(--accent-error)'}}>Could not load system status: {error}</p>;
    if (!status) return <p>Loading system status...</p>;
    if (Object.keys(status).length === 0 && !error) return <p>No system status data available.</p>

    return (
        <div style={{ border: '1px solid var(--border)', borderRadius: '6px', padding: '1rem' }}>
            {Object.entries(status).map(([key, value]) => (
                <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                    <strong>{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}:</strong>
                    <code>{String(value)}</code>
                </div>
            ))}
        </div>
    );
};

/**
 * The main component for the "Dashboard" tab.
 * It provides an at-a-glance view of the system's recent activity and its current
 * status. It serves as the main landing page for the UI.
 * @returns {React.Component} The dashboard component.
 */
export default function DashboardTab() {
  const [tasks, setTasks] = useState([]);
  const [tasksError, setTasksError] = useState(null);

  const fetchTasks = () => {
    setTasksError(null);
    fetch('/api/artifacts')
      .then(res => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        return res.json();
      })
      .then(data => setTasks(data.slice(0, 10))) 
      .catch(err => {
          console.error("Failed to fetch tasks:", err);
          setTasksError(err.message);
      });
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  return (
    <div>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
        <h2 style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem', marginBottom: '1rem', flexGrow: 1 }}>📈 Dashboard Overview</h2>
        <button onClick={fetchTasks} style={{marginLeft: '1rem'}}>Refresh Activities</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.5fr) minmax(0, 1fr)', gap: '2rem' }}>
          <div>
              <h3>Recent Activity</h3>
              <div style={{ border: '1px solid var(--border)', borderRadius: '6px', background: 'var(--input-bg)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', padding: '0.5rem', borderBottom: '1px solid var(--border)' }}>
                      <span>Task ID</span>
                      <span>Timestamp</span>
                      <span>Artifacts</span>
                  </div>
                  {tasksError && <p style={{ padding: '1rem', textAlign: 'center', color: 'var(--accent-error)' }}>Error loading tasks: {tasksError}</p>}
                  {!tasksError && tasks.length > 0 && (
                      tasks.map(task => <TaskItem key={task.task_id} task={task} />)
                  )}
                  {!tasksError && tasks.length === 0 && (
                      <p style={{ padding: '1rem', textAlign: 'center' }}>No recent tasks found.</p>
                  )}
              </div>
          </div>
          <div>
              <h3>ℹ️ System Status</h3>
              <StatusPanel />
          </div>
      </div>
    </div>
  );
}