import logging
import sys
from googleapiclient.errors import HttpError
from config.settings import settings, ConfigurationError
from api.youtube_client import YouTubeClient, YouTubeAPIClientError
from utils.logging_config import setup_logging

logger = logging.getLogger("test_connection")

def verify_connection() -> bool:
    """Verifies connection and authentication status with the YouTube Data API v3.
    
    Returns:
        bool: True if connection is successful and verified, False otherwise.
    """
    logger.info("Starting YouTube Data API connection verification...")
    
    try:
        # Initialize client
        client_wrapper = YouTubeClient()
        youtube = client_wrapper.get_service()
        
        # Perform lightweight request: Get details for Google Developers Channel (UC_x5XG1OV2P6uZZ5FSM9Ttw)
        # This call consumes 1 quota point.
        logger.info("Executing lightweight request to YouTube API...")
        request = youtube.channels().list(
            part="id,snippet",
            id="UC_x5XG1OV2P6uZZ5FSM9Ttw"
        )
        response = request.execute()
        
        # Verify response structure
        if "items" in response and len(response["items"]) > 0:
            channel_title = response["items"][0]["snippet"]["title"]
            logger.info("API Authentication successful!")
            logger.info(f"Successfully fetched channel details. Channel Title: '{channel_title}'")
            return True
        else:
            logger.warning("API connection succeeded, but returned an unexpected or empty response.")
            return False
            
    except ConfigurationError as e:
        logger.critical(f"Configuration Error: {e}")
        return False
    except HttpError as e:
        # Parse specific API errors (invalid key, etc.)
        status_code = e.resp.status
        reason = e.reason
        if status_code == 400:
            logger.error(f"HTTP 400 Bad Request: Check your query parameters. Reason: {reason}")
        elif status_code == 403:
            logger.error(
                f"HTTP 403 Forbidden: Verification failed. "
                f"The API key may be invalid, restricted, or YouTube Data API v3 is not enabled. "
                f"Reason: {reason}"
            )
        elif status_code == 429:
            logger.error(f"HTTP 429 Quota Exceeded: Your API limit has been reached. Reason: {reason}")
        else:
            logger.error(f"HTTP Error {status_code} occurred: {e}")
        return False
    except YouTubeAPIClientError as e:
        logger.error(f"YouTube Client Error: {e}")
        return False
    except Exception as e:
        logger.critical(f"Unexpected connection error occurred: {e}", exc_info=True)
        return False

def main() -> None:
    """Main execution entry point."""
    try:
        # Initialize logging
        setup_logging()
    except Exception as e:
        print(f"CRITICAL: Failed to initialize logging: {e}", file=sys.stderr)
        sys.exit(1)
        
    logger.info("=== YouTube Data Tool - Phase 1 Verification ===")
    
    success = verify_connection()
    
    if success:
        logger.info("SUCCESS: Phase 1 foundation is stable and API connection is validated.")
        print("\n[+] Verification SUCCESS: YouTube API connection verified successfully!")
        sys.exit(0)
    else:
        logger.error("FAILED: Phase 1 verification failed. Please review the errors in the logs above.")
        print("\n[-] Verification FAILED: Please check logs/app.log and console output for details.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
