declare module 'pkce-challenge' {
  export default function pkceChallenge(length?: number): {
    code_verifier: string;
    code_challenge: string;
  };
}
