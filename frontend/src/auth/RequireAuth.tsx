import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { accessToken } from "../api";

export function RequireAuth({ children }: { children: ReactNode }) {
  const location = useLocation();
  if (!accessToken()) {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }
  return children;
}
