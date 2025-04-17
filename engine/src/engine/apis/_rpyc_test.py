import rpyc
import os
from loguru import logger
import sys

# --- Configuration ---
# Match the host and port where your engine's RPyC service is listening
RPYC_HOST = os.getenv("ENGINE_RPYC_HOST", "localhost") # Use localhost if running test on same machine
RPYC_PORT = int(os.getenv("ENGINE_RPYC_PORT", 18861)) # Use the INTERNAL_RPYC_PORT value

# Configure logging for the test script
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# --- Test Function ---
def test_connection():
    conn = None
    try:
        logger.info(f"Attempting to connect to RPyC server at {RPYC_HOST}:{RPYC_PORT}...")

        # Connect to the RPyC server
        # Set allow_public_attrs=True because the service exposes methods directly
        conn = rpyc.connect(
            RPYC_HOST,
            RPYC_PORT,
            config={
                "allow_public_attrs": True, # Need this to access exposed_ methods
                "allow_pickle": False,      # Match server config
                "sync_request_timeout": 30 # Shorter timeout for testing
            }
        )
        logger.info("Connection successful!")

        # Access the remote service root
        remote_service = conn.root
        logger.debug(f"Remote root object: {remote_service}")

        # --- Call a simple exposed method ---
        logger.info("Calling exposed_ping()...")
        try:
            response = remote_service.exposed_ping()
            logger.success(f"Received response from ping: {response}")
            if response != "pong_rpyc":
                logger.error("Ping response mismatch!")
            else:
                 logger.success("Ping test PASSED!")
        except Exception as e:
            logger.error(f"Error calling exposed_ping: {e}", exc_info=True)

        # --- Example: Call another method (e.g., generate UUID) ---
        logger.info("Calling exposed_generate_uuid()...")
        try:
            new_uuid = remote_service.exposed_generate_uuid()
            logger.success(f"Generated UUID remotely: {new_uuid}")
            # Basic validation
            import uuid
            try:
                uuid.UUID(new_uuid)
                logger.success("UUID generation test PASSED!")
            except ValueError:
                logger.error("Generated value is not a valid UUID!")
        except Exception as e:
            logger.error(f"Error calling exposed_generate_uuid: {e}", exc_info=True)

        # --- Example: Call a method requiring context (simulate) ---
        # Note: This requires the service method to handle potential errors gracefully
        # if the module doesn't actually exist in the DB used by the engine.
        logger.info("Calling exposed_get_messages (with dummy context)...")
        dummy_module_id = "test-module-id"
        dummy_profile = "test-profile"
        dummy_session_id = str(uuid.uuid4())
        try:
            # This call might fail if the module/profile doesn't exist,
            # but tests if the RPyC call itself works.
            messages = remote_service.exposed_get_messages(
                module_id=dummy_module_id,
                profile=dummy_profile,
                session_id=dummy_session_id
            )
            # If it doesn't raise an error, the call worked.
            logger.success(f"exposed_get_messages called successfully (returned {len(messages)} messages).")
        except Exception as e:
            # Catching potential errors (like DB lookup failures) is expected here for dummy data
            logger.warning(f"Call to exposed_get_messages failed as expected for dummy data OR RPyC error: {e}")


    except ConnectionRefusedError:
        logger.error(f"Connection refused. Is the RPyC server running on {RPYC_HOST}:{RPYC_PORT}?")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if conn and not conn.closed:
            logger.info("Closing RPyC connection.")
            conn.close()

# --- Run the test ---
if __name__ == "__main__":
    test_connection()