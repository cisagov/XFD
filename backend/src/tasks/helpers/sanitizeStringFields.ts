// Sometimes, a field might contain null characters, but we can't store null
// characters in a string field in PostgreSQL. For example, a site might have
// a banner ending with "</body>\r\n</html>\u0000" or "\\u0000".
export const sanitizeStringField = (input) =>
  input.replace(/\\u0000/g, '').replace(/\0/g, '');
