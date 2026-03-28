import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  startScrape,
  reviewProspect,
  updateProspect,
  fetchRandomProspect,
  sendWhatsApp,
  createProspect,
} from "../api";
import { MSG, LABELS, DEFAULT_CITY, DEFAULT_SCRAPE_LIMIT } from "../constants";
import { useModals } from "./useModals";
import { useScanner } from "./useScanner";
import type { Prospect, AppSettings } from "../types";

export function useAppActions(
  refresh: (silent?: boolean) => Promise<void>,
  refreshCatalog: () => Promise<void>,
  catalog: { name: string; label: string }[],
  appSettings: AppSettings | null
) {
  const navigate = useNavigate();
  const modals = useModals();
  const scanner = useScanner();

  const [selectedProspect, setSelectedProspect] = useState<Prospect | null>(null);
  const [scrapeFormOpen, setScrapeFormOpen] = useState(false);
  const [registrySearch, setRegistrySearch] = useState("");
  const [tinderHistory, setTinderHistory] = useState<Prospect[]>([]);
  const [editForm, setEditForm] = useState({ name: "", category: "", phone: "", address: "" });

  const handleHexClick = useCallback(
    async (_hex: unknown, latlng: { lat: number; lng: number }) => {
      const opts = [{ name: "*", label: LABELS.SCRAPE_ALL_AUTO }, ...catalog];
      const res = await modals.showPrompt(LABELS.NEW_SEARCH_ZONE, LABELS.CATEGORY_SEARCH_PROMPT, "*", opts);
      if (!res) return;
      const city = appSettings?.default_city ?? DEFAULT_CITY;
      const limit = appSettings?.default_scrape_limit ?? DEFAULT_SCRAPE_LIMIT;
      const r = await startScrape({ category: res, city, limit, lat: latlng.lat, lon: latlng.lng });
      if (r.ok) { modals.setModal("scanner"); scanner.start(refresh); }
    },
    [catalog, refresh, modals, scanner, appSettings]
  );

  const handleScrape = useCallback(async () => {
    const category = (document.getElementById("scrape-category") as HTMLSelectElement)?.value;
    const limit = (document.getElementById("scrape-limit") as HTMLInputElement)?.value || String(appSettings?.default_scrape_limit ?? DEFAULT_SCRAPE_LIMIT);
    if (!category) return modals.showAlert(MSG.ERROR, MSG.ENTER_CATEGORY);
    const city = appSettings?.default_city ?? DEFAULT_CITY;
    const r = await startScrape({ category, city, limit: parseInt(limit, 10) });
    if (r.ok) { modals.setModal("scanner"); scanner.start(refresh); }
    else { const err = await r.json(); modals.showAlert(MSG.ERROR, MSG.SCRAPE_START_FAIL(err.detail)); }
  }, [refresh, modals, scanner, appSettings]);

  const handleReview = useCallback(
    async (action: string) => {
      if (!selectedProspect) return;
      const r = await reviewProspect(selectedProspect.name, action);
      if (!r.ok) return;
      await refresh();
      const next = await fetchRandomProspect("scraped");
      if (next && "message" in next) {
        await modals.showAlert(MSG.FINISH, next.message || MSG.NO_LEADS);
        setSelectedProspect(null);
        navigate("/panel");
      } else if (next?.name) {
        setSelectedProspect(next as Prospect);
      } else {
        setSelectedProspect(null);
      }
    },
    [selectedProspect, refresh, modals, navigate]
  );

  const handleTinderNext = useCallback(async () => {
    navigate("/tinder");
    setTinderHistory((prev) => selectedProspect ? [...prev, selectedProspect] : prev);
    const p = await fetchRandomProspect("scraped");
    if (p && "message" in p) {
      await modals.showAlert(MSG.FINISH, p.message || MSG.NO_LEADS_NEW);
      setSelectedProspect(null);
      navigate("/panel");
      return;
    }
    if (p?.name) setSelectedProspect(p as Prospect);
  }, [modals, selectedProspect, navigate]);

  const handleTinderPrev = useCallback(() => {
    if (tinderHistory.length > 0) {
      setSelectedProspect(tinderHistory[tinderHistory.length - 1]);
      setTinderHistory((curr) => curr.slice(0, -1));
    }
  }, [tinderHistory]);

  const handleEditSubmit = useCallback(async () => {
    if (!selectedProspect) return;
    const r = await updateProspect(selectedProspect.name, editForm);
    if (r.ok) {
      modals.setModal(null);
      await modals.showAlert(MSG.SUCCESS, MSG.LEAD_UPDATED);
      refresh(true);
      setSelectedProspect({ ...selectedProspect, ...editForm });
    }
  }, [selectedProspect, editForm, modals, refresh]);

  const handleCategoryDelete = useCallback(
    async (name: string) => {
      const confirm = await modals.showPrompt(MSG.DELETE, MSG.TYPE_BORRAR(name));
      if (confirm === "BORRAR") {
        await fetch(`/api/catalog/categories/${encodeURIComponent(name)}`, { method: "DELETE" });
        await refreshCatalog();
      }
    },
    [modals, refreshCatalog]
  );

  const handleCategoryAdd = useCallback(async () => {
    const name = await modals.showPrompt(LABELS.NEW_CATEGORY, LABELS.CATEGORY_ID_PROMPT);
    if (!name) return;
    const label = await modals.showPrompt(LABELS.NAME, LABELS.CATEGORY_LABEL_PROMPT);
    if (!label) return;
    await fetch("/api/catalog/categories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, label }),
    });
    await refreshCatalog();
  }, [modals, refreshCatalog]);

  const handleAdvanceStatus = useCallback(async (nextStatus: string) => {
    if (!selectedProspect) return;
    const r = await updateProspect(selectedProspect.name, { status: nextStatus });
    if (r.ok) { await refresh(); setSelectedProspect({ ...selectedProspect, status: nextStatus }); }
  }, [selectedProspect, refresh]);

  const handleGenerateDemo = useCallback(async () => {
    if (!selectedProspect) return;
    const url = await modals.showPrompt("Ingresar URL de Demo", "Pega el enlace de Lovable que creaste para este cliente:");
    if (!url) return;
    const r = await updateProspect(selectedProspect.name, { demo_url: url, status: "demo_created" });
    if (r.ok) { modals.showAlert(MSG.SUCCESS, "Demo guardada correctamente"); refresh(); }
  }, [selectedProspect, modals, refresh]);

  const handleWhatsApp = useCallback(async () => {
    if (!selectedProspect) return;
    await sendWhatsApp(selectedProspect.name);
    modals.showAlert("WhatsApp", MSG.WHATSAPP_SENDING);
  }, [selectedProspect, modals]);

  const handleAddProspectSubmit = useCallback(async (data: Partial<Prospect>) => {
    try {
      const r = await createProspect(data);
      if (r.ok) {
        modals.setModal(null);
        await modals.showAlert(MSG.SUCCESS, "Prospecto creado exitosamente.");
        refresh(true);
      } else {
        const err = await r.json();
        await modals.showAlert(MSG.ERROR, err.detail || "Error al crear el prospecto.");
      }
    } catch (e: any) {
      await modals.showAlert(MSG.ERROR, "Error de red al crear el prospecto.");
    }
  }, [modals, refresh]);

  return {
    modals,
    scanner,
    selectedProspect,
    setSelectedProspect,
    scrapeFormOpen,
    setScrapeFormOpen,
    registrySearch,
    setRegistrySearch,
    tinderHistory,
    editForm,
    setEditForm,
    handleHexClick,
    handleScrape,
    handleReview,
    handleTinderNext,
    handleTinderPrev,
    handleEditSubmit,
    handleCategoryDelete,
    handleCategoryAdd,
    handleAdvanceStatus,
    handleGenerateDemo,
    handleWhatsApp,
    handleAddProspectSubmit,
  };
}
