// aegis/web/react_ui/src/components/TaskResultViewer.jsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { Accordion, AccordionItem } from '@szhsin/react-accordion';

/**
 * A reusable component for displaying the results of a completed agent task.
 * It shows the final summary and a collapsible, step-by-step history of the
 * agent's execution, including its thoughts, actions, and observations.
 * @param {object} props - The component props.
 * @param {object} props.taskResult - The final task result object from the API.
 * @returns {React.Component} The task result viewer component.
 */
export default function TaskResultViewer({ taskResult }) {
  if (!taskResult) {
    return <p>No result data available.</p>;
  }

  return (
    <div style={{ marginTop: '1rem' }}>
      <h3>Task Result: {taskResult.task_id}</h3>

      <h4>Summary</h4>
      <div style={{ background: 'var(--input-bg)', padding: '1rem', borderRadius: '6px', border: '1px solid var(--border)', whiteSpace: 'pre-wrap' }}>
        <ReactMarkdown>{taskResult.summary || "No summary was generated."}</ReactMarkdown>
      </div>

      <h4 style={{ marginTop: '1.5rem' }}>Execution History</h4>
      <Accordion transition timeout={200}>
        {(taskResult.history || []).map((step, index) => (
          <AccordionItem
            key={index}
            header={
              <div style={{ width: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <strong>Step {index + 1}:</strong> {step.tool_name}
                <code style={{ fontSize: '0.8em', marginLeft: '1rem', opacity: 0.7 }}>
                  {JSON.stringify(step.tool_args)}
                </code>
              </div>
            }
            style={{ border: '1px solid var(--border)', borderRadius: '6px', marginBottom: '0.5rem' }}
            buttonProps={{ style: { width: '100%', textAlign: 'left', padding: '0.75rem', background: 'var(--input-bg)', color: 'var(--fg)', cursor: 'pointer', border: 'none' } }}
            contentProps={{ style: { padding: '1rem', background: 'var(--bg)' } }}
          >
            <p><strong>🤔 Thought:</strong> {step.thought}</p>
            <strong>🔍 Observation:</strong>
            <pre style={{ background: '#000', color: '#eee', padding: '0.5rem', marginTop: '0.5rem', overflowX: 'auto', whiteSpace: 'pre-wrap', borderRadius: '4px' }}>
              {step.tool_output}
            </pre>
          </AccordionItem>
        ))}
        {(!taskResult.history || taskResult.history.length === 0) && <p>No execution steps were recorded.</p>}
      </Accordion>
    </div>
  );
}