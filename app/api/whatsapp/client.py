## 5. WhatsApp Client (`app/api/whatsapp/client.py`)
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import structlog

import httpx  # Replace requests with httpx for async support
from ...config.settings import config

logger = structlog.get_logger(__name__)

@dataclass
class WhatsAppMessage:
    """WhatsApp message data structure"""
    to: str
    type: str
    content: Dict[str, Any]
    message_id: Optional[str] = None

@dataclass
class WhatsAppContact:
    """WhatsApp contact information"""
    phone: str
    name: Optional[str] = None
    profile_picture: Optional[str] = None

class WhatsAppClient:
    """Enhanced WhatsApp Business API client"""
    
    def __init__(self):
        self.api_url = f"https://graph.facebook.com/v18.0/{config.WHATSAPP_PHONE_NUMBER_ID}"
        self.headers = {
            "Authorization": f"Bearer {config.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
    
    async def send_text_message(self, to: str, text: str) -> Optional[str]:
        """Send a text message"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text}
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    headers=self.headers,
                    json=payload
                )
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('messages', [{}])[0].get('id')
                logger.info("Text message sent successfully", 
                           to=to, message_id=message_id)
                return message_id
            else:
                logger.error("Failed to send text message", 
                           status_code=response.status_code, 
                           response=response.text, to=to)
                return None
                
        except Exception as e:
            logger.error("Error sending text message", error=str(e), to=to)
            return None
    
    async def send_template_message(self, to: str, template_name: str, 
                                  language_code: str = "en", 
                                  parameters: List[str] = None) -> Optional[str]:
        """Send a template message"""
        try:
            components = []
            
            if parameters:
                components.append({
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": param} for param in parameters
                    ]
                })
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language_code},
                    "components": components
                }
            }
            


            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    headers=self.headers,
                    json=payload
                )
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('messages', [{}])[0].get('id')
                logger.info("Template message sent successfully", 
                           to=to, template=template_name, message_id=message_id)
                return message_id
            else:
                logger.error("Failed to send template message", 
                           status_code=response.status_code, 
                           response=response.text, to=to, template=template_name)
                return None
                
        except Exception as e:
            logger.error("Error sending template message", 
                        error=str(e), to=to, template=template_name)
            return None
    
    async def send_interactive_message(self, to: str, header: str, body: str, 
                                     buttons: List[Dict[str, str]]) -> Optional[str]:
        """Send an interactive message with buttons"""
        try:
            interactive_buttons = []
            for i, button in enumerate(buttons[:3]):  # WhatsApp allows max 3 buttons
                interactive_buttons.append({
                    "type": "reply",
                    "reply": {
                        "id": f"btn_{i}",
                        "title": button.get("title", "")[:20]  # Max 20 chars
                    }
                })
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "header": {"type": "text", "text": header},
                    "body": {"text": body},
                    "action": {"buttons": interactive_buttons}
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    headers=self.headers,
                    json=payload
                )
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('messages', [{}])[0].get('id')
                logger.info("Interactive message sent successfully", 
                           to=to, message_id=message_id)
                return message_id
            else:
                logger.error("Failed to send interactive message", 
                           status_code=response.status_code, 
                           response=response.text, to=to)
                return None
                
        except Exception as e:
            logger.error("Error sending interactive message", error=str(e), to=to)
            return None
    
    async def send_list_message(self, to: str, header: str, body: str, 
                              button_text: str, sections: List[Dict[str, Any]]) -> Optional[str]:
        """Send a list message"""
        try:
            list_sections = []
            for section in sections:
                rows = []
                for row in section.get('rows', []):
                    rows.append({
                        "id": row.get('id', ''),
                        "title": row.get('title', '')[:24],  # Max 24 chars
                        "description": row.get('description', '')[:72]  # Max 72 chars
                    })
                
                list_sections.append({
                    "title": section.get('title', '')[:24],
                    "rows": rows[:10]  # Max 10 rows per section
                })
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {"type": "text", "text": header},
                    "body": {"text": body},
                    "action": {
                        "button": button_text[:20],  # Max 20 chars
                        "sections": list_sections[:10]  # Max 10 sections
                    }
                }
            }
            

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    headers=self.headers,
                    json=payload
                )
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('messages', [{}])[0].get('id')
                logger.info("List message sent successfully", 
                           to=to, message_id=message_id)
                return message_id
            else:
                logger.error("Failed to send list message", 
                           status_code=response.status_code, 
                           response=response.text, to=to)
                return None
                
        except Exception as e:
            logger.error("Error sending list message", error=str(e), to=to)
            return None
    
    async def send_media_message(self, to: str, media_type: str, 
                               media_id: str, caption: str = None) -> Optional[str]:
        """Send a media message (image, document, audio, video)"""
        try:
            media_payload = {"id": media_id}
            if caption:
                media_payload["caption"] = caption
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": media_type,
                media_type: media_payload
            }
            
            # response = requests.post(
            #     f"{self.api_url}/messages",
            #     headers=self.headers,
            #     data=json.dumps(payload)
            # )

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    headers=self.headers,
                    json=payload
                )
            
            if response.status_code == 200:
                result = response.json()
                message_id = result.get('messages', [{}])[0].get('id')
                logger.info("Media message sent successfully", 
                           to=to, media_type=media_type, message_id=message_id)
                return message_id
            else:
                logger.error("Failed to send media message", 
                           status_code=response.status_code, 
                           response=response.text, to=to)
                return None
                
        except Exception as e:
            logger.error("Error sending media message", 
                        error=str(e), to=to, media_type=media_type)
            return None
    
    async def mark_message_as_read(self, message_id: str) -> bool:
        """Mark a message as read"""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/messages",
                    headers=self.headers,
                    json=payload
                )
            
            if response.status_code == 200:
                logger.info("Message marked as read", message_id=message_id)
                return True
            else:
                logger.error("Failed to mark message as read", 
                           status_code=response.status_code, 
                           response=response.text, message_id=message_id)
                return False
                
        except Exception as e:
            logger.error("Error marking message as read", 
                        error=str(e), message_id=message_id)
            return False
    
    async def get_media_url(self, media_id: str) -> Optional[str]:
        """Get media URL from media ID"""
        try:
            # response = requests.get(
            #     f"https://graph.facebook.com/v18.0/{media_id}",
            #     headers=self.headers
            # )
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://graph.facebook.com/v18.0/{media_id}",
                    headers=self.headers  
                )
            
            if response.status_code == 200:
                result = response.json()
                media_url = result.get('url')
                logger.info("Media URL retrieved", media_id=media_id, url=media_url)
                return media_url
            else:
                logger.error("Failed to get media URL", 
                           status_code=response.status_code, 
                           response=response.text, media_id=media_id)
                return None
                
        except Exception as e:
            logger.error("Error getting media URL", error=str(e), media_id=media_id)
            return None
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Verify webhook subscription"""
        if mode == "subscribe" and token == config.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            logger.info("Webhook verified successfully")
            return challenge
        else:
            logger.warning("Webhook verification failed", mode=mode, token=token)
            return None
    
    async def get_business_profile(self) -> Optional[Dict[str, Any]]:
        """Get business profile information"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}",
                    headers=self.headers,
                    params={"fields": "about,address,description,email,profile_picture_url,websites"}
                )
            
            if response.status_code == 200:
                profile = response.json()
                logger.info("Business profile retrieved")
                return profile
            else:
                logger.error("Failed to get business profile", 
                        status_code=response.status_code, 
                        response=response.text)
                return None
                
        except Exception as e:
            logger.error("Error getting business profile", error=str(e))
            return None

    async def update_business_profile(self, profile_data: Dict[str, Any]) -> bool:
        """Update business profile"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}",
                    headers=self.headers,
                    json=profile_data  # Use json parameter instead of data=json.dumps()
                )
            
            if response.status_code == 200:
                logger.info("Business profile updated successfully")
                return True
            else:
                logger.error("Failed to update business profile", 
                        status_code=response.status_code, 
                        response=response.text)
                return False
                
        except Exception as e:
            logger.error("Error updating business profile", error=str(e))
            return False

# Create global client instance
whatsapp_client = WhatsAppClient()