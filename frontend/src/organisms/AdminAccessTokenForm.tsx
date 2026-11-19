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

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    storeAccessToken(value);
    window.location.reload();
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
    <div>
      {supabaseConfigured && (
        <form
          onSubmit={onPassword}
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: "0.5rem",
            alignItems: "flex-end",
            marginTop: "0.75rem",
          }}
        >
          <div className="filter-group" style={{ minWidth: "14rem", flex: 1 }}>
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
          <div className="filter-group" style={{ minWidth: "14rem", flex: 1 }}>
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
          <button type="submit" className="btn-primary">
            Entrar
          </button>
          {error && (
            <p style={{ margin: 0, flexBasis: "100%", color: "var(--danger, #b42318)" }}>{error}</p>
          )}
        </form>
      )}
    <form
      onSubmit={onSubmit}
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "0.5rem",
        alignItems: "flex-end",
        marginTop: "0.75rem",
      }}
    >
      <div className="filter-group" style={{ minWidth: "16rem", flex: 1 }}>
        <label htmlFor={tokenId}>Token de acceso (Bearer)</label>
        <input
          id={tokenId}
          className="search-input"
          type="password"
          autoComplete="off"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="JWT local. No es una contraseña."
        />
      </div>
      <button type="submit" className="btn-primary">
        Usar token
      </button>
      {hint && (
        <p style={{ margin: 0, flexBasis: "100%", color: "var(--text-muted)", fontSize: "0.85rem" }}>
          {hint}
        </p>
      )}
    </form>
    </div>
  );
}
