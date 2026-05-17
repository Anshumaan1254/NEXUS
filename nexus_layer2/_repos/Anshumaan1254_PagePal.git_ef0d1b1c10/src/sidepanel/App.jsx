import React, { useState } from 'react';
import Antigravity from './Antigravity';

function App() {
  const [summary, setSummary] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [downloadProgress, setDownloadProgress] = useState(0);

  const handleSummarizeClick = () => {
    setIsLoading(true);
    setSummary('');
    setDownloadProgress(0);

    chrome.runtime.sendMessage({ type: 'GET_PAGE_CONTENT' }, async (response) => {
      if (chrome.runtime.lastError) {
        setSummary("Error: " + chrome.runtime.lastError.message);
        setIsLoading(false);
        return;
      }
      if (response && response.error) {
        setSummary("Error: " + response.error);
        setIsLoading(false);
        return;
      }

      if (response && response.content) {
        try {
          await generateSummary(response.content);
        } catch (err) {
          setSummary("Error generating summary: " + err.message);
        } finally {
          setIsLoading(false);
          setDownloadProgress(0);
        }
      } else {
        setSummary("Error: No content received.");
        setIsLoading(false);
      }
    });
  };

  const generateSummary = async (text) => {
    const chunks = text.split('\n\n').filter(chunk => chunk.trim().length > 100);
    if (chunks.length === 0) {
      setSummary("Content too short to summarize.");
      return;
    }

    let session;
    let strategy = 'none';

    const ai = window.ai || window.model;
    const GlobalWriter = window.Writer;
    const GlobalSummarizer = window.Summarizer;

    try {
      const monitorConfig = {
        monitor(m) {
          m.addEventListener('downloadprogress', (e) => {
            const pct = Math.round((e.loaded / e.total) * 100);
            setDownloadProgress(pct);
          });
        }
      };

      if (GlobalSummarizer && GlobalSummarizer.create) {
        const available = await GlobalSummarizer.availability();
        if (available === 'available' || available === 'readily' || available === 'downloadable' || available === 'after-download') {
          session = await GlobalSummarizer.create({
            type: 'key-points',
            format: 'markdown',
            length: 'medium',
            sharedContext: "This is an article or web page content. The user needs a concise summary.",
            outputLanguage: 'en',
            ...monitorConfig
          });
          setDownloadProgress(0);
          strategy = 'summarizer';
        }
      }

      if (strategy === 'none' && ai && ai.summarizer) {
        let sAvailable = 'no';
        if (ai.summarizer.availability) {
          sAvailable = await ai.summarizer.availability();
        } else if (ai.summarizer.capabilities) {
          const caps = await ai.summarizer.capabilities();
          sAvailable = caps.available;
        }

        if (sAvailable === 'available' || sAvailable === 'readily' || sAvailable === 'downloadable' || sAvailable === 'after-download') {
          session = await ai.summarizer.create({
            type: 'key-points',
            format: 'markdown',
            length: 'medium',
            sharedContext: "This is an article or web page content. The user needs a concise summary.",
            outputLanguage: 'en',
            ...monitorConfig
          });
          setDownloadProgress(0);
          strategy = 'summarizer';
        }
      }

      if (strategy === 'none' && GlobalWriter && GlobalWriter.create) {
        const available = await GlobalWriter.availability();
        if (available === 'available' || available === 'readily' || available === 'downloadable' || available === 'after-download') {
          session = await GlobalWriter.create({
            sharedContext: "You are a helpful assistant. Summarize the text provided.",
            ...monitorConfig
          });
          strategy = 'writer';
        }
      }

      if (strategy === 'none' && ai && ai.writer) {
        let wAvailable = 'no';
        if (ai.writer.availability) {
          wAvailable = await ai.writer.availability();
        } else if (ai.writer.capabilities) {
          const caps = await ai.writer.capabilities();
          wAvailable = caps.available;
        }

        if (wAvailable === 'available' || wAvailable === 'readily' || wAvailable === 'downloadable' || wAvailable === 'after-download') {
          session = await ai.writer.create({
            sharedContext: "You are a helpful assistant. Summarize the text provided.",
            ...monitorConfig
          });
          strategy = 'writer';
        }
      }

      if (strategy === 'none') {
        strategy = 'heuristic';
      }

    } catch (e) {
      strategy = 'heuristic';
    }

    let fullSummary = "";

    try {
      if (strategy === 'heuristic') {
        fullSummary = "⚠️ **Note:** AI API unavailable (Heuristic Mode).\n";
        fullSummary += `DEBUG: Ext ID: ${chrome.runtime.id} \n`;
        fullSummary += `DEBUG: window.ai: ${!!ai} \n`;
        if (ai) {
          fullSummary += `DEBUG: ai.summarizer: ${ai.summarizer ? 'Found' : 'Missing'} \n`;
          fullSummary += `DEBUG: ai.writer: ${ai.writer ? 'Found' : 'Missing'} \n`;
        }
        fullSummary += `DEBUG: Global Writer: ${!!GlobalWriter} \n`;
        fullSummary += `DEBUG: Global Summarizer: ${!!GlobalSummarizer} \n\n`;

        fullSummary += chunks.map(chunk => {
          const firstSentence = chunk.trim().split(/[.!?]/)[0];
          return "- " + firstSentence + ".";
        }).join("\n");
      } else if (strategy === 'writer') {
        for (const chunk of chunks) {
          const result = await session.write(chunk, {
            context: "Summarize this paragraph concisely."
          });
          fullSummary += (fullSummary ? "\n\n" : "") + result;
        }
        session.destroy();
      } else {
        for (let i = 0; i < chunks.length; i++) {
          const result = await session.summarize(chunks[i], {
            context: "This chunk is part of a larger webpage."
          });
          const summaryText = typeof result === 'string' ? result : result.summary;
          fullSummary += (fullSummary ? "\n\n" : "") + summaryText;
        }
        session.destroy();
      }
    } catch (err) {
      if (strategy !== 'heuristic') {
        setSummary(prev => prev + "\n\n⚠️ AI Error (" + err.message + "). Switching to basic summary.\n\n" + chunks.map(c => "- " + c.split('.')[0]).join('\n'));
        return;
      }
      throw err;
    }

    setSummary(fullSummary);
  };

  return (
    <div className="app-wrapper">
      <div className="background-animation">
        <Antigravity
          count={200}
          magnetRadius={8}
          ringRadius={6}
          waveSpeed={0.3}
          waveAmplitude={1.2}
          particleSize={1.2}
          lerpSpeed={0.04}
          color={'#0ad1c8'}
          autoAnimate={true}
          particleVariance={0.8}
        />
      </div>

      <div className="container">
        <header>
          <div className="logo-icon">📄</div>
          <h1>PagePal</h1>
          <p>Your AI-powered reading companion</p>
        </header>

        <main>
          <button
            className={`primary-btn ${isLoading ? 'loading' : ''}`}
            onClick={handleSummarizeClick}
            disabled={isLoading}
          >
            <span className="btn-icon">📸</span>
            <span className="btn-text">
              {isLoading
                ? (downloadProgress > 0 ? `Downloading AI: ${downloadProgress}%` : 'Capturing...')
                : 'Page Snapshot'
              }
            </span>
          </button>

          {summary && (
            <div className="results-card">
              <div className="card-header">
                <span className="card-icon">✨</span>
                <h2>Page Snapshot</h2>
              </div>
              <div className="card-content">
                <pre>{summary}</pre>
              </div>
            </div>
          )}

          <div className="instructions-card">
            <div className="card-header">
              <span className="card-icon">💡</span>
              <h2>How to use</h2>
            </div>
            <div className="card-content">
              <div className="feature-item">
                <span className="feature-icon">📸</span>
                <div className="feature-text">
                  <strong>Page Snapshot</strong>
                  <p>Click the button above to capture key points from any page.</p>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">🔍</span>
                <div className="feature-text">
                  <strong>Quick Define</strong>
                  <p>Highlight any word on the page to get an instant explanation.</p>
                </div>
              </div>
            </div>
          </div>
        </main>

        <footer>
          <p>Powered by Chrome AI</p>
        </footer>
      </div>
    </div>
  );
}

export default App;
