// aegis/web/react_ui/src/ExecutionGraphViewer.jsx
import React, { useState, useEffect, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

const getNodeColor = (status) => {
  switch (status) {
    case 'success':
      return '#28a745'; // Green for success
    case 'failure':
      return '#dc3545'; // Red for failure
    default:
      return '#6c757d'; // Grey for unknown
  }
};

const transformProvenanceToFlow = (provenanceData) => {
  if (!provenanceData || !provenanceData.events) {
    return { nodes: [], edges: [] };
  }

  const initialNodes = provenanceData.events.map((event, index) => {
    const nodeId = `step-${event.step}`;
    const toolArgs = JSON.stringify(event.tool_args, null, 2);
    const observation =
      event.observation.length > 200
        ? `${event.observation.substring(0, 200)}...`
        : event.observation;

    return {
      id: nodeId,
      data: {
        label: (
          <div style={{ padding: '10px', minWidth: '250px' }}>
            <strong>Step {event.step}: {event.tool_name}</strong>
            <hr style={{ margin: '5px 0', borderColor: 'var(--border)' }} />
            <div style={{ fontSize: '0.8em', opacity: 0.8 }}>
              <p><strong>🤔 Thought:</strong> {event.thought}</p>
              <p><strong>📥 Args:</strong> <code>{toolArgs}</code></p>
              <p><strong>🔍 Observation:</strong> {observation}</p>
            </div>
          </div>
        ),
      },
      position: { x: (index % 3) * 350, y: Math.floor(index / 3) * 250 },
      style: {
        background: 'var(--input-bg)',
        color: 'var(--fg)',
        border: `2px solid ${getNodeColor(event.status)}`,
        borderRadius: '8px',
      },
    };
  });

  const initialEdges = provenanceData.events
    .slice(0, -1)
    .map((event) => ({
      id: `e-step-${event.step}-to-step-${event.step + 1}`,
      source: `step-${event.step}`,
      target: `step-${event.step + 1}`,
      animated: true,
      style: { stroke: 'var(--accent)' },
    }));

  return { nodes: initialNodes, edges: initialEdges };
};

export default function ExecutionGraphViewer({ taskId }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (taskId) {
      setError('');
      fetch(`/api/artifacts/${taskId}/provenance`)
        .then((res) => {
          if (!res.ok) throw new Error(`Failed to fetch provenance for ${taskId}`);
          return res.json();
        })
        .then((data) => {
          const { nodes: newNodes, edges: newEdges } = transformProvenanceToFlow(data);
          setNodes(newNodes);
          setEdges(newEdges);
        })
        .catch((err) => {
          console.error(err);
          setError(err.message);
        });
    }
  }, [taskId, setNodes, setEdges]);

  if (error) {
    return <p style={{ color: '#ff6666' }}>Error: {error}</p>;
  }

  return (
    <div style={{ height: 'calc(100vh - 200px)', border: '1px solid var(--border)', borderRadius: '4px' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}