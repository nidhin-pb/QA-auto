import React, { useState } from 'react';

function LoginConfig({ onInitialize, isInitialized }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [headless, setHeadless] = useState(false);
  const [cvaAppName, setCvaAppName] = useState('IT Servicedesk AI');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onInitialize({ email, password, headless, cva_app_name: cvaAppName });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <h3 style={{fontSize:'14px', fontWeight:700, marginBottom:'16px', color:'#667eea'}}>
        <i className="fas fa-lock" style={{marginRight:'8px'}}></i>
        Teams Login
      </h3>

      <div className="form-group">
        <label className="form-label">Email / Username</label>
        <input
          type="text"
          className="form-input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="user@company.com"
          required
        />
      </div>

      <div className="form-group">
        <label className="form-label">Password</label>
        <input
          type="password"
          className="form-input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          required
        />
      </div>

      <div className="form-group">
        <label className="form-label">CVA App Name</label>
        <input
          type="text"
          className="form-input"
          value={cvaAppName}
          onChange={(e) => setCvaAppName(e.target.value)}
          placeholder="IT Servicedesk AI"
        />
      </div>

      <div className="form-group">
        <label className="form-checkbox">
          <input
            type="checkbox"
            checked={headless}
            onChange={(e) => setHeadless(e.target.checked)}
          />
          Run headless (no browser window)
        </label>
      </div>

      <button
        type="submit"
        className="btn btn-primary"
        disabled={loading || isInitialized || !email || !password}
      >
        {loading ? (
          <><i className="fas fa-spinner fa-spin"></i> Connecting...</>
        ) : isInitialized ? (
          <><i className="fas fa-check"></i> Connected</>
        ) : (
          <><i className="fas fa-sign-in-alt"></i> Connect & Initialize</>
        )}
      </button>

      {isInitialized && (
        <div style={{marginTop:'12px', padding:'8px', background:'#1a472a', borderRadius:'6px', fontSize:'12px', color:'#68d391', textAlign:'center'}}>
          ✅ Connected! Select tests and click Run.
        </div>
      )}
    </form>
  );
}

export default LoginConfig;
