// aegis/web/react_ui/src/ReportsTab.jsx
import React, { useEffect, useState } from 'react';

/**
 * The main component for the "Reports" tab.
 * This tab allows users to compare the final summaries of two different
 * task runs. It fetches a list of tasks that have summaries, allows the user
 * to select two, and then displays a unified diff of their content.
 * @returns {React.Component} The reports comparison tab component.
 */
export default function ReportsTab() {
  const [tasks, setTasks] = useState([]);
  const [selected, setSelected] = useState([]);
  const [diff, setDiff] = useState(null);
  const [error, setError] = useState('');

  // Fetch all tasks that have a summary artifact.
  useEffect(() => {
    fetch('/api/artifacts')
      .then(res => res.json())
      .then(data => setTasks(data.filter(t => t.has_summary)))
      .catch(err => console.error("Failed to fetch tasks:", err));
  }, []);

  /**
   * Toggles the selection of a task for comparison.
   * Allows up to two tasks to be selected.
   * @param {string} id - The task ID to select or deselect.
   */
  const toggleSelect = (id) => {
    setSelected(prev => {
      if (prev.includes(id)) {
        return prev.filter(item => item !== id);
      }
      if (prev.length < 2) {
        return [...prev, id];
      }
      return prev;
    });
  };

  /**
   * Handles the comparison by sending the two selected task IDs to the backend.
   */
  const handleCompare = async () => {
    if (selected.length !== 2) {
      setError("Please select exactly two reports to compare.");
      return;
    }
    setError('');
    setDiff(null);

    try {
      const res = await fetch('/api/compare_reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selected)
      });

      const json = await res.json();

      if (!res.ok) {
        throw new Error(json.detail || `Failed to compare reports: ${res.statusText}`);
      }

      setDiff(json.diff.join('\n') || 'No differences found.');
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div>
      <h2>📄 Compare Task Reports</h2>
      <p>Select two task reports from the list below to see a diff of their final summaries.</p>
      
      <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border)', padding: '0.5rem', marginBottom: '1rem' }}>
        {tasks.length === 0 && <p>No reports available.</p>}
        {tasks.map((task, i) => (
          <div key={i} style={{ padding: '0.25rem' }}>
            <input 
              type="checkbox" 
              id={`task-${task.task_id}`}
              onChange={() => toggleSelect(task.task_id)} 
              checked={selected.includes(task.task_id)}
              disabled={selected.length >= 2 && !selected.includes(task.task_id)}
            />
            <label htmlFor={`task-${task.task_id}`} style={{ marginLeft: '0.5rem', fontFamily: 'monospace' }}>
              {task.task_id}
            </label>
          </div>
        ))}
      </div>

      <button onClick={handleCompare} disabled={selected.length !== 2}>
        Compare Selected ({selected.length}/2)
      </button>

      {error && <p style={{ color: '#ff6666', marginTop: '1rem' }}>Error: {error}</p>}

      {diff !== null && (
        <div style={{ marginTop: '2rem' }}>
          <h3>🔍 Comparison Result</h3>
          <pre style={{
            border: '1px dashed var(--border)',
            padding: '1rem',
            whiteSpace: 'pre-wrap',
            backgroundColor: '#111',
            color: 'var(--fg)',
            fontFamily: 'monospace',
            fontSize: '0.85em',
            maxHeight: '500px',
            overflowY: 'auto'
          }}>
            {diff}
          </pre>
        </div>
      )}
    </div>
  );
}