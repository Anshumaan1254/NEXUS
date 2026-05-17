/* global chrome */

let tooltip = null;

document.addEventListener('mouseup', (event) => {
  const selectedText = window.getSelection().toString().trim();

  if (selectedText.length > 2 && selectedText.length < 100) {
    chrome.runtime.sendMessage({ type: 'EXPLAIN_TEXT', text: selectedText }, (response) => {
      if (chrome.runtime.lastError) {
        console.error("Quick Define error:", chrome.runtime.lastError.message);
      }
    });
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'SHOW_EXPLANATION') {
    displayTooltip(message.explanation);
  }
});

window.addEventListener("message", (event) => {
  if (event.source !== window) return;

  if (event.data.type && (event.data.type === 'GIST_MAIN_WORLD_RESULT' || event.data.type === 'GIST_MAIN_WORLD_ERROR')) {
    chrome.runtime.sendMessage(event.data);
  }
});

function displayTooltip(text) {
  if (tooltip) {
    tooltip.remove();
  }

  tooltip = document.createElement('div');
  tooltip.id = 'cognitive-flow-tooltip';

  const header = document.createElement('div');
  header.innerHTML = '🔍 <strong>Quick Define</strong>';
  Object.assign(header.style, {
    marginBottom: '8px',
    paddingBottom: '8px',
    borderBottom: '1px solid rgba(255,255,255,0.2)',
    fontSize: '12px',
    color: '#93c5fd'
  });

  const content = document.createElement('div');
  content.textContent = text;

  const closeBtn = document.createElement('span');
  closeBtn.textContent = '×';
  Object.assign(closeBtn.style, {
    position: 'absolute',
    top: '8px',
    right: '12px',
    cursor: 'pointer',
    fontSize: '18px',
    color: '#94a3b8',
    fontWeight: 'bold'
  });
  closeBtn.onclick = () => {
    if (tooltip) {
      tooltip.remove();
      tooltip = null;
    }
  };

  Object.assign(tooltip.style, {
    position: 'fixed',
    top: '20px',
    right: '20px',
    backgroundColor: '#1e293b',
    border: '1px solid #3b82f6',
    borderRadius: '12px',
    padding: '16px',
    boxShadow: '0 10px 25px rgba(0,0,0,0.3), 0 0 0 1px rgba(59, 130, 246, 0.5)',
    zIndex: '2147483647',
    maxWidth: '320px',
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#e2e8f0',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    animation: 'cogflow-slide-in 0.3s ease-out'
  });

  if (!document.getElementById('cogflow-styles')) {
    const style = document.createElement('style');
    style.id = 'cogflow-styles';
    style.textContent = `
      @keyframes cogflow-slide-in {
        from { opacity: 0; transform: translateX(20px); }
        to { opacity: 1; transform: translateX(0); }
      }
    `;
    document.head.appendChild(style);
  }

  tooltip.appendChild(closeBtn);
  tooltip.appendChild(header);
  tooltip.appendChild(content);
  document.body.appendChild(tooltip);

  setTimeout(() => {
    if (tooltip) {
      tooltip.remove();
      tooltip = null;
    }
  }, 10000);
}