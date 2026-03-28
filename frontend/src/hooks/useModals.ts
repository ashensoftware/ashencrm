import { useState, useCallback } from "react";
import type { ModalType } from "../types";

export function useModals() {
  const [modal, setModal] = useState<ModalType>(null);
  const [alertState, setAlertState] = useState({ title: "", message: "" });
  const [promptState, setPromptState] = useState({
    title: "",
    message: "",
    defaultValue: "",
    options: null as { name: string; label: string }[] | null,
  });
  const [promptResolve, setPromptResolve] = useState<((v: string | null) => void) | null>(null);

  const showAlert = useCallback((title: string, message: string) => {
    return new Promise<void>((resolve) => {
      setAlertState({ title, message });
      setModal("alert");
      (window as unknown as { __alertResolve?: () => void }).__alertResolve = resolve;
    });
  }, []);

  const showPrompt = useCallback(
    (
      title: string,
      message: string,
      defaultValue: string = "",
      options?: { name: string; label: string }[] | null
    ) =>
      new Promise<string | null>((resolve) => {
        setPromptState({ title, message, defaultValue, options: options ?? null });
        setModal("prompt");
        setPromptResolve(() => resolve);
      }),
    []
  );

  const closeAlert = useCallback(() => {
    setModal(null);
    (window as unknown as { __alertResolve?: () => void }).__alertResolve?.();
  }, []);

  const resolvePrompt = useCallback((value: string | null) => {
    promptResolve?.(value);
    setModal(null);
    setPromptResolve(null);
  }, [promptResolve]);

  const cancelPrompt = useCallback(() => {
    promptResolve?.(null);
    setModal(null);
    setPromptResolve(null);
  }, [promptResolve]);

  return {
    modal,
    setModal,
    alertState,
    promptState,
    promptResolve,
    showAlert,
    showPrompt,
    closeAlert,
    resolvePrompt,
    cancelPrompt,
  };
}
