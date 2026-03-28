import type { ProspectFilters } from "../types";

export function createDefaultFilters(): ProspectFilters {
  return {
    status: "",
    contacted: "",
    has_instagram: "",
    category: "",
    name: "",
  };
}
