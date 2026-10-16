export const demoMode = import.meta.env.MODE === 'demo';

export async function newsRequest(url, options) {
  if (!demoMode) return fetch(url, options);
  const { demoNewsResponse } = await import('./demo-news.js');
  options?.signal?.throwIfAborted();
  return demoNewsResponse(url);
}
