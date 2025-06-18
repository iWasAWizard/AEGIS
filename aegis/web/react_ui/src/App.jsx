// aegis/web/react_ui/src/App.jsx
import React, { useState, useEffect } from 'react';
import LaunchTab from './LaunchTab';
import PresetsTab from './PresetsTab';
import ArtifactsTab from './ArtifactsTab';
import ReportsTab from './ReportsTab';
import ToolsTab from './ToolsTab'; // Corrected import path
import LogStreamTab from './LogStreamTab';
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
  const [theme, setTheme] = useState(() => localStorage.getItem('aegis-theme') || 'oled');

  // Effect to apply the selected theme to the body and persist it.
  useEffect(() => {
    document.body.className = `theme-${theme}`;
    localStorage.setItem('aegis-theme', theme);
  }, [theme]);

  // Effect to update the document title based on the active tab.
  useEffect(() => {
    const tabName = activeTab.charAt(0).toUpperCase() + activeTab.slice(1);
    document.title = `AEGIS | ${tabName}`;
  }, [activeTab]);

  /**
   * Renders the component for the currently active tab.
   * @returns {React.Component} The component for the active tab.
   */
  const renderTab = () => {
    switch (activeTab) {
      case 'dashboard':
        return <DashboardTab />;
      case 'launch':
        return <LaunchTab />;
      case 'presets':
        return <PresetsTab />;
      case 'artifacts':
        return <ArtifactsTab />;
      case 'reports':
        return <ReportsTab />;
      case 'tools':
        return <ToolsTab />;
      case 'logs':
        return <LogStreamTab />;
      case 'graph':
        return <GraphViewTab />;
      default:
        return <DashboardTab />;
    }
  };

  /**
   * A reusable navigation button component.
   * @param {object} props - The component props.
   * @param {string} props.tabId - The ID of the tab this button corresponds to.
   * @param {React.Node} props.children - The content of the button.
   * @returns {React.Component} A styled navigation button.
   */
  const NavButton = ({ tabId, children }) => (
    <button
      onClick={() => setActiveTab(tabId)}
      style={{
          background: activeTab === tabId ? 'var(--accent)' : 'var(--input-bg)',
          color: activeTab === tabId ? (theme.includes('light') ? '#fff' : 'var(--fg)') : 'var(--fg)',
          border: '1px solid var(--border)',
          padding: '0.5rem 1rem',
          cursor: 'pointer',
          borderRadius: '6px',
          fontWeight: activeTab === tabId ? 'bold' : 'normal',
      }}
    >
      {children}
    </button>
  );

  return (
    <div style={{ padding: '1rem', maxWidth: '1400px', margin: 'auto' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
        <h1 style={{ fontSize: '1.5em', margin: 0 }}>🛡️ AEGIS Dashboard</h1>

        <nav style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <NavButton tabId="dashboard">🏠 Dashboard</NavButton>
          <NavButton tabId="launch">🚀 Launch</NavButton>
          <NavButton tabId="logs">📡 Live Logs</NavButton>
          <NavButton tabId="graph">🗺️ Graph</NavButton>
          <NavButton tabId="tools">🧰 Tools</NavButton>
          <NavButton tabId="presets">🧠 Presets</NavButton>
          <NavButton tabId="artifacts">📦 Artifacts</NavButton>
        </nav>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <select value={theme} onChange={e => setTheme(e.target.value)} style={{ padding: '0.5rem' }}>
            <option value="oled">OLED</option>
            <option value="dracula">Dracula</option>
            <option value="hacker">Hacker</option>
            <option value="solarized-dark">Solarized Dark</option>
            <option value="light">Light</option>
            <option value="tango-dark">Tango Dark</option>
          </select>
        </div>
      </header>

      <main style={{ marginTop: '1rem' }}>
        {renderTab()}
      </main>
    </div>
  );
}