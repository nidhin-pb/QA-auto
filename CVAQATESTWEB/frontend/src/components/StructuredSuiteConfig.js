import React, { useEffect, useState } from 'react';

function StructuredSuiteConfig({ apiBase, isRunning, isInitialized, onRunStructuredSuite }) {
  const [suite, setSuite] = useState({
    suite_name: '',
    count: 0,
    errors: [],
    plan_summary: {},
    preview: []
  });

  const [summary, setSummary] = useState({
    total: 0,
    modules: {},
    families: {},
    execution_modes: {},
    automation_levels: {},
    priorities: {}
  });

  const [busy, setBusy] = useState(false);

  const [selectedModules, setSelectedModules] = useState([]);
  const [selectedFamilies, setSelectedFamilies] = useState([]);
  const [selectedModes, setSelectedModes] = useState([]);
  const [selectedLevels, setSelectedLevels] = useState([]);
  const [selectedPriorities, setSelectedPriorities] = useState([]);
  const [limit, setLimit] = useState(10);

  const refresh = async () => {
    try {
      const res1 = await fetch(`${apiBase}/api/structured-suite`);
      const data1 = await res1.json();
      setSuite(data1);

      const res2 = await fetch(`${apiBase}/api/structured-suite/classification-summary`);
      const data2 = await res2.json();
      setSummary(data2);
    } catch (err) {
      console.error('Structured suite refresh failed:', err);
    }
  };

  useEffect(() => { refresh(); }, []);

  const onPick = async (e) => {
    const f = (e.target.files || [])[0];
    if (!f) return;

    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', f);
      const res = await fetch(`${apiBase}/api/structured-suite/upload`, { method: 'POST', body: fd });
      await res.json();
      await refresh();
    } finally {
      setBusy(false);
      e.target.value = '';
    }
  };

  const toggleValue = (value, selected, setter) => {
    if (selected.includes(value)) {
      setter(selected.filter(x => x !== value));
    } else {
      setter([...selected, value]);
    }
  };

  const renderMultiSelect = (title, items, selected, setter) => (
    <div className="form-group">
      <label className="form-label">{title}</label>
      <div style={{ maxHeight: '120px', overflowY: 'auto', background: '#2d3748', borderRadius: '6px', padding: '8px' }}>
        {Object.keys(items || {}).sort().map((item, i) => (
          <label key={i} style={{ display: 'block', fontSize: '12px', color: '#e2e8f0', marginBottom: '4px', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={selected.includes(item)}
              onChange={() => toggleValue(item, selected, setter)}
              style={{ marginRight: '8px' }}
            />
            {item} ({items[item]})
          </label>
        ))}
      </div>
    </div>
  );

  const handleRun = () => {
    const payload = {
      limit: Number(limit) || 10
    };

    if (selectedModules.length > 0) payload.modules = selectedModules;
    if (selectedFamilies.length > 0) payload.families = selectedFamilies;
    if (selectedModes.length > 0) payload.execution_modes = selectedModes;
    if (selectedLevels.length > 0) payload.automation_levels = selectedLevels;
    if (selectedPriorities.length > 0) payload.priorities = selectedPriorities;

    onRunStructuredSuite(payload);
  };

  const clearFilters = () => {
    setSelectedModules([]);
    setSelectedFamilies([]);
    setSelectedModes([]);
    setSelectedLevels([]);
    setSelectedPriorities([]);
    setLimit(10);
  };

  return (
    <div style={{ marginTop: '14px' }}>
      <h3 style={{ fontSize: '14px', fontWeight: 700, marginBottom: '10px', color: '#667eea' }}>
        Structured Scenario Workbook
      </h3>

      <input
        type="file"
        disabled={busy || isRunning}
        onChange={onPick}
        style={{ width: '100%', marginBottom: '10px' }}
        accept=".xlsx"
      />

      <div style={{ fontSize: '12px', color: '#a0aec0', marginBottom: '6px' }}>
        Loaded: {suite.count || 0} structured scenarios {suite.suite_name ? `(${suite.suite_name})` : ''}
      </div>

      {suite.errors && suite.errors.length > 0 && (
        <div style={{ background: '#742a2a', color: '#fed7d7', padding: '8px', borderRadius: '6px', fontSize: '12px', marginBottom: '10px' }}>
          {suite.errors.map((er, i) => <div key={i}>• {er}</div>)}
        </div>
      )}

      <div style={{ background: '#1a202c', padding: '10px', borderRadius: '8px', marginBottom: '10px', fontSize: '12px' }}>
        <div><strong>Total:</strong> {summary.total || 0}</div>
        <div><strong>Modules:</strong> {Object.keys(summary.modules || {}).length}</div>
        <div><strong>Families:</strong> {Object.keys(summary.families || {}).length}</div>
        <div><strong>Execution Modes:</strong> {Object.keys(summary.execution_modes || {}).length}</div>
      </div>

      <div style={{ background: '#1a202c', padding: '10px', borderRadius: '8px', marginBottom: '10px' }}>
        <div style={{ fontSize: '12px', fontWeight: 700, color: '#e2e8f0', marginBottom: '8px' }}>
          Select Filters for Run
        </div>

        {renderMultiSelect('Modules', summary.modules, selectedModules, setSelectedModules)}
        {renderMultiSelect('Families', summary.families, selectedFamilies, setSelectedFamilies)}
        {renderMultiSelect('Execution Modes', summary.execution_modes, selectedModes, setSelectedModes)}
        {renderMultiSelect('Automation Levels', summary.automation_levels, selectedLevels, setSelectedLevels)}
        {renderMultiSelect('Priorities', summary.priorities, selectedPriorities, setSelectedPriorities)}

        <div className="form-group">
          <label className="form-label">Limit</label>
          <input
            type="number"
            className="form-input"
            value={limit}
            onChange={(e) => setLimit(e.target.value)}
            min="1"
            max="200"
          />
        </div>

        <button
          className="btn btn-sm"
          style={{ width: '100%', marginBottom: '8px', background: '#4a5568', color: '#e2e8f0' }}
          onClick={clearFilters}
        >
          Clear Filters
        </button>
      </div>

      <button
        className="btn btn-primary"
        disabled={!isInitialized || isRunning || busy || !(suite.count > 0)}
        onClick={handleRun}
        style={{ width: '100%' }}
      >
        Run Structured Suite
      </button>

      <button
        className="btn btn-sm"
        style={{ width: '100%', marginTop: '8px', background: '#2d3748', color: '#a0aec0' }}
        onClick={refresh}
        disabled={busy || isRunning}
      >
        Refresh Structured Suite
      </button>
    </div>
  );
}

export default StructuredSuiteConfig;
