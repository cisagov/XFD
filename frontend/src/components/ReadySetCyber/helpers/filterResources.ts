export const isResourceVisible = (response: string) => {
  const r = response.toLowerCase();
  return r === 'no' || r === 'not in scope' || r === 'not started';
};
