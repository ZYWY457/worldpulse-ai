from ai.ai_client import AIClient
from ai.prompts import SOCIAL_WRITER_PROMPT
import json
import logging

logger = logging.getLogger(__name__)

class SocialMediaWriter:
    def __init__(self):
        self.ai_client = AIClient()

    def generate_social_content(self, title, ai_summary, source):
        prompt_content = SOCIAL_WRITER_PROMPT.format(
            title=title,
            summary=ai_summary,
            source=source
        )
        
        try:
            # The AI client expects a system prompt and user content. 
            # For social media generation, the prompt_content itself contains all instructions.
            # We can pass an empty string or a placeholder for the user content if the prompt is self-contained.
            response = self.ai_client.analyze(prompt_content, "")
            if response and isinstance(response, dict):
                return response
            else:
                logger.error(f"AI returned non-dict response for social media: {response}")
                return None
        except Exception as e:
            logger.error(f"Error generating social media content: {e}")
            return None
