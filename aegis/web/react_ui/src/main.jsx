// aegis/web/react_ui/src/main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './themes.css'; // Import the new theme file

/**
 * The main entry point for the React application.
 * It renders the root `App` component into the DOM.
 */
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);