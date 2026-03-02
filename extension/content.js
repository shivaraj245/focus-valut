let pageLoadTime = Date.now();
let isPageVisible = true;
let totalVisibleTime = 0;
let lastVisibilityChange = Date.now();

document.addEventListener('visibilitychange', () => {
  const now = Date.now();
  
  if (document.hidden) {
    totalVisibleTime += (now - lastVisibilityChange);
    isPageVisible = false;
  } else {
    lastVisibilityChange = now;
    isPageVisible = true;
  }
});

function extractPageContent() {
  const content = {
    title: document.title,
    url: window.location.href,
    domain: window.location.hostname,
    
    mainText: '',
    headings: [],
    links: [],
    
    meta: {
      description: '',
      keywords: '',
      author: ''
    }
  };
  
  const metaDescription = document.querySelector('meta[name="description"]');
  if (metaDescription) {
    content.meta.description = metaDescription.content;
  }
  
  const metaKeywords = document.querySelector('meta[name="keywords"]');
  if (metaKeywords) {
    content.meta.keywords = metaKeywords.content;
  }
  
  const metaAuthor = document.querySelector('meta[name="author"]');
  if (metaAuthor) {
    content.meta.author = metaAuthor.content;
  }
  
  const headings = document.querySelectorAll('h1, h2, h3');
  content.headings = Array.from(headings).map(h => ({
    level: h.tagName,
    text: h.textContent.trim()
  })).slice(0, 10);
  
  const article = document.querySelector('article, main, .content, .post, #content');
  if (article) {
    content.mainText = article.textContent.trim().substring(0, 5000);
  } else {
    const paragraphs = document.querySelectorAll('p');
    content.mainText = Array.from(paragraphs)
      .map(p => p.textContent.trim())
      .join(' ')
      .substring(0, 5000);
  }
  
  return content;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'EXTRACT_CONTENT') {
    const content = extractPageContent();
    sendResponse(content);
  }
  
  if (message.type === 'GET_PAGE_STATS') {
    const now = Date.now();
    const currentVisibleTime = isPageVisible ? (now - lastVisibilityChange) : 0;
    
    sendResponse({
      totalTime: Math.floor((now - pageLoadTime) / 1000),
      visibleTime: Math.floor((totalVisibleTime + currentVisibleTime) / 1000),
      scrollDepth: Math.floor((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100)
    });
  }
  
  return true;
});

window.addEventListener('beforeunload', () => {
  if (isPageVisible) {
    totalVisibleTime += (Date.now() - lastVisibilityChange);
  }
});
