// aegis/web/react_ui/src/ArtifactsTab.jsx
import React, { useEffect, useState, useRef } from 'react';
import { Accordion, AccordionItem } from '@szhsin/react-accordion';
import ReactMarkdown from 'react-markdown';

/**
 * A component to view the details of a single task's artifacts, fetched on demand.
 * It displays a summary and a provenance tab for the selected task.
 * @param {object} props - The component props.
 * @param {object} props.task - The metadata object for the task.
 * @returns {React.Component} The artifact viewer component.
 */
const ArtifactViewer = ({ task }) => {
    const [summary, setSummary] = useState('');
    const [provenance, setProvenance] = useState(null);
    const [activeTab, setActiveTab] = useState('summary');
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            setIsLoading(true);
            try {
                if (task.has_summary) {
                    const summaryRes = await fetch(`/api/artifacts/${task.task_id}/summary`);
                    setSummary(await summaryRes.text());
                }
                if (task.has_provenance) {
                    const provRes = await fetch(`/api/artifacts/${task.task_id}/provenance`);
                    setProvenance(await provRes.json());
                }
            } catch (err) {
                console.error("Failed to fetch artifact details:", err);
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, [task.task_id, task.has_summary, task.has_provenance]);

    if (isLoading) return <p>Loading artifacts...</p>;

    return (
        <div style={{ padding: '1rem' }}>
            <div style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border)' }}>
                <button onClick={() => setActiveTab('summary')} style={{ background: activeTab === 'summary' ? 'var(--accent)' : 'none', border: 'none', padding: '0.5rem 1rem' }}>Summary</button>
                <button onClick={() => setActiveTab('provenance')} style={{ background: activeTab === 'provenance' ? 'var(--accent)' : 'none', border: 'none', padding: '0.5rem 1rem' }}>Provenance</button>
            </div>
            {activeTab === 'summary' && (
                <div style={{ background: '#1a192b', padding: '1rem', borderRadius: '4px', border: '1px solid var(--border)'}}>
                    <ReactMarkdown>{summary || 'No summary available.'}</ReactMarkdown>
                </div>
            )}
            {activeTab === 'provenance' && (
                <pre style={{ background: '#000', padding: '1rem', overflowX: 'auto', whiteSpace: 'pre-wrap', maxHeight: '500px' }}>
                    {provenance ? JSON.stringify(provenance, null, 2) : 'No provenance data available.'}
                </pre>
            )}
        </div>
    );
};

/**
 * The main component for the "Artifacts" tab.
 * It fetches and displays a list of all completed tasks that have generated artifacts.
 * Each task is rendered as a collapsible accordion item, which reveals the
 * `ArtifactViewer` component when clicked.
 * @param {object} props - The component props.
 * @param {string|null} props.targetArtifactId - The ID of the artifact to initially open.
 * @param {function} props.clearTargetArtifactId - Function to clear the target artifact ID.
 * @returns {React.Component} The artifacts tab component.
 */
export default function ArtifactsTab({ targetArtifactId, clearTargetArtifactId }) {
  const [artifacts, setArtifacts] = useState([]);
  const accordionRef = useRef(null); // Ref for the accordion container for scrolling

  const fetchArtifacts = () => {
    fetch('/api/artifacts')
      .then(res => res.json())
      .then(setArtifacts)
      .catch(err => console.error("Failed to fetch artifacts:", err));
  };

  useEffect(() => {
    fetchArtifacts();
  }, []);

  // Effect to handle scrolling to and clearing the target artifact ID
  useEffect(() => {
    if (targetArtifactId && artifacts.length > 0) {
      const itemElement = document.getElementById(`accordion-item-${targetArtifactId}`);
      if (itemElement) {
        // Slight delay to ensure the item is rendered and accordion can process initialEntered
        setTimeout(() => {
            itemElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 100);
      }
      // Clear the target ID after attempting to scroll and expand,
      // so it doesn't re-trigger on subsequent renders without new navigation.
      const clearTimer = setTimeout(() => {
        clearTargetArtifactId();
      }, 500); // Longer delay to ensure animation completes if any
      return () => clearTimeout(clearTimer);
    }
  }, [targetArtifactId, clearTargetArtifactId, artifacts]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>📦 Task Artifacts</h2>
        <button onClick={fetchArtifacts}>Refresh List</button>
      </div>
      <p style={{ opacity: 0.8, marginTop: '-0.5rem', marginBottom: '1.5rem' }}>
        Browse the results of previously completed agent tasks. Each entry represents a single task run. Expand an item to view its final summary report and the detailed, machine-readable provenance log.
      </p>

      {artifacts.length === 0 && <p>No artifacts found. Run an agent task to generate some.</p>}

      <Accordion
        transition
        timeout={200}
        ref={accordionRef}
        // By using targetArtifactId in the key, we can force Accordion to re-evaluate initialEntered states
        // when navigating to this tab with a specific target.
        key={targetArtifactId || 'accordion-default'}
      >
        {artifacts.map((task, idx) => (
          <AccordionItem
            key={task.task_id} // Use task_id as the key for the item itself for stability
            itemKey={task.task_id} // This key is used by Accordion for managing state
            initialEntered={task.task_id === targetArtifactId} // Set initialEntered based on target
            header={
              <div style={{ width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <code style={{ fontFamily: 'var(--font-mono)' }}>{task.task_id}</code>
                <span>{new Date(task.timestamp * 1000).toLocaleString()}</span>
              </div>
            }
            // Add an id to the wrapper div of AccordionItem for scrolling
            style={{ border: '1px solid var(--border)', borderRadius: '6px', marginBottom: '0.5rem' }}
            id={`accordion-item-${task.task_id}`} // ID for scrolling
            buttonProps={{ style: { width: '100%', textAlign: 'left', padding: '0.75rem', background: 'var(--input-bg)', color: 'var(--fg)', cursor: 'pointer', border: 'none' } }}
            contentProps={{ style: { background: '#111' } }}
          >
            <ArtifactViewer task={task} />
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  );
}