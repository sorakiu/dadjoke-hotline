from django.conf import settings
from openai import OpenAI

# Initialize the OpenAI client with OpenRouter's base URL
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

def get_dad_joke():
    """
    Generate a dad joke using OpenRouter's LLM API.
    Returns a dad joke as a string.
    """
    try:
        # Call OpenAI client with proper extra_headers parameter
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": settings.OPENROUTER_REFERER,  # Optional but good practice
                "X-Title": "Dad Joke Hotline",  # Optional title for tracking usage
            },
            model="anthropic/claude-3-haiku",  # Use a specific model instead of auto
            messages=[
                {"role": "system", "content": "You are a dad who loves telling classic dad jokes. Keep your responses short and focused on the joke only."},
                {"role": "user", "content": "Tell me a short, clean dad joke that would make kids groan."}
            ],
            temperature=0.7,
            max_tokens=100
        )
        
        # Extract the joke from the response
        joke = response.choices[0].message.content
        return joke.strip()
    
    except Exception as e:
        # Log the error and return a fallback joke
        print(f"Error calling LLM API: {str(e)}")
        return "Why don't scientists trust atoms? Because they make up everything!"
