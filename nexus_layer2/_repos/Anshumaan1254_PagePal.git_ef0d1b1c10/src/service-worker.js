/* global chrome */

chrome.action.onClicked.addListener((tab) => {
  chrome.sidePanel.open({ tabId: tab.id });
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'GET_PAGE_CONTENT':
      if (sender.tab) {
        handleGetPageContent(sender.tab.id, sendResponse);
      } else {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (tabs.length > 0) {
            handleGetPageContent(tabs[0].id, sendResponse);
          } else {
            sendResponse({ error: "No active tab found." });
          }
        });
      }
      return true;
      break;
    case 'SUMMARIZE_PAGE':
      if (sender.tab) {
        handleGetPageContent(sender.tab.id, sendResponse);
      }
      return true;
      break;
    case 'EXPLAIN_TEXT':
      handleExplainText(message.text, sender.tab.id);
      break;
  }
  return true;
});

async function handleGetPageContent(tabId, sendResponse) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => document.body.innerText,
    });

    if (!results || !results[0] || !results[0].result) {
      sendResponse({ error: "No content found on page." });
      return;
    }
    const pageText = results[0].result;
    sendResponse({ content: pageText });

  } catch (error) {
    sendResponse({ error: error.message });
  }
}

async function handleSummarizePageInMainWorld(tabId, sendResponse) {
  try {
    await chrome.scripting.executeScript({
      target: { tabId: tabId },
      world: 'MAIN',
      func: async () => {
        try {
          const text = document.body.innerText;
          if (!text || text.trim().length === 0) throw new Error("Page is empty.");

          const ai = window.ai || window.model;

          let summarizer;
          let strategy = 'none';

          if (!ai) {
            strategy = 'heuristic';
          } else {
            try {
              if (ai.summarizer) {
                let available = 'no';
                if (ai.summarizer.availability) {
                  available = await ai.summarizer.availability();
                } else if (ai.summarizer.capabilities) {
                  const caps = await ai.summarizer.capabilities();
                  available = caps.available;
                }

                if (available === 'available' || available === 'readily' || available === 'downloadable' || available === 'after-download') {
                  summarizer = await ai.summarizer.create({
                    type: 'key-points',
                    format: 'markdown',
                    length: 'medium',
                    sharedContext: "This is an article or web page content. The user needs a concise summary."
                  });
                  strategy = 'summarizer';
                }
              }

              if (strategy === 'none' && ai.writer) {
                let available = 'no';
                if (ai.writer.availability) {
                  available = await ai.writer.availability();
                }

                if (available === 'available' || available === 'readily' || available === 'downloadable' || available === 'after-download') {
                  summarizer = await ai.writer.create({
                    sharedContext: "You are a helpful assistant. Summarize the text provided."
                  });
                  strategy = 'writer';
                }
              }

              if (strategy === 'none') {
                strategy = 'heuristic';
              }

            } catch (err) {
              strategy = 'heuristic';
            }
          }

          const chunks = text.split('\n\n').filter(chunk => chunk.trim().length > 100);
          if (chunks.length === 0) {
            window.postMessage({ type: 'GIST_MAIN_WORLD_ERROR', error: "Content too short to summarize." }, '*');
            return;
          }

          let fullSummary = "";

          if (strategy === 'heuristic') {
            fullSummary = "⚠️ **Note:** AI API unavailable. Showing basic summary.\n\n";
            fullSummary += chunks.map(chunk => {
              const firstSentence = chunk.trim().split(/[.!?]/)[0];
              return "- " + firstSentence + ".";
            }).join("\n");
          } else if (strategy === 'writer') {
            for (const chunk of chunks) {
              const result = await summarizer.write(chunk, {
                context: "Summarize this paragraph concisely."
              });
              fullSummary += (fullSummary ? "\n\n" : "") + result;
            }
            if (summarizer.destroy) summarizer.destroy();
          } else {
            for (const chunk of chunks) {
              const result = await summarizer.summarize(chunk, {
                context: "This chunk is part of a larger webpage."
              });
              const summaryText = typeof result === 'string' ? result : result.summary;
              fullSummary += (fullSummary ? "\n\n" : "") + summaryText;
            }
            if (summarizer.destroy) summarizer.destroy();
          }

          window.postMessage({ type: 'GIST_MAIN_WORLD_RESULT', content: fullSummary }, '*');

        } catch (e) {
          let msg = e.message;
          if (msg.includes("Error:")) msg = msg.split("Error:")[1].trim();
          window.postMessage({ type: 'GIST_MAIN_WORLD_ERROR', error: msg }, '*');
        }
      }
    });

    sendResponse({ status: "Script injected. Waiting for result..." });

  } catch (error) {
    sendResponse({ error: error.message });
  }
}

async function handleExplainText(text, tabId) {
  const prompt = `Explain the following term or phrase in one simple sentence for a non-expert: "${text}"`;

  try {
    let session = null;
    let fullResponse = "";

    const LanguageModel = self.LanguageModel || (self.ai && self.ai.languageModel);

    if (LanguageModel) {
      let availability = 'no';
      if (LanguageModel.availability) {
        availability = await LanguageModel.availability();
      } else if (LanguageModel.capabilities) {
        const caps = await LanguageModel.capabilities();
        availability = caps.available;
      }

      if (availability === 'available' || availability === 'readily' || availability === 'downloadable' || availability === 'after-download') {
        session = await LanguageModel.create({
          systemPrompt: "You are a helpful assistant that explains complex terms simply."
        });
        fullResponse = await session.prompt(prompt);
      }
    }

    if (!session && self.ai && self.ai.canCreateTextSession) {
      const availability = await self.ai.canCreateTextSession();
      if (availability === 'readily') {
        session = await self.ai.createTextSession();
        const stream = session.promptStreaming(prompt);
        for await (const chunk of stream) {
          fullResponse = chunk;
        }
      }
    }

    if (fullResponse) {
      chrome.tabs.sendMessage(tabId, {
        type: 'SHOW_EXPLANATION',
        explanation: fullResponse,
      });
      if (session && session.destroy) session.destroy();
    } else {
      chrome.tabs.sendMessage(tabId, {
        type: 'SHOW_EXPLANATION',
        explanation: "AI unavailable. Please enable chrome://flags/#language-model-api",
      });
    }
  } catch (error) {
    chrome.tabs.sendMessage(tabId, {
      type: 'SHOW_EXPLANATION',
      explanation: "Error: " + error.message,
    });
  }
}