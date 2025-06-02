import React, { useState, useEffect } from 'react';
import PromptForm from './components/PromptForm';
import LogViewer from './components/LogViewer';
import ReportList from './components/ReportList';
import ToolsTab from './components/ToolsTab';
import ConfigTab from './components/ConfigTab';
import ThemeSelector from './components/ThemeSelector';

function DashboardTab() {
  return (
    <div className="space-y-6">
      <PromptForm />
      <LogViewer />
      <ReportList />
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'oled');

  useEffect(() => {
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <div className={`min-h-screen font-sans px-6 py-4 theme-${theme}`}>
      <header className="flex justify-between items-center border-b border-gray-700 pb-2 mb-4">
        <h1 className="text-2xl font-bold">🧠 Agentic Agent Dashboard</h1>
        <div className="flex items-center gap-4">
          <nav className="space-x-4">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={\`px-3 py-1 rounded \${activeTab === 'dashboard' ? 'bg-blue-700' : 'bg-gray-800'}\`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('config')}
              className={\`px-3 py-1 rounded \${activeTab === 'config' ? 'bg-blue-700' : 'bg-gray-800'}\`}
            >
              Config
            </button>
            <button
              onClick={() => setActiveTab('tools')}
              className={\`px-3 py-1 rounded \${activeTab === 'tools' ? 'bg-blue-700' : 'bg-gray-800'}\`}
            >
              Tools
            </button>
          </nav>
          <ThemeSelector theme={theme} setTheme={setTheme} />
        </div>
      </header>

      <main className="max-w-4xl mx-auto">
        {activeTab === 'dashboard' && <DashboardTab />}
        {activeTab === 'config' && <ConfigTab />}
        {activeTab === 'tools' && <ToolsTab />}
      </main>
    </div>
  );
}
