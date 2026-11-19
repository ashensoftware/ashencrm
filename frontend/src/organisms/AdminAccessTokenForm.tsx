import { useId, useState, type FormEvent } from "react";
import { signInWithPassword, storeAccessToken } from "../api";

interface Props {
  hint?: string;
}

const supabaseConfigured = Boolean(
  import.meta.env.VITE_SUPABASE_URL && import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY,
);

export function AdminAccessTokenForm({ hint }: Props) {
  const emailId = useId();
  const passwordId = useId();
  const tokenId = useId();
  const [value, setValue] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [showToken, setShowToken] = useState(!supabaseConfigured);

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    storeAccessToken(value);
    window.location.assign("/leads");
  };

  const onPassword = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    try {
      await signInWithPassword(email, password);
      window.location.assign("/leads");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "No se pudo iniciar sesión.");
    }
  };

  return (
    <div className="auth-panel">
      {supabaseConfigured && (
        <form onSubmit={onPassword} className="auth-form">
          <div className="filter-group">
            <label htmlFor={emailId}>Correo</label>
            <input
              id={emailId}
              className="search-input"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div className="filter-group">
            <label htmlFor={passwordId}>Contraseña</label>
            <input
              id={passwordId}
              className="search-input"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn-primary auth-submit">
            Entrar
          </button>
          {error && <p className="auth-error">{error}</p>}
        </form>
      )}

      <button
        type="button"
        className="auth-toggle"
        onClick={() => setShowToken((open) => !open)}
      >
        {showToken ? "Ocultar acceso con token" : "Usar token de acceso"}
      </button>

      {showToken && (
        <form onSubmit={onSubmit} className="auth-form">
          <div className="filter-group">
            <label htmlFor={tokenId}>Token de acceso (Bearer)</label>
            <input
              id={tokenId}
              className="search-input"
              type="password"
              autoComplete="off"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              placeholder="JWT. No es una contraseña."
            />
          </div>
          <button type="submit" className="btn-primary auth-submit">
            Usar token
          </button>
          {hint && <p className="auth-hint">{hint}</p>}
        </form>
      )}
    </div>
  );
}
