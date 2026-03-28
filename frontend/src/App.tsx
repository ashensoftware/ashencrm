import { useMemo } from "react";
import { Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import { Sidebar } from "./organisms/Sidebar";
import { MapView } from "./organisms/MapView";
import { ProspectDetailModal } from "./organisms/modals/ProspectDetailModal";
import { AlertModal, PromptModal, CategoryModal, EditModal, ScannerModal } from "./organisms/modals";
import { DashboardPage, KanbanPage, TinderPage, PanelPage } from "./pages";
import { useProspects } from "./hooks/useProspects";
import { useAppActions } from "./hooks/useAppActions";
import { updateProspect, sendWhatsApp } from "./api";
import { MSG, LABELS } from "./constants";

const VIEW_TO_ROUTE: Record<string, string> = { overview: "/", map: "/map", tinder: "/tinder", panel: "/panel", todo: "/kanban" };
const ROUTE_TO_VIEW: Record<string, "overview" | "map" | "tinder" | "panel" | "todo"> = { "/": "overview", "/map": "map", "/tinder": "tinder", "/panel": "panel", "/kanban": "todo" };

function App() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const currentView = useMemo(() => ROUTE_TO_VIEW[pathname] ?? "overview", [pathname]);

  const { prospects, hexagons, stats, catalog, filters, setFilters, refresh, refreshCatalog } = useProspects();
  const actions = useAppActions(refresh, refreshCatalog, catalog);
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
        onCategoryManage={() => modals.setModal("category")}
        onScrape={actions.handleScrape}
      />

      <main className="main-content">
        <Routes>
          <Route path="/" element={<DashboardPage prospects={prospects} />} />
          <Route path="/map" element={<MapView prospects={prospects} hexagons={hexagons} selectedProspect={selectedProspect} onHexClick={actions.handleHexClick} />} />
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
          <Route path="/panel" element={<PanelPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
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
