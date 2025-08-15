from django.shortcuts import render
from vonage_voice import Talk
# Create your views here.
from django.http import JsonResponse, HttpResponse
# Stub GET endpoint for /api/answer
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
import logging
import json
import os
from vonage import Vonage, Auth, HttpClientOptions
from vonage_messages import Sms


logger = logging.getLogger(__name__)

@csrf_exempt
@require_GET
def answer(request):
    logger.info(f"Payload for /api/answer: {request.GET}")
    from_number = request.GET.get('from', 'unknown')
    
    try:
        # Import the LLM service (here to avoid import errors if LLM is not set up)
        from .llm_service import get_dad_joke
        
        # Get a dad joke from the LLM
        dad_joke = get_dad_joke()
        
        # Create a greeting followed by the joke
        greeting = f"Hello, caller from {from_number}! Here's your dad joke for today: "
        full_message = greeting + dad_joke
        
        # Create the response data as a list with the Talk object
        response_data = [
            Talk(text=full_message).model_dump(
                by_alias=True, exclude_none=True
            )
        ]
        
        logger.info(f"Generated joke: {dad_joke}")
    except Exception as e:
        # Fallback in case the LLM service fails
        logger.error(f"Error generating joke: {str(e)}")
        response_data = [
            Talk(text=f"Hello from {from_number}! I'm having trouble thinking of a joke right now. Please call back later!").model_dump(
                by_alias=True, exclude_none=True
            )
        ]
    
    # Return a JsonResponse with safe=False to allow non-dict objects
    return JsonResponse(response_data, safe=False)

@csrf_exempt
@require_POST
def event(request):
    logger.info(f"Payload for /api/event: {request.POST}")
    return HttpResponse(status=200)

@csrf_exempt
@require_GET
def fallback(request):
    logger.info(f"Payload for /api/fallback: {request.GET}")
    return HttpResponse(status=200)

# SMS webhook handler for /api/inbound
@csrf_exempt
@require_POST
def inbound(request):
    """
    Handle inbound SMS webhook from Vonage and respond with a dad joke
    """
    try:
        # Parse the incoming JSON webhook payload
        payload = json.loads(request.body)
        logger.info(f"Inbound SMS webhook received: {payload}")
        
        # Extract the sender's phone number
        from_number = payload.get('msisdn')
        
        if not from_number:
            logger.error("Missing 'from' number in webhook payload")
            return HttpResponse(status=400)
        
        # Get a dad joke from the LLM service
        try:
            from .llm_service import get_dad_joke
            dad_joke = get_dad_joke()
        except Exception as e:
            logger.error(f"Error getting dad joke from LLM: {e}")
            dad_joke = "Why don't scientists trust atoms? Because they make up everything!"
        
        # Initialize the Vonage client
        auth = Auth(api_key=os.getenv("VONAGE_API_KEY"), api_secret=os.getenv("VONAGE_API_SECRET"))
        vonage_client = Vonage(auth=auth)
        
        # Send the SMS response with the dad joke
        message = Sms(
            from_=os.getenv("VONAGE_PHONE_NUMBER"),  # Your Vonage number
            to=from_number,
            text=f"Dad Joke Hotline: {dad_joke}"
        )

        response_data = vonage_client.messages.send(message)
        
        # Log the response from Vonage
        if response_data["messages"][0]["status"] == "0":
            logger.info(f"SMS sent successfully to {from_number}")
        else:
            logger.error(f"SMS failed with error: {response_data['messages'][0]['error-text']}")
        
        # Return a 200 OK to the webhook
        return HttpResponse(status=200)
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        return HttpResponse(status=400)
        
    except Exception as e:
        logger.error(f"Error processing inbound webhook: {str(e)}")
        return HttpResponse(status=500)
