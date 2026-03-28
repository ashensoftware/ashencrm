import { useMemo, lazy, Suspense } from "react";
import { Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { Sidebar } from "./organisms/Sidebar";
import { ProspectDetailModal } from "./organisms/modals/ProspectDetailModal";
import { AlertModal, PromptModal, CategoryModal, EditModal, ScannerModal, AddProspectModal } from "./organisms/modals";
import { DashboardPage } from "./pages/DashboardPage";
import { AdminPage } from "./pages/AdminPage"; // Eager: first paint + admin
import { useProspects } from "./hooks/useProspects";
import { useAppActions } from "./hooks/useAppActions";
import { useAppSettings } from "./hooks/useAppSettings";
import { updateProspect, sendWhatsApp } from "./api";
import { MSG, LABELS } from "./constants";

const MapView = lazy(() => import("./organisms/MapView").then((m) => ({ default: m.MapView })));
const TinderPage = lazy(() => import("./pages").then((m) => ({ default: m.TinderPage })));
const KanbanPage = lazy(() => import("./pages").then((m) => ({ default: m.KanbanPage })));
const PanelPage = lazy(() => import("./pages").then((m) => ({ default: m.PanelPage })));

const VIEW_TO_ROUTE: Record<string, string> = { overview: "/", map: "/map", tinder: "/tinder", panel: "/panel", todo: "/kanban", admin: "/admin" };
const ROUTE_TO_VIEW: Record<string, "overview" | "map" | "tinder" | "panel" | "todo" | "admin"> = { "/": "overview", "/map": "map", "/tinder": "tinder", "/panel": "panel", "/kanban": "todo", "/admin": "admin" };

function App() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const currentView = useMemo(() => ROUTE_TO_VIEW[pathname] ?? "overview", [pathname]);

  const { prospects, hexagons, stats, catalog, filters, setFilters, refresh, refreshCatalog } = useProspects();
  const { settings: appSettings, reload: reloadAppSettings } = useAppSettings();
  const actions = useAppActions(refresh, refreshCatalog, catalog, appSettings);
  const { modals, scanner, selectedProspect, setSelectedProspect } = actions;

  return (
    <div className="app-container">
      <Sidebar
        prospects={prospects} stats={stats} catalog={catalog} filters={filters}
        selectedProspect={selectedProspect} currentView={currentView}
        onViewChange={(v) => { navigate(VIEW_TO_ROUTE[v] ?? "/"); if (v === "tinder") actions.handleTinderNext(); }}
        scrapeFormOpen={actions.scrapeFormOpen}
        registrySearch={actions.registrySearch}
        onFiltersChange={setFilters}
        onSelectProspect={(p) => { navigate("/map"); setSelectedProspect(p); modals.setModal("detail"); }}
        onScrapeFormToggle={() => actions.setScrapeFormOpen((o) => !o)}
        onRegistrySearchChange={actions.setRegistrySearch}
        onScrape={actions.handleScrape}
        defaultScrapeLimit={appSettings?.default_scrape_limit}
      />

      <main className="main-content">
        <Suspense fallback={<div style={{display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)'}}>Cargando página...</div>}>
          <Routes>
            <Route path="/" element={<DashboardPage prospects={prospects} />} />
            <Route path="/map" element={<MapView prospects={prospects} hexagons={hexagons} selectedProspect={selectedProspect} onHexClick={actions.handleHexClick} mapCenter={appSettings ? { lat: appSettings.map_center_lat, lng: appSettings.map_center_lng } : undefined} mapZoom={appSettings?.map_zoom} />} />
            <Route path="/tinder" element={
              <TinderPage 
              prospect={selectedProspect}
              onClose={() => { modals.setModal(null); navigate("/panel"); }}
              onReject={() => actions.handleReview("reject")}
              onAccept={() => actions.handleReview("accept")}
              onContact={() => actions.handleReview("contact")}
              onNext={actions.handleTinderNext}
              onPrev={actions.handleTinderPrev}
              hasPrev={actions.tinderHistory.length > 0}
              onAdvanceStatus={actions.handleAdvanceStatus}
              onGenerateDemo={actions.handleGenerateDemo}
              onWhatsApp={actions.handleWhatsApp}
            />
          } />
          <Route path="/kanban" element={
            <KanbanPage prospects={prospects}
              onSelectProspect={(p) => { setSelectedProspect(p); modals.setModal("detail"); }}
              onWhatsApp={async (p) => { await sendWhatsApp(p.name); modals.showAlert("WhatsApp", MSG.WHATSAPP_SENDING); }}
              onChangeStatus={async (name, status) => { const r = await updateProspect(name, { status }); if (r.ok) await refresh(); }}
            />
          } />
            <Route path="/panel" element={
              <PanelPage 
                prospects={prospects} 
                filters={filters} 
                catalog={catalog} 
                onFiltersChange={setFilters} 
                onAddProspect={() => modals.setModal("add")} 
                onSelectProspect={(p) => { setSelectedProspect(p); modals.setModal("detail"); }} 
              />
            } />
            <Route path="/admin" element={
              <AdminPage
                catalog={catalog}
                refreshCatalog={refreshCatalog}
                refreshProspects={() => refresh()}
                onSettingsSaved={reloadAppSettings}
              />
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>

      {modals.modal === "alert" && <AlertModal title={modals.alertState.title} message={modals.alertState.message} onClose={() => { modals.closeAlert(); modals.setModal(null); }} />}
      {modals.modal === "prompt" && modals.promptResolve && <PromptModal title={modals.promptState.title} message={modals.promptState.message} defaultValue={modals.promptState.defaultValue} options={modals.promptState.options} onConfirm={modals.resolvePrompt} onCancel={modals.cancelPrompt} />}
      {(modals.modal === "detail") && selectedProspect && (
        <ProspectDetailModal
          prospect={selectedProspect}
          onClose={() => { modals.setModal(null); if (currentView === "tinder") navigate("/panel"); }}
          onReject={() => actions.handleReview("reject")} onAccept={() => actions.handleReview("accept")} onContact={() => actions.handleReview("contact")}
          onNext={actions.handleTinderNext} onPrev={actions.handleTinderPrev} hasPrev={actions.tinderHistory.length > 0}
          onAdvanceStatus={actions.handleAdvanceStatus} onGenerateDemo={actions.handleGenerateDemo} onWhatsApp={actions.handleWhatsApp}
        />
      )}
      {modals.modal === "edit" && selectedProspect && <EditModal prospect={selectedProspect} form={actions.editForm} catalog={catalog} onFormChange={actions.setEditForm} onClose={() => modals.setModal(null)} onSubmit={actions.handleEditSubmit} />}
      {modals.modal === "add" && <AddProspectModal catalog={catalog} onClose={() => modals.setModal(null)} onSubmit={actions.handleAddProspectSubmit} />}
      {modals.modal === "category" && <CategoryModal catalog={catalog} onClose={() => modals.setModal(null)} onDelete={actions.handleCategoryDelete} onAdd={async () => { await actions.handleCategoryAdd(); modals.setModal(null); }} />}
      {modals.modal === "scanner" && !scanner.minimized && <ScannerModal logs={scanner.logs} active={scanner.active} onMinimize={() => { scanner.minimize(); modals.setModal(null); }} />}
      {scanner.minimized && scanner.active && (
        <div className="floating-scanner" onClick={() => { scanner.restore(); modals.setModal("scanner"); }}>
          <div className="scanner-dot" />
          <div className="scanner-info">
            <span className="scanner-title">{LABELS.SCANNING}</span>
            <span className="scanner-last-log">{scanner.lastLog || MSG.CONNECTING}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
