import type { LucideIcon } from "lucide-react";
import {
  Bike,
  Briefcase,
  Building2,
  CakeSlice,
  Car,
  Cat,
  Circle,
  Coffee,
  Dog,
  Dumbbell,
  Factory,
  Flower2,
  GraduationCap,
  Hammer,
  Heart,
  Home,
  Hospital,
  Hotel,
  Landmark,
  Laptop,
  Milk,
  Paintbrush,
  Pill,
  Pizza,
  Scissors,
  Shirt,
  ShoppingBag,
  Sparkles,
  Stethoscope,
  Store,
  TreePine,
  Truck,
  Utensils,
  UtensilsCrossed,
  Wheat,
  Wine,
  Wrench,
} from "lucide-react";

/** Opciones del selector: id coincide con el nombre del export de Lucide (persistido en BD). */
export const CATEGORY_ICON_PICKER: { id: string; label: string; Icon: LucideIcon }[] = [
  { id: "Coffee", label: "Café", Icon: Coffee },
  { id: "UtensilsCrossed", label: "Restaurante", Icon: UtensilsCrossed },
  { id: "Utensils", label: "Comida", Icon: Utensils },
  { id: "Pizza", label: "Pizza", Icon: Pizza },
  { id: "Wine", label: "Bar / vinos", Icon: Wine },
  { id: "CakeSlice", label: "Repostería", Icon: CakeSlice },
  { id: "Dumbbell", label: "Gimnasio", Icon: Dumbbell },
  { id: "Scissors", label: "Peluquería / barbería", Icon: Scissors },
  { id: "Sparkles", label: "Estética / spa", Icon: Sparkles },
  { id: "Stethoscope", label: "Salud", Icon: Stethoscope },
  { id: "Hospital", label: "Hospital / clínica", Icon: Hospital },
  { id: "Pill", label: "Farmacia", Icon: Pill },
  { id: "Dog", label: "Veterinaria / mascotas", Icon: Dog },
  { id: "Cat", label: "Mascotas", Icon: Cat },
  { id: "ShoppingBag", label: "Tienda", Icon: ShoppingBag },
  { id: "Shirt", label: "Ropa", Icon: Shirt },
  { id: "Store", label: "Comercio", Icon: Store },
  { id: "Wrench", label: "Taller / servicio", Icon: Wrench },
  { id: "Hammer", label: "Ferretería", Icon: Hammer },
  { id: "Car", label: "Automotor", Icon: Car },
  { id: "Truck", label: "Logística", Icon: Truck },
  { id: "Bike", label: "Bici / movilidad", Icon: Bike },
  { id: "Building2", label: "Oficinas / edificio", Icon: Building2 },
  { id: "Briefcase", label: "Negocios", Icon: Briefcase },
  { id: "Factory", label: "Industria", Icon: Factory },
  { id: "Hotel", label: "Hotel / hospedaje", Icon: Hotel },
  { id: "Landmark", label: "Turismo", Icon: Landmark },
  { id: "GraduationCap", label: "Educación", Icon: GraduationCap },
  { id: "Laptop", label: "Tech / coworking", Icon: Laptop },
  { id: "Home", label: "Hogar", Icon: Home },
  { id: "TreePine", label: "Exterior / parques", Icon: TreePine },
  { id: "Flower2", label: "Floristería", Icon: Flower2 },
  { id: "Paintbrush", label: "Diseño / arte", Icon: Paintbrush },
  { id: "Wheat", label: "Alimentos / agrícola", Icon: Wheat },
  { id: "Milk", label: "Lácteos / panadería", Icon: Milk },
  { id: "Heart", label: "Cuidado / bienestar", Icon: Heart },
];

const ICON_BY_ID: Record<string, LucideIcon> = Object.fromEntries(
  CATEGORY_ICON_PICKER.map(({ id, Icon }) => [id, Icon])
);

export function LucideCategoryIcon({
  iconId,
  size = 22,
  className,
}: {
  iconId?: string;
  size?: number;
  className?: string;
}) {
  const Cmp = iconId ? ICON_BY_ID[iconId] : undefined;
  if (!Cmp) {
    return <Circle size={size} className={className} strokeWidth={1.2} style={{ opacity: 0.35 }} />;
  }
  return <Cmp size={size} className={className} />;
}

export function getCategoryIconLabel(iconId: string): string | undefined {
  return CATEGORY_ICON_PICKER.find((o) => o.id === iconId)?.label;
}
