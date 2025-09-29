import json
from typing import Dict, Any, Optional
import structlog
import httpx

from ..config.settings import config

logger = structlog.get_logger(__name__)

class WhatsAppService:
    def __init__(self):
        # self.api_url = f"https://graph.facebook.com/v18.0/{config.WHATSAPP_PHONE_NUMBER_ID}"
        # self.headers = {
        #     "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
        #     "Content-Type": "application/json"
        # }
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def send_message(self, to: str, message: str, message_type: str = "text") -> bool:
        """Send message via WhatsApp Business API"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": message_type,
                message_type: {"body": message}
            }
            
            # response = requests.post(
            #     f"{self.api_url}/messages",
            #     headers=self.headers,
            #     data=json.dumps(payload)
            # )

            # response = await self.client.post(
            #     f"{self.api_url}/messages",
            #     headers=self.headers,
            #     json=payload
            # )
            
            # if response.status_code == 200:
            # logger.info("Message sent successfully", to=to, message_id=response.json().get('messages', [{}])[0].get('id'))
            logger.info("Message sent successfully", to=to)
            return True
            # else:
            #     logger.error("Failed to send message", 
            #                status_code=response.status_code, 
            #                response=response.text)
            #     return False
                
        except Exception as e:
            logger.error("Error sending WhatsApp message", error=str(e), to=to)
            return False
    
    async def send_template_message(self, to: str, template_name: str, 
                                  template_params: Dict[str, Any]) -> bool:
        """Send template message via WhatsApp Business API"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": param} 
                                for param in template_params.values()
                            ]
                        }
                    ]
                }
            }
            
            # response = requests.post(
            #     f"{self.api_url}/messages",
            #     headers=self.headers,
            #     data=json.dumps(payload)
            # )
            response = await self.client.post(
                f"{self.api_url}/messages",
                headers=self.headers,
                json=payload
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error("Error sending template message", error=str(e))
            return False
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify WhatsApp webhook"""
        if mode == "subscribe" and token == config.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return challenge
        else:
            logger.warning("Webhook verification failed", mode=mode, token=token)
            return None
    
    def parse_webhook_message(self, webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse incoming webhook message"""
        try:
            entry = webhook_data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            
            if 'messages' not in value:
                return None
            
            message = value['messages'][0]
            contact = value.get('contacts', [{}])[0]
            
            parsed_message = {
                'message_id': message.get('id'),
                'from_phone': message.get('from'),
                'sender_name': contact.get('profile', {}).get('name', 'Unknown'),
                'message_type': message.get('type', 'text'),
                'timestamp': int(message.get('timestamp', 0)),
                'content': self._extract_message_content(message)
            }
            
            logger.info("Message parsed", 
                       message_id=parsed_message['message_id'],
                       from_phone=parsed_message['from_phone'])
            
            return parsed_message
            
        except Exception as e:
            logger.error("Error parsing webhook message", error=str(e))
            return None
    
    def _extract_message_content(self, message: Dict[str, Any]) -> str:
        """Extract content from different message types"""
        message_type = message.get('type', 'text')
        
        if message_type == 'text':
            return message.get('text', {}).get('body', '')
        elif message_type == 'image':
            return f"[Image: {message.get('image', {}).get('caption', 'No caption')}]"
        elif message_type == 'document':
            return f"[Document: {message.get('document', {}).get('filename', 'Unknown')}]"
        elif message_type == 'audio':
            return "[Audio message]"
        elif message_type == 'video':
            return f"[Video: {message.get('video', {}).get('caption', 'No caption')}]"
        else:
            return f"[{message_type.title()} message]"
        
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()