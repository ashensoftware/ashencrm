"""
Servicio para orquestar el envío de mensajes a prospectos.
"""

import asyncio
from backend.outreach.message_builder import build_whatsapp_message
from backend.outreach.whatsapp import WhatsAppAutomation
from backend.domain.prospect import Prospect, ProspectStatus


class OutreachService:
    def __init__(self, db):
        self.db = db
        self.wa = WhatsAppAutomation()

    async def send_proposal(self, prospect: Prospect) -> dict:
        """
        Envía la propuesta personalizada vía WhatsApp.
        """
        if not prospect.demo_url:
            return {"error": "El prospecto no tiene un demo generado aún."}

        phone = prospect.get_best_phone()
        if not phone:
            return {"error": "No se encontró un número de teléfono válido."}

        message = build_whatsapp_message(prospect, self.db)

        try:

            await self.wa.start(headless=False)
            if not await self.wa.login():
                return {"error": "No se pudo iniciar sesión en WhatsApp."}

            success = await self.wa.send_message(phone, message)

            if success:

                from datetime import datetime

                self.db.update_status(
                    prospect.name,
                    prospect.address,
                    status=ProspectStatus.CONTACTED,
                    is_contacted=True,
                    contacted_at=datetime.now().isoformat(),
                )
                return {
                    "success": True,
                    "message": f"Propuesta enviada a {prospect .name }",
                }
            else:
                return {"error": "Fallo al enviar el mensaje por WhatsApp."}

        except Exception as e:
            print(f"[OutreachService] Error: {e }")
            return {"error": str(e)}
        finally:
            await self.wa.stop()
