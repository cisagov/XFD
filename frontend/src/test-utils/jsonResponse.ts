/**
 * Utility function to create a JSON response for testing purposes.
 * @param body - The response body.
 * @param init - Optional response initialization options.
 * @returns A Response object with the JSON-serialized body and appropriate headers.
 */

export function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  const headers = new Headers({
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string> | undefined)
  });

  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    statusText: init.statusText,
    headers: headers
  });
}
