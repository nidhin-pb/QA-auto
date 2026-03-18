import React from 'react';

function LiveView({ messages, chatEndRef }) {
  if (messages.length === 0) {
    return (
      <div style={{display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100%', color:'#4a5568'}}>
        <i className="fas fa-comments" style={{fontSize:'48px', marginBottom:'16px'}}></i>
        <p style={{fontSize:'14px'}}>Conversations will appear here in real-time</p>
        <p style={{fontSize:'12px', marginTop:'4px'}}>Connect and run tests to begin</p>
      </div>
    );
  }

  return (
    <div className="chat-container">
      {messages.map((msg, i) => (
        <div key={i} className={`chat-message ${msg.sender}`}>
          <div className="chat-sender">
            {msg.sender === 'user' ? 'Tester / Simulated User' : msg.sender === 'cva' ? 'CVA' : 'System'}
            <span style={{marginLeft:'8px', fontSize:'9px', opacity:0.6}}>{msg.time}</span>
          </div>
          <div>{msg.message}</div>
          {msg.screenshot && (
            <img
              src={msg.screenshot}
              alt="Screenshot"
              className="chat-screenshot"
              style={{maxWidth:'300px', maxHeight:'200px', cursor:'pointer'}}
              onClick={() => window.open(msg.screenshot, '_blank')}
            />
          )}
        </div>
      ))}
      <div ref={chatEndRef} />
    </div>
  );
}

export default LiveView;
