"""
🌙 Moon Dev's Groq Model Implementation
Built with love by Moon Dev 🚀
"""

from groq import Groq
from termcolor import cprint
from .base_model import BaseModel, ModelResponse

class GroqModel(BaseModel):
    """Implementation for Groq's models"""
    
    AVAILABLE_MODELS = {
        # Production Models
        "mixtral-8x7b-32768": {
            "description": "Mixtral 8x7B - Production - 32k context",
            "input_price": "$0.27/1M tokens",
            "output_price": "$0.27/1M tokens"
        },
        "gemma2-9b-it": {
            "description": "Google Gemma 2 9B - Production - 8k context",
            "input_price": "$0.10/1M tokens",
            "output_price": "$0.10/1M tokens"
        },
        "llama-3.3-70b-versatile": {
            "description": "Llama 3.3 70B Versatile - Production - 128k context",
            "input_price": "$0.70/1M tokens",
            "output_price": "$0.90/1M tokens"
        },
        "llama-3.1-8b-instant": {
            "description": "Llama 3.1 8B Instant - Production - 128k context",
            "input_price": "$0.10/1M tokens",
            "output_price": "$0.10/1M tokens"
        },
        "llama-guard-3-8b": {
            "description": "Llama Guard 3 8B - Production - 8k context",
            "input_price": "$0.20/1M tokens",
            "output_price": "$0.20/1M tokens"
        },
        "llama3-70b-8192": {
            "description": "Llama 3 70B - Production - 8k context",
            "input_price": "$0.70/1M tokens",
            "output_price": "$0.90/1M tokens"
        },
        "llama3-8b-8192": {
            "description": "Llama 3 8B - Production - 8k context",
            "input_price": "$0.10/1M tokens",
            "output_price": "$0.10/1M tokens"
        },
        # Preview Models
        "deepseek-r1-distill-llama-70b": {
            "description": "DeepSeek R1 Distill Llama 70B - Preview - 128k context",
            "input_price": "$0.70/1M tokens",
            "output_price": "$0.90/1M tokens"
        },
        "llama-3.3-70b-specdec": {
            "description": "Llama 3.3 70B SpecDec - Preview - 8k context",
            "input_price": "$0.70/1M tokens",
            "output_price": "$0.90/1M tokens"
        },
        "llama-3.2-1b-preview": {
            "description": "Llama 3.2 1B - Preview - 128k context",
            "input_price": "$0.05/1M tokens",
            "output_price": "$0.05/1M tokens"
        },
        "llama-3.2-3b-preview": {
            "description": "Llama 3.2 3B - Preview - 128k context",
            "input_price": "$0.07/1M tokens",
            "output_price": "$0.07/1M tokens"
        }
    }
    
    def __init__(self, api_key: str, model_name: str = "mixtral-8x7b-32768", **kwargs):
        try:
            cprint(f"\n🌙 Moon Dev's Groq Model Initialization", "cyan")
            
            # Validate API key
            if not api_key or len(api_key.strip()) == 0:
                raise ValueError("API key is empty or None")
            
            cprint(f"🔑 API Key validation:", "cyan")
            cprint(f"  ├─ Length: {len(api_key)} chars", "cyan")
            cprint(f"  ├─ Contains whitespace: {'yes' if any(c.isspace() for c in api_key) else 'no'}", "cyan")
            cprint(f"  └─ Starts with 'gsk_': {'yes' if api_key.startswith('gsk_') else 'no'}", "cyan")
            
            # Validate model name
            cprint(f"\n📝 Model validation:", "cyan")
            cprint(f"  ├─ Requested: {model_name}", "cyan")
            if model_name not in self.AVAILABLE_MODELS:
                cprint(f"  └─ ❌ Invalid model name", "red")
                cprint("\nAvailable models:", "yellow")
                for available_model, info in self.AVAILABLE_MODELS.items():
                    cprint(f"  ├─ {available_model}", "yellow")
                    cprint(f"  │  └─ {info['description']}", "yellow")
                raise ValueError(f"Invalid model name: {model_name}")
            cprint(f"  └─ ✅ Model name valid", "green")
            
            self.model_name = model_name
            
            # Call parent class initialization
            cprint(f"\n📡 Parent class initialization...", "cyan")
            super().__init__(api_key, **kwargs)
            cprint(f"✅ Parent class initialized", "green")
            
        except Exception as e:
            cprint(f"\n❌ Error in Groq model initialization", "red")
            cprint(f"  ├─ Error type: {type(e).__name__}", "red")
            cprint(f"  ├─ Error message: {str(e)}", "red")
            if "api_key" in str(e).lower():
                cprint(f"  ├─ 🔑 This appears to be an API key issue", "red")
                cprint(f"  └─ Please check your GROQ_API_KEY in .env", "red")
            elif "model" in str(e).lower():
                cprint(f"  ├─ 🤖 This appears to be a model name issue", "red")
                cprint(f"  └─ Available models: {list(self.AVAILABLE_MODELS.keys())}", "red")
            raise
    
    def initialize_client(self, **kwargs) -> None:
        """Initialize the Groq client"""
        try:
            cprint(f"\n🔌 Initializing Groq client...", "cyan")
            cprint(f"  ├─ API Key length: {len(self.api_key)} chars", "cyan")
            cprint(f"  ├─ Model name: {self.model_name}", "cyan")
            
            cprint(f"\n  ├─ Creating Groq client...", "cyan")
            self.client = Groq(api_key=self.api_key)
            cprint(f"  ├─ ✅ Groq client created", "green")
            
            # Get list of available models first
            cprint(f"  ├─ Fetching available models from Groq API...", "cyan")
            available_models = self.client.models.list()
            api_models = [model.id for model in available_models.data]
            cprint(f"  ├─ Models available from API: {api_models}", "cyan")
            
            if self.model_name not in api_models:
                cprint(f"  ├─ ⚠️ Requested model not found in API", "yellow")
                cprint(f"  ├─ Falling back to mixtral-8x7b-32768", "yellow")
                self.model_name = "mixtral-8x7b-32768"
            
            # Test the connection with a simple completion
            cprint(f"  ├─ Testing connection with model: {self.model_name}", "cyan")
            test_response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            cprint(f"  ├─ ✅ Test response received", "green")
            cprint(f"  ├─ Response content: {test_response.choices[0].message.content}", "cyan")
            
            model_info = self.AVAILABLE_MODELS.get(self.model_name, {})
            cprint(f"  ├─ ✨ Groq model initialized: {self.model_name}", "green")
            cprint(f"  ├─ Model info: {model_info.get('description', '')}", "cyan")
            cprint(f"  └─ Pricing: Input {model_info.get('input_price', '')} | Output {model_info.get('output_price', '')}", "yellow")
            
        except Exception as e:
            cprint(f"\n❌ Failed to initialize Groq client", "red")
            cprint(f"  ├─ Error type: {type(e).__name__}", "red")
            cprint(f"  ├─ Error message: {str(e)}", "red")
            
            # Check for specific error types
            if "api_key" in str(e).lower():
                cprint(f"  ├─ 🔑 This appears to be an API key issue", "red")
                cprint(f"  ├─ Make sure your GROQ_API_KEY is correct", "red")
                cprint(f"  └─ Key length: {len(self.api_key)} chars", "red")
            elif "model" in str(e).lower():
                cprint(f"  ├─ 🤖 This appears to be a model name issue", "red")
                cprint(f"  ├─ Requested model: {self.model_name}", "red")
                cprint(f"  └─ Available models: {list(self.AVAILABLE_MODELS.keys())}", "red")
            
            if hasattr(e, 'response'):
                cprint(f"  ├─ Response status: {e.response.status_code}", "red")
                cprint(f"  └─ Response body: {e.response.text}", "red")
            
            if hasattr(e, '__traceback__'):
                import traceback
                cprint(f"\n📋 Full traceback:", "red")
                cprint(traceback.format_exc(), "red")
            
            self.client = None
            raise
    
    def generate_response(self, 
        system_prompt: str,
        user_content: str,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> ModelResponse:
        """Generate a response using Groq"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            return ModelResponse(
                content=response.choices[0].message.content.strip(),
                raw_response=response,
                model_name=self.model_name,
                usage=response.usage.model_dump() if hasattr(response, 'usage') else None
            )
            
        except Exception as e:
            cprint(f"❌ Groq generation error: {str(e)}", "red")
            raise
    
    def is_available(self) -> bool:
        """Check if Groq is available"""
        return self.client is not None
    
    @property
    def model_type(self) -> str:
        return "groq" 