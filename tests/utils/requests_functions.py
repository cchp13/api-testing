
import logging

import requests
import pytest


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def request_get_with_exception_handling(url, **kwargs):
    """
    Retry the GET requests a few times before failing. Log every exception raised in the process. Note that the status
    code is not checked at this point, only that not exception is raised when attempting to make the connection.
    """
    n = 0
    N = 5
    while n<N:
        try:
            return requests.get(url, **kwargs)
        except Exception as e:                
            n+=1
            logger.error(f"Request to {url=} failed with exception: {str(e)}")
            
    pytest.fail(f"Failed to complete the request. Inspect logged ERRORs for more information.")

def request_limit_reached(response):
    """
    There are two different types of requests being made for the tests: requests to the API endpoint to query for
    specific data, and requests to retrieve the json after successful data requests. Their structure differs.
    """
    try:
        return response.json()["estado"] == 429
    except:
        return "429 Too Many Requests" in response.text
    