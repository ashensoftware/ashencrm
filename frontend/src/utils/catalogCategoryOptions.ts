import type { CatalogItem } from "../types";

/**
 * Opciones para un &lt;select&gt; de categoría: catálogo global + valor actual si ya no está listado.
 * Mismo criterio para leads y clientes.
 */
export function catalogCategoryOptions(
  catalog: CatalogItem[],
  currentName: string | undefined
): CatalogItem[] {
  const cur = (currentName ?? "").trim();
  if (!cur) return catalog;
  if (catalog.some((c) => c.name === cur)) return catalog;
  return [...catalog, { name: cur, label: `${cur} (histórico)` }];
}
