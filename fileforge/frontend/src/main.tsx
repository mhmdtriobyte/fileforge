/**
 * main.tsx - React Application Entry Point
 *
 * Initializes the React application with StrictMode for
 * additional development checks and warnings.
 */

import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles/globals.css';

// Get the root element from the DOM
const rootElement = document.getElementById('root');

if (!rootElement) {
  throw new Error(
    'Failed to find the root element. Make sure there is a <div id="root"></div> in your HTML.'
  );
}

// Create React root and render the application
ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
