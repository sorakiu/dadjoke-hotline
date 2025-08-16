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
from vonage_jwt.verify_jwt import verify_signature
from django.conf import settings
from functools import wraps


logger = logging.getLogger(__name__)

def verify_jwt_signature(view_func):
    """
    Decorator to verify JWT signature from Vonage webhooks.
    Expects JWT token in Authorization header as "Bearer <token>".
    Returns 401 Unauthorized if signature is invalid.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            # Get the authorization header
            auth_header = request.headers.get("Authorization", "")
            
            if not auth_header:
                logger.warning("Missing authorization header, available headers are %s", dict(request.headers))
                return HttpResponse("Unauthorized: Missing authorization header", status=401)
            
            # Split the header to get the token after "Bearer "
            auth_parts = auth_header.split()
            
            if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
                logger.warning("Invalid authorization header format")
                return HttpResponse("Unauthorized: Invalid authorization header format", status=401)
            
            token = auth_parts[1].strip()
            
            # Verify the signature using the Vonage secret
            if verify_signature(token, settings.VONAGE_SIGNATURE_SECRET):
                logger.info('Valid JWT signature')
                return view_func(request, *args, **kwargs)
            else:
                logger.warning('Invalid JWT signature')
                return HttpResponse("Unauthorized: Invalid signature", status=401)
                
        except KeyError as e:
            logger.error(f"Missing required header: {e}")
            return HttpResponse("Unauthorized: Missing authorization header", status=401)
        except Exception as e:
            logger.error(f"Error verifying JWT signature: {str(e)}")
            return HttpResponse("Unauthorized: Signature verification failed", status=401)
    
    return wrapper

@csrf_exempt
@require_GET
@verify_jwt_signature
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
@verify_jwt_signature
def event(request):
    try:
        # Try to parse JSON body first (most common for webhooks)
        if request.content_type == 'application/json':
            payload = json.loads(request.body)
            logger.info(f"Payload for /api/event (JSON): {payload}")
        else:
            # Fall back to POST data for form-encoded requests
            payload = dict(request.POST)
            logger.info(f"Payload for /api/event (POST): {payload}")
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON in /api/event, raw body: {request.body.decode('utf-8', errors='ignore')}")
    except Exception as e:
        logger.error(f"Error parsing /api/event payload: {e}")
    
    return HttpResponse(status=200)

@csrf_exempt
@require_GET
@verify_jwt_signature
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
        auth = Auth(api_key=settings.VONAGE_API_KEY, api_secret=settings.VONAGE_API_SECRET)
        vonage_client = Vonage(auth=auth)
        
        # Send the SMS response with the dad joke
        message = Sms(
            from_=settings.VONAGE_PHONE_NUMBER,  # Your Vonage number
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

# Health check endpoint
@require_GET
def healthz(request):
    """
    Simple health check endpoint for monitoring and load balancers.
    Returns 200 OK with basic status information.
    """
    health_data = {
        "status": "healthy",
        "service": "dadjoke-hotline",
        "timestamp": request.META.get("HTTP_DATE", ""),
    }
    return JsonResponse(health_data)
