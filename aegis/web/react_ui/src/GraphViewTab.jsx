// aegis/web/react_ui/src/GraphViewTab.jsx
import React, { useState, useEffect, useCallback } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

/**
 * Determines the color for a node based on its type.
 * @param {object} node - The React Flow node object.
 * @returns {string} A hex color code.
 */
const nodeColor = (node) => {
    switch (node.type) {
      case 'input':
        return '#0041d0';
      case 'output':
        return '#ff0072';
      default:
        return '#1a192b';
    }
  };

/**
 * A component for visualizing agent graph configurations using React Flow.
 * It fetches presets and renders them as interactive graphs, showing the
 * nodes, edges, and conditional logic that define an agent's behavior.
 * @returns {React.Component} The graph visualizer component.
 */
const GraphViewTab = () => {
    const [presets, setPresets] = useState([]);
    const [selectedPreset, setSelectedPreset] = useState('');
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // Fetch the list of available presets on component mount.
    useEffect(() => {
        fetch('/api/graphs/')
            .then((res) => res.json())
            .then((data) => {
                const presetOptions = data.map(p => ({ id: p, name: p.replace('.yaml', '') }));
                setPresets(presetOptions);
                if (presetOptions.length > 0) {
                    setSelectedPreset(presetOptions[0].id);
                }
            })
            .catch(err => console.error("Failed to fetch presets:", err));
    }, []);

    /**
     * Transforms agent graph configuration data from the API into a format
     * that React Flow can render.
     * @param {object} presetData - The raw agent config object from the API.
     */
    const transformDataToFlow = useCallback((presetData) => {
        if (!presetData || !presetData.nodes) {
            setNodes([]);
            setEdges([]);
            return;
        }

        const initialNodes = presetData.nodes.map((node, index) => ({
            id: node.id,
            data: { label: `${node.id}\n(${node.tool})` },
            position: { x: (index % 4) * 250, y: Math.floor(index / 4) * 150 },
            type: node.id === presetData.entrypoint ? 'input' : 'default',
            style: {
                background: node.id === presetData.entrypoint ? '#28a745' : '#333',
                color: '#fff',
                border: '1px solid #555',
            },
        }));

        const initialEdges = (presetData.edges || []).map(([source, target]) => ({
            id: `e-${source}-${target}`,
            source,
            target,
            animated: true,
        }));

        // Add conditional edges if they are defined in the preset.
        if (presetData.condition_node && presetData.condition_map) {
            const source = presetData.condition_node;
            Object.entries(presetData.condition_map).forEach(([label, target]) => {
                initialEdges.push({
                    id: `ce-${source}-${target}-${label}`,
                    source,
                    target,
                    label,
                    type: 'smoothstep',
                    style: { stroke: '#f6ad55' },
                    markerEnd: { type: 'arrowclosed' },
                });
            });
        }

        setNodes(initialNodes);
        setEdges(initialEdges);
    }, [setNodes, setEdges]);


    // Fetch the full config for the selected preset whenever the selection changes.
    useEffect(() => {
        if (selectedPreset) {
            fetch(`/api/graphs/view?name=${selectedPreset}`)
                .then((res) => res.json())
                .then(transformDataToFlow)
                .catch(err => console.error(`Failed to fetch preset ${selectedPreset}:`, err));
        } else {
            setNodes([]);
            setEdges([]);
        }
    }, [selectedPreset, transformDataToFlow]);

    return (
        <div>
            <h2 style={{ fontSize: '1.2em', marginBottom: '1rem' }}>🗺️ Agent Graph Visualizer</h2>
            <p style={{ opacity: 0.8, marginTop: '-0.5rem', marginBottom: '1.5rem' }}>
              This tab renders a visual representation of an agent's behavior preset. Each graph shows the nodes (steps) and edges (transitions) that define how the agent operates. Use the dropdown to explore different agent workflows.
            </p>
            <div style={{ marginBottom: '1rem' }}>
                <label htmlFor="preset-selector" style={{ marginRight: '0.5rem' }}>Select a Preset to View:</label>
                <select
                    id="preset-selector"
                    value={selectedPreset}
                    onChange={(e) => setSelectedPreset(e.target.value)}
                    style={{ padding: '0.5rem' }}
                >
                    <option value="">-- Choose a Graph --</option>
                    {presets.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                </select>
            </div>
            <div style={{ height: '70vh', border: '1px solid var(--border)', borderRadius: '4px' }}>
                <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    fitView
                >
                    <Background />
                    <Controls />
                    <MiniMap nodeColor={nodeColor} nodeStrokeWidth={3} zoomable pannable />
                </ReactFlow>
            </div>
        </div>
    );
};

export default GraphViewTab;