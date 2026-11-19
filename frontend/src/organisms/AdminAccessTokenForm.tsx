import { useState, type FormEvent } from "react";
import { storeAccessToken } from "../api";

interface Props {
  hint?: string;
}

export function AdminAccessTokenForm({ hint }: Props) {
  const [value, setValue] = useState("");

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    storeAccessToken(value);
    window.location.reload();
  };

  return (
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
        <label htmlFor="admin-access-token">Token de acceso (Bearer)</label>
        <input
          id="admin-access-token"
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
  );
}
