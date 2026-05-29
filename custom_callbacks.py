from litellm.integrations.custom_logger import CustomLogger
import litellm

class TokenClamper(CustomLogger):
    def __init__(self):
        super().__init__()

    async def async_pre_call_hook(
        self, 
        user_api_key_dict, 
        cache, 
        data: dict, 
        call_type: str
    ):
        # Clamp max_tokens and max_completion_tokens to a reasonable limit (e.g. 4096 or 8192)
        # to prevent:
        # 1. exceeding context window length (e.g. 32000 output requested + input tokens > model context length)
        # 2. openrouter credit limit error ("You requested up to 32000 tokens, but can only afford 15561")
        
        for key in ["max_tokens", "max_completion_tokens"]:
            if key in data and data[key] is not None:
                original_value = data[key]
                model = data.get("model", "")
                
                # Default limit to 4096, but deepseek/claude-t2/claude-t3 can go up to 8192
                limit = 4096
                if "deepseek" in model or "claude-t3" in model or "claude-t2" in model:
                    limit = 8192
                
                if original_value > limit:
                    data[key] = limit
                    print(f"[TokenClamper] Clamping {key} from {original_value} to {limit} for model {model}", flush=True)

        return data

proxy_handler_instance = TokenClamper()
