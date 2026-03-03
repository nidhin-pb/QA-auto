import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import LoginConfig from './components/LoginConfig';
import AttachmentConfig from './components/AttachmentConfig';
import ExcelSuiteConfig from './components/ExcelSuiteConfig';
import LiveView from './components/LiveView';
import TestDashboard from './components/TestDashboard';
import ReportView from './components/ReportView';

const API_BASE = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

function App() {
  const [activeTab, setActiveTab] = useState('config');
  const [status, setStatus] = useState({ status: 'idle', message: 'Not connected' });
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenarios, setSelectedScenarios] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [logs, setLogs] = useState([]);
  const [testResults, setTestResults] = useState([]);
  const [progress, setProgress] = useState({ current: 0, total: 0, percentage: 0, current_test: '' });
  const [reports, setReports] = useState([]);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const wsRef = useRef(null);
  const chatEndRef = useRef(null);
  const logEndRef = useRef(null);

  // Fetch scenarios on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/scenarios`)
      .then(res => res.json())
      .then(data => {
        setScenarios(data.scenarios || []);
        setSelectedScenarios(data.scenarios?.map(s => s.id) || []);
      })
      .catch(err => console.error('Failed to fetch scenarios:', err));
  }, []);

  // WebSocket connection
  useEffect(() => {
    let ws = null;
    let pingInterval = null;
    let reconnectTimeout = null;

    const connectWs = () => {
      try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
          console.log('WebSocket connected');
          pingInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ type: 'ping' }));
            }
          }, 30000);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);

            switch (data.type) {
              case 'log':
                setLogs(prev => [...prev.slice(-500), {
                  level: data.level,
                  message: data.message,
                  time: new Date().toLocaleTimeString()
                }]);
                break;

              case 'chat':
                setChatMessages(prev => [...prev.slice(-200), {
                  sender: data.sender,
                  message: data.message,
                  screenshot: data.screenshot,
                  time: new Date().toLocaleTimeString()
                }]);
                break;

              case 'test_result':
                setTestResults(prev => {
                  const existing = prev.findIndex(r => r.test_id === data.test_id);
                  if (existing >= 0) {
                    const updated = [...prev];
                    updated[existing] = data;
                    return updated;
                  }
                  return [...prev, data];
                });
                break;

              case 'progress':
                setProgress(data);
                break;

              case 'status':
                setStatus(data);
                if (data.status === 'ready') setIsInitialized(true);
                if (data.status === 'running') setIsRunning(true);
                if (data.status === 'completed' || data.status === 'error') {
                  setIsRunning(false);
                  fetchReports();
                }
                break;

              case 'pong':
                break;

              default:
                break;
            }
          } catch (err) {
            console.error('WS message parse error:', err);
          }
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          if (pingInterval) clearInterval(pingInterval);
          reconnectTimeout = setTimeout(connectWs, 3000);
        };

        ws.onerror = (err) => {
          console.error('WebSocket error');
        };

        wsRef.current = ws;
      } catch (err) {
        console.error('WS connect error:', err);
        reconnectTimeout = setTimeout(connectWs, 3000);
      }
    };

    connectWs();

    return () => {
      if (pingInterval) clearInterval(pingInterval);
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null; // Prevent reconnect on unmount
        ws.close();
      }
    };
  }, []);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const fetchReports = useCallback(() => {
    fetch(`${API_BASE}/api/reports`)
      .then(res => res.json())
      .then(data => setReports(data.reports || []))
      .catch(err => console.error('Failed to fetch reports:', err));
  }, []);

  const handleInitialize = async (config) => {
    try {
      setStatus({ status: 'initializing', message: 'Connecting to Teams...' });
      setLogs([]);
      setChatMessages([]);

      const res = await fetch(`${API_BASE}/api/initialize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to initialize');
    } catch (err) {
      setStatus({ status: 'error', message: err.message });
    }
  };

  const handleRunTests = async () => {
    try {
      setChatMessages([]);
      setTestResults([]);
      setLogs([]);

      const res = await fetch(`${API_BASE}/api/run-tests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          scenario_ids: selectedScenarios.length > 0 ? selectedScenarios : null
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start tests');
      setActiveTab('live');
    } catch (err) {
      setStatus({ status: 'error', message: err.message });
    }
  };

  const handleRunExcelSuite = async () => {
    try {
      setChatMessages([]);
      setTestResults([]);
      setLogs([]);

      const res = await fetch(`${API_BASE}/api/run-excel-suite`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to start Excel suite');
      setActiveTab('live');
    } catch (err) {
      setStatus({ status: 'error', message: err.message });
    }
  };

  const handleStopTests = async () => {
    try {
      await fetch(`${API_BASE}/api/stop-tests`, { method: 'POST' });
    } catch (err) {
      console.error('Stop failed:', err);
    }
  };

  const handleCleanup = async () => {
    try {
      await fetch(`${API_BASE}/api/cleanup`, { method: 'POST' });
      setIsInitialized(false);
      setIsRunning(false);
      setStatus({ status: 'idle', message: 'Cleaned up' });
    } catch (err) {
      console.error('Cleanup failed:', err);
    }
  };

  const toggleScenario = (id) => {
    setSelectedScenarios(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const selectAll = () => setSelectedScenarios(scenarios.map(s => s.id));
  const selectNone = () => setSelectedScenarios([]);

  const getStatusClass = () => {
    const s = status.status;
    if (['ready', 'completed'].includes(s)) return 'ready';
    if (['running', 'initializing', 'logging_in', 'opening_cva', 'generating_report'].includes(s)) return 'running';
    if (s === 'error') return 'error';
    return 'idle';
  };

  const passedCount = testResults.filter(r => r.status === 'passed').length;
  const failedCount = testResults.filter(r => r.status === 'failed').length;
  const errorCount = testResults.filter(r => r.status === 'error').length;

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <div className="header-logo">
            <i className="fas fa-robot"></i>
          </div>
          <div>
            <div className="header-title">CVA QA Testing Automation</div>
            <div className="header-subtitle">Intelligent Testing for Chat Virtual Agent</div>
          </div>
        </div>
        <div className="header-right">
          <div className={`status-badge ${getStatusClass()}`}>
            <span className="status-dot"></span>
            {status.status.toUpperCase()}: {(status.message || '').substring(0, 60)}
          </div>
          {isRunning && (
            <button className="btn btn-danger btn-sm" onClick={handleStopTests}>
              <i className="fas fa-stop"></i> Stop
            </button>
          )}
          {isInitialized && !isRunning && (
            <button className="btn btn-primary btn-sm" onClick={handleRunTests}>
              <i className="fas fa-play"></i> Run Tests
            </button>
          )}
          <button
            className="btn btn-sm"
            style={{ background: '#4a5568', color: '#e2e8f0' }}
            onClick={handleCleanup}
          >
            <i className="fas fa-broom"></i>
          </button>
        </div>
      </header>

      <div className="main-content">
        {/* Sidebar */}
        <div className="sidebar">
          <div className="sidebar-tabs">
            <button
              className={`sidebar-tab ${activeTab === 'config' ? 'active' : ''}`}
              onClick={() => setActiveTab('config')}
            >
              <i className="fas fa-cog"></i> Config
            </button>
            <button
              className={`sidebar-tab ${activeTab === 'scenarios' ? 'active' : ''}`}
              onClick={() => setActiveTab('scenarios')}
            >
              <i className="fas fa-list"></i> Tests ({selectedScenarios.length})
            </button>
            <button
              className={`sidebar-tab ${activeTab === 'results' ? 'active' : ''}`}
              onClick={() => setActiveTab('results')}
            >
              <i className="fas fa-chart-bar"></i> Results
            </button>
          </div>
          <div className="sidebar-content">
            {activeTab === 'config' && (
  <div>
    <LoginConfig onInitialize={handleInitialize} isInitialized={isInitialized} />
    <AttachmentConfig apiBase={API_BASE} isRunning={isRunning} />
    <ExcelSuiteConfig
      apiBase={API_BASE}
      isRunning={isRunning}
      isInitialized={isInitialized}
      onRunSuite={handleRunExcelSuite}
    />
  </div>
)}
            {activeTab === 'scenarios' && (
              <div>
                <div className="select-controls">
                  <button className="btn btn-sm btn-success" onClick={selectAll}>All</button>
                  <button
                    className="btn btn-sm"
                    style={{ background: '#4a5568', color: '#e2e8f0' }}
                    onClick={selectNone}
                  >
                    None
                  </button>
                  <span style={{ fontSize: '11px', color: '#a0aec0', alignSelf: 'center' }}>
                    {selectedScenarios.length}/{scenarios.length} selected
                  </span>
                </div>
                {scenarios.map(s => {
                  const result = testResults.find(r => r.test_id === s.id);
                  return (
                    <div
                      key={s.id}
                      className={`scenario-item ${selectedScenarios.includes(s.id) ? 'selected' : ''}`}
                      onClick={() => toggleScenario(s.id)}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span className="scenario-id">{s.id}</span>
                        <span className={`priority-badge ${s.priority}`}>{s.priority}</span>
                      </div>
                      <div className="scenario-name">{s.name}</div>
                      <div className="scenario-category">{s.category}</div>
                      {result && (
                        <span className={`scenario-status ${result.status}`}>
                          {result.status}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            {activeTab === 'results' && (
              <TestDashboard results={testResults} progress={progress} />
            )}
          </div>
        </div>

        {/* Center Panel - Live View */}
        <div className="center-panel">
          {isRunning && (
            <div className="progress-container">
              <div className="progress-info">
                <span>
                  Test {progress.current}/{progress.total}: {progress.current_test}
                </span>
                <span>{progress.percentage}%</span>
              </div>
              <div className="progress-bar-track">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${progress.percentage}%` }}
                ></div>
              </div>
            </div>
          )}
          <div className="panel-header">
            <span className="panel-title">
              <i className="fas fa-comments" style={{ marginRight: '8px', color: '#667eea' }}></i>
              Live Conversation View
            </span>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span style={{ fontSize: '11px', color: '#68d391' }}>✅ {passedCount}</span>
              <span style={{ fontSize: '11px', color: '#fc8181' }}>❌ {failedCount}</span>
              <span style={{ fontSize: '11px', color: '#f6e05e' }}>⚠️ {errorCount}</span>
            </div>
          </div>
          <div className="panel-body">
            <LiveView messages={chatMessages} chatEndRef={chatEndRef} />
          </div>
        </div>

        {/* Right Panel - Logs & Reports */}
        <div className="right-panel">
          <div className="panel-header">
            <span className="panel-title">
              <i className="fas fa-terminal" style={{ marginRight: '8px', color: '#667eea' }}></i>
              Logs & Reports
            </span>
          </div>
          <div className="panel-body" style={{ flex: 1 }}>
            {logs.map((log, i) => (
              <div key={i} className={`log-entry ${log.level}`}>
                <span className="log-time">{log.time}</span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
          <div style={{ borderTop: '1px solid #2d3748', padding: '12px' }}>
            <div className="panel-title" style={{ marginBottom: '8px', fontSize: '12px' }}>
              <i className="fas fa-file-excel" style={{ marginRight: '6px', color: '#68d391' }}></i>
              Reports
            </div>
            <ReportView reports={reports} apiBase={API_BASE} onRefresh={fetchReports} />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
