import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App.jsx';
import { IDTCCProvider } from './context/IDTCCContext.jsx';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <IDTCCProvider>
      <App />
    </IDTCCProvider>
  </React.StrictMode>,
);
