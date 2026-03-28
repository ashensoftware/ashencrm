"""
Módulo para construir mensajes de WhatsApp personalizados y persuasivos.
"""

from backend.domain.prospect import Prospect


def build_whatsapp_message(prospect: Prospect) -> str:
    """
    Construye un mensaje altamente personalizado para el prospecto.
    """
    name = prospect.name
    category = prospect.category
    demo_url = prospect.demo_url
    prompt_data = prospect.prompt_used

    message = f"""
Hola, equipo de *{name }*! 👋

He estado siguiendo su trabajo en Instagram y me encanta lo que están haciendo en el sector de *{category }*. 🚀

Sin embargo, he notado que aún no tienen una presencia web optimizada para captar clientes en Google. Me tomé la libertad de diseñarles una propuesta visual de cómo podría verse su nueva página web:

✨ **Ver Demo Personalizada:** {demo_url }

Diseñé esto pensando en la estética minimalista y moderna que su marca merece. 

¿Les gustaría que charláramos 5 minutos sobre cómo esto podría ayudarles a escalar sus ventas este mes?

¡Quedo atento! 😊
""".strip()

    return message


if __name__ == "__main__":

    mock_p = Prospect(
        name="Café Central",
        category="Cafetería",
        demo_url="https://demo-cafe.lovable.app",
    )
    print("--- MENSAJE PARA WHATSAPP ---")
    print(build_whatsapp_message(mock_p))
