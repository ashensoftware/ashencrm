"""Builds demo prompts from prospect data."""

from backend.domain.prospect import Prospect


def build_demo_prompt(prospect: Prospect) -> str:
    name = prospect.name
    category = prospect.category
    bio = prospect.ig_bio or "No disponible"
    followers = prospect.ig_followers
    rating = prospect.rating
    return f"""
Eres un experto en Growth Hacking y Diseño Web Minimalista (estilo Apple/Vercel).
Tu objetivo es diseñar una propuesta de valor IRRECHAZABLE para un cliente potencial.

DATOS DEL CLIENTE:
- Nombre: {name }
- Categoría: {category }
- Bio de Instagram: {bio }
- Seguidores: {followers }
- Valoración en Google: {rating }/5

TAREA:
1. Analiza el negocio basándote en su categoría y bio.
2. Define un "Hook" (Gancho) emocional que ataque un problema que tengan.
3. Diseña el contenido para una Landing Page de una sola sección (One-Page) ultra-moderna.
4. Incluye: Un Titular (H1) poderoso, Subtitular, 3 Beneficios clave, CTA creativo.
5. El tono debe ser profesional pero cercano.

FORMATO DE RESPUESTA REQUERIDO (JSON):
{{
  "analysis": "Breve análisis estratégico",
  "hook": "El gancho de venta inicial",
  "landing_content": {{
    "h1": "Título principal",
    "sub": "Subtítulo",
    "benefits": ["b1", "b2", "b3"],
    "cta": "Texto del botón"
  }},
  "color_palette": ["#Hex1", "#Hex2", "Concepto visual"]
}}
""".strip()
