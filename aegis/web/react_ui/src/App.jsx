// aegis/web/react_ui/src/App.jsx
import React, { useState, useEffect, useRef } from 'react';
import LaunchTab from './LaunchTab';
import PresetsTab from './PresetsTab';
import ConfigEditorTab from './ConfigEditorTab';
import ArtifactsTab from './ArtifactsTab';
import ReportsTab from './ReportsTab';
import ToolsTab from './ToolsTab';
import GraphViewTab from './GraphViewTab';
import DashboardTab from './DashboardTab';

/**
 * The main application component that serves as the root of the UI.
 * It manages the active tab state, theme, and renders the main layout
 * including the header, navigation, and the content of the currently
 * selected tab.
 * @returns {React.Component} The main application component.
 */
export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [themes, setThemes] = useState([]);
  const [selectedTheme, setSelectedTheme] = useState(localStorage.getItem('aegis-theme') || 'oled');
  const [targetArtifactId, setTargetArtifactId] = useState(null);

  // --- Lifted state for ALL tabs ---

  // LaunchTab state
  const [prompt, setPrompt] = useState('');
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState('');
  const [backends, setBackends] = useState([]);
  const [selectedBackend, setSelectedBackend] = useState('');
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [response, setResponse] = useState(null);
  const [isSafeMode, setIsSafeMode] = useState(true);
  const [executionOverrides, setExecutionOverrides] = useState('');
  const [logs, setLogs] = useState([]);
  const [wsStatus, setWsStatus] = useState('Connecting...');
  const wsRef = useRef(null);

  // ConfigEditorTab state
  const [configFiles, setConfigFiles] = useState([]);
  const [currentFile, setCurrentFile] = useState('');
  const [fileContent, setFileContent] = useState('');
  const [fileStatus, setFileStatus] = useState('');

  // PresetsTab state
  const [presetList, setPresetList] = useState([]);
  const [currentPresetId, setCurrentPresetId] = useState(null);
  const [presetForm, setPresetForm] = useState({ id: '', name: '', description: '', config: '{}' });
  const [presetConfigError, setPresetConfigError] = useState('');


  // --- WebSocket Connection ---
  useEffect(() => {
    const connectWebSocket = () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/logs`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => setWsStatus('Connected');
      ws.onmessage = (event) => setLogs(prev => [...prev, { level: 'log', msg: event.data, timestamp: Date.now() }]);
      ws.onclose = () => { setWsStatus('Disconnected'); setTimeout(connectWebSocket, 5000); };
      ws.onerror = (error) => { setWsStatus('Error'); console.error('WebSocket Error:', error);};
    };
    connectWebSocket();
    return () => { if (wsRef.current) wsRef.current.close(); };
  }, []);

  // --- Data Fetching ---
  const fetchPresetsForEditor = () => {
    fetch('/api/presets')
      .then(res => res.json())
      .then(setPresetList)
      .catch(err => console.error("Failed to fetch presets for editor:", err));
  };

  useEffect(() => {
    fetchPresetsForEditor();

    fetch('/api/editor/files')
      .then(res => res.json())
      .then(setConfigFiles)
      .catch(err => console.error("Failed to fetch editable files:", err));

    const fetchData = (url, setter, defaultSetter, findDefault) => {
        fetch(url)
            .then(res => {
                if (!res.ok) throw new Error(`API fetch failed for ${url}`);
                return res.json();
            })
            .then(data => {
                if (Array.isArray(data)) {
                    setter(data);
                    if (data.length > 0) {
                        const defaultValue = findDefault(data);
                        defaultSetter(defaultValue);
                    }
                } else {
                    setter([]);
                }
            })
            .catch(err => console.error(err));
    };

    fetchData('/api/presets', setPresets, setSelectedPreset, data => {
        const d = data.find(p => p.id === 'default');
        return d ? d.id : data[0].id;
    });
    fetchData('/api/backends', setBackends, setSelectedBackend, data => {
        const d = data.find(b => b.profile_name === 'bend_local');
        return d ? d.profile_name : data[0].profile_name;
    });
    fetchData('/api/models', setModels, setSelectedModel, data => {
        const d = data.find(m => m.key === 'hermes');
        return d ? d.key : data[0].key;
    });
    fetch('/api/themes')
      .then(res => res.ok ? res.json() : ['oled'])
      .then(setThemes)
      .catch(err => { console.error("Failed to fetch themes:", err); setThemes(['oled']); });
  }, []);

  // --- UI Effects ---
  useEffect(() => {
    if (!selectedTheme) return;
    fetch(`/api/themes/${selectedTheme}`)
      .then(res => res.ok ? res.json() : Promise.reject(new Error(`Failed to load theme`)))
      .then(themeData => {
        if (themeData && themeData.properties) {
            for (const [key, value] of Object.entries(themeData.properties)) {
                document.documentElement.style.setProperty(`--${key}`, value);
            }
            localStorage.setItem('aegis-theme', selectedTheme);
        }
      })
      .catch(err => console.error(err));
  }, [selectedTheme]);

  useEffect(() => {
    document.title = `AEGIS | ${activeTab.charAt(0).toUpperCase() + activeTab.slice(1)}`;
    if (activeTab !== 'artifacts') {
      setTargetArtifactId(null);
    }
  }, [activeTab]);

  const navigateAndOpenArtifact = (taskId) => {
    setTargetArtifactId(taskId);
    setActiveTab('artifacts');
  };

  // --- Lifted Functions for Child Components ---
  const launch = async () => {
    if (isLoading || !prompt || !selectedPreset || !selectedBackend || !selectedModel) {
        return;
    }
    setIsLoading(true);
    setError('');
    setResponse(null);
    setLogs([]);

    const executionPayload = {
        backend_profile: selectedBackend,
        llm_model_name: selectedModel,
        safe_mode: isSafeMode,
    };

    if (executionOverrides.trim()) {
        try {
            const overrides = JSON.parse(executionOverrides);
            Object.assign(executionPayload, overrides);
        } catch (e) {
            setError('Invalid JSON in Execution Overrides. Please correct it and try again.');
            setIsLoading(false);
            return;
        }
    }

    const body = {
      task: { prompt },
      config: selectedPreset,
      execution: executionPayload
    };

    try {
      const res = await fetch('/api/launch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || `HTTP Error: ${res.status}`);
      setResponse(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadConfigFileContent = (path) => {
    if (!path) return;
    setFileStatus('Loading...');
    fetch(`/api/editor/file?path=${encodeURIComponent(path)}`)
      .then(res => res.json())
      .then(data => {
        setFileContent(data.content);
        setCurrentFile(data.path);
        setFileStatus('Loaded.');
      })
      .catch(err => {
        console.error(`Failed to fetch file content for ${path}:`, err);
        setFileStatus(`Error loading ${path}.`);
      });
  };

  const saveConfigFileContent = () => {
    if (!currentFile) return;
    setFileStatus('Saving...');
    fetch('/api/editor/file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: currentFile, content: fileContent })
    })
    .then(res => { if (!res.ok) throw new Error('Save failed'); return res.json(); })
    .then(() => {
      setFileStatus('Saved successfully!');
      setTimeout(() => setFileStatus(''), 2000);
    })
    .catch(err => {
      console.error(`Failed to save file ${currentFile}:`, err);
      setFileStatus(`Error saving ${currentFile}.`);
    });
  };

  const loadPreset = (p) => {
    setCurrentPresetId(p.id);
    fetch(`/api/presets/${p.id}`)
      .then(res => res.json())
      .then(data => {
        const { name, description, ...config } = data;
        setPresetForm({
          id: p.id,
          name: name || p.name,
          description: description || '',
          config: JSON.stringify(config, null, 2)
        });
        setPresetConfigError('');
      })
      .catch(err => console.error("Failed to load preset config:", err));
  };

  const savePreset = async () => {
    if (presetConfigError) {
      alert(`Cannot save: ${presetConfigError}`);
      return;
    }
    try {
      const configObject = JSON.parse(presetForm.config);
      const payload = {
        id: currentPresetId || presetForm.id || presetForm.name.toLowerCase().replace(/\s+/g, '_'),
        name: presetForm.name,
        description: presetForm.description,
        config: configObject,
      };
      await fetch('/api/presets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      alert("Preset saved.");
      fetchPresetsForEditor();
    } catch (e) {
        alert("Failed to save preset. Ensure config is valid JSON.");
    }
  };


  const renderTab = () => {
    switch (activeTab) {
      case 'dashboard': return <DashboardTab navigateAndOpenArtifact={navigateAndOpenArtifact} />;
      case 'launch':
        return <LaunchTab {...{ prompt, setPrompt, presets, selectedPreset, setSelectedPreset, backends, selectedBackend, setSelectedBackend, models, selectedModel, setSelectedModel, isLoading, error, response, launch, isSafeMode, setIsSafeMode, executionOverrides, setExecutionOverrides, logs, setLogs, wsStatus }} />;
      case 'presets':
        return <PresetsTab {...{ presetList, currentPresetId, presetForm, setPresetForm, presetConfigError, setPresetConfigError, loadPreset, savePreset, fetchPresets: fetchPresetsForEditor }} />;
      case 'editor':
        return <ConfigEditorTab {...{ files: configFiles, currentFile, content: fileContent, setContent: setFileContent, status: fileStatus, loadConfigFileContent, saveConfigFileContent }} />;
      case 'artifacts': return <ArtifactsTab targetArtifactId={targetArtifactId} />;
      case 'reports': return <ReportsTab />;
      case 'tools': return <ToolsTab />;
      case 'graph': return <GraphViewTab />;
      default: return <DashboardTab navigateAndOpenArtifact={navigateAndOpenArtifact} />;
    }
  };

  const NavButton = ({ tabId, children }) => ( <button onClick={() => setActiveTab(tabId)} style={{ background: activeTab === tabId ? 'var(--accent)' : 'var(--input-bg)', color: 'var(--fg)', border: '1px solid var(--border)', padding: '0.5rem 1rem', cursor: 'pointer', borderRadius: '6px', fontWeight: activeTab === tabId ? 'bold' : 'normal', }} > {children} </button> );

  return ( <div style={{ padding: '1rem', maxWidth: '1400px', margin: 'auto' }}> <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem', marginBottom: '1rem' }}> <h1 style={{ fontSize: '1.5em', margin: 0 }}>🛡️ AEGIS Dashboard</h1> <nav style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}> <NavButton tabId="dashboard">🏠 Dashboard</NavButton> <NavButton tabId="launch">🚀 Launch</NavButton> <NavButton tabId="graph">🗺️ Graph</NavButton> <NavButton tabId="tools">🧰 Tools</NavButton> <NavButton tabId="presets">🧠 Presets</NavButton> <NavButton tabId="editor">✏️ Config Editor</NavButton> <NavButton tabId="artifacts">📦 Artifacts</NavButton> </nav> <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}> <select value={selectedTheme} onChange={e => setSelectedTheme(e.target.value)} style={{ padding: '0.5rem' }}> {themes.length === 0 ? ( <option>Loading...</option> ) : ( themes.map(themeName => ( <option key={themeName} value={themeName}>{themeName.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</option> )) )} </select> </div> </header> <main style={{ marginTop: '1rem' }}> {renderTab()} </main> </div> );
}