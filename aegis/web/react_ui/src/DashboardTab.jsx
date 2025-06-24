// aegis/web/react_ui/src/DashboardTab.jsx
import React, { useState, useEffect } from 'react';

/**
 * A small component to render each task item in the recent activity list.
 * @param {object} props - The component props.
 * @param {object} props.task - The task metadata object.
 * @param {function} props.onClick - Function to call when the item is clicked.
 * @returns {React.Component} A single row in the task list.
 */
const TaskItem = ({ task, onClick }) => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        padding: '0.5rem',
        borderBottom: '1px solid var(--border)',
        cursor: 'pointer' // Make it look clickable
      }}
      onClick={onClick}
      title={`Click to view artifacts for ${task.task_id}`} // Tooltip
    >
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

    useEffect(() => {
        fetch('/api/status')
            .then(res => res.json())
            .then(setStatus)
            .catch(err => console.error("Failed to fetch status:", err));
    }, []);

    if (!status) return <p>Loading status...</p>;

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
 * @param {object} props - The component props.
 * @param {function} props.navigateAndOpenArtifact - Function to navigate to Artifacts tab.
 * @returns {React.Component} The dashboard component.
 */
export default function DashboardTab({ navigateAndOpenArtifact }) {
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    fetch('/api/artifacts')
      .then(res => res.json())
      .then(data => setTasks(data.slice(0, 10))) // Show top 10 most recent
      .catch(err => console.error("Failed to fetch tasks:", err));
  }, []);

  return (
    <div>
        <h2 style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem' }}>📈 Recent Activity</h2>
        <div style={{ border: '1px solid var(--border)', borderRadius: '6px', background: 'var(--input-bg)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', borderBottom: '1px solid var(--border)' }}>
                <strong>Task ID</strong>
                <strong>Timestamp</strong>
                <strong>Artifacts</strong>
            </div>
            {tasks.length > 0 ? (
                tasks.map(task =>
                  <TaskItem
                    key={task.task_id}
                    task={task}
                    onClick={() => navigateAndOpenArtifact(task.task_id)}
                  />)
            ) : (
                <p style={{ padding: '1rem', textAlign: 'center' }}>No recent tasks found.</p>
            )}
        </div>

        <h2 style={{ borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem', marginTop: '2rem' }}>ℹ️ System Status</h2>
        <StatusPanel />
    </div>
  );
}