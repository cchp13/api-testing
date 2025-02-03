
from datetime import datetime, timedelta
import logging
import math
import time
from unittest.mock import patch

import pytest

from tests.utils.requests_functions import request_get_with_exception_handling, request_limit_reached

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


ESTACION_RADIOMETRICA_JCI_ARCHIVE_DATE = datetime(2007,3,7)
DATA_TIME_RESOLUTION = timedelta(minutes=10)
API_REQUEST_CAP_SLEEP = 5  # Seconds between attempts after api request cap is reached.


# Input parameters
VALID_STATION_IDENTIFICATORS = ["89064", "89064R", "89064RA", "89070"]
STARTING_DATES = [
    # Included a very old datapoint since the Antarctica bases were founded around 1988-1989.
    # There is an argument for randomizing these, but it depends on the specific use intended for the data.
    datetime(year=y, month=6, day=15) for y in [1990, 2000, 2010, 2020, 2023, 2024]
]
VALID_INTERVALS = [timedelta(minutes=15), timedelta(minutes=25), timedelta(hours=6) , timedelta(days=29)]


@pytest.fixture(autouse=True, scope="module")
def check_api_key_present(api_key_handler):
    if not api_key_handler.key:
        pytest.skip("No API key found. Please run `pytest test_api_key_retrieval.py` first.")

@pytest.fixture()
def request_get_retry(request_cap_wait):
    def _request_get_retry(url, headers = None, querystring = None):
        # In order to focus on data validity, we will try to avoid failing tests due to non-functional issues.
        n = 0
        N = 5
        response = request_get_with_exception_handling(url=url, headers=headers, params=querystring)
        while not response.ok and n<N:
            if request_limit_reached(response):
                m = 0
                M = request_cap_wait * 60 / API_REQUEST_CAP_SLEEP
                while request_limit_reached(response) and m<M:
                    # Loop to wait for api request limit to expire
                    response = request_get_with_exception_handling(url=url, headers=headers, params=querystring)
                    time.sleep(API_REQUEST_CAP_SLEEP)
                    m+=1

                if request_limit_reached(response):
                    # Note that we may fail the test during the first iteration of the outer loop if this is the cause.
                    return response

            time.sleep(1)
            response = request_get_with_exception_handling(url=url, headers=headers, params=querystring)
            n+=1
        return response

    return _request_get_retry


@pytest.fixture()
def make_request(
    base_api_url,
    api_key_handler,
    station,
    starting_date,
    interval,
    request_get_retry,
    antartida_api_endpoint,
    date_format,
):
    def _request_response(starting_date=starting_date, time_zone="UTC"):

        end_date = starting_date + interval

        # Prepare request components
        starting_date_string = starting_date.strftime(date_format(time_zone))
        end_date_string = end_date.strftime(date_format(time_zone))
        url = antartida_api_endpoint(base_api_url, starting_date_string, end_date_string, station)
        querystring = {"api_key": api_key_handler.key}
        headers = {'cache-control': "no-cache"}

        # Request to target endpoint
        response = request_get_retry(url, headers=headers, querystring=querystring)
            
        return response
    
    return _request_response


@pytest.mark.parametrize("station", VALID_STATION_IDENTIFICATORS)
@pytest.mark.parametrize("starting_date", STARTING_DATES)
@pytest.mark.parametrize("interval", VALID_INTERVALS)
def test_api_key_valid_request(
    make_request,
    interval,
    data_point_structure,
    allow_missing_datapoints,
    request_get_retry,
    station,
    starting_date
):

    logger.info(f"Making data request for {station=}, {starting_date=} and {interval=}.")
    request_response = make_request()
    logger.info(f"Response text: {request_response.text}.")

    if (not request_response.ok):
    # Even if no data is retrieved, we still expect a 200 code for the API request itself.
        pytest.fail(f"Request failed. Inspect the logs for more information.")

    if (
        station == "89064R" and starting_date < ESTACION_RADIOMETRICA_JCI_ARCHIVE_DATE
        or station == "89064RA" and starting_date > ESTACION_RADIOMETRICA_JCI_ARCHIVE_DATE
    ):
        # In this case, data is expected to be missing as per the documentation.
        logger.info("This station does not cover this time interval. Expecting a 404 status.")
        assert request_response.json() == {
            "estado": 404,
            "descripcion": "No hay datos que satisfagan esos criterios"
        }

    ## Data availability
    if request_response.json()["estado"] == 404:
        # Whether this is a passed or failed test would depend on the specific business logic behind the API
        # consumption and the particular scope of these tests. I have finally opted for consider this a passing
        # behavior, since being able to properly inform about the lack of data for this query is expected behavior.
        logger.info("A 404 status was returned. Ensuring description matches status code.")
        assert "No hay datos que satisfagan esos criterios" in request_response.json()["descripcion"]
        return

    ## Data retrieval
    logger.info(f"Retrieving data from {request_response.json()['datos']}.")
    data_response = request_get_retry(request_response.json()['datos'])
    # We will not log this response directly, as it may contain a large amount of data.

    if not data_response.ok:
        # We can log it for troubleshooting if there was an error, no data is expected.
        logger.error(f"Response text: {request_response.text}.")
        pytest.fail(f"Request failed. Inspect the logs for more information.")

    data = data_response.json()
    N = len(data)

    if N == 0:
        # This is an odd scenario, but I've experienced it. Adding logging as a precaution.
        logger.error(f"Data response content: {data_response.text}")
        pytest.fail("No data points were retrieved, but the status was not 404 either.")

    ## Data validity
    if not allow_missing_datapoints:
        logger.info("Checking data length.")
        # Check that number of data points is consistent with the time interval selected.
        n_points_estimated = interval // DATA_TIME_RESOLUTION
        if not(n_points_estimated <= N <= (n_points_estimated + 1)):
            pytest.fail(f"Expected {n_points_estimated} or {n_points_estimated + 1} datapoints, received {N}")

    # Verify consistency of data structure
    for i in range(0, math.ceil(N/100), N):
        logger.info("Verifying datapoint structure.")
        # Since the data series is a list of dictionaries, I do not see another way to ensure check the structure is
        # consistent other than checking each element. Beinh thorough may be an unnecessary consumption of testing
        # resources. To mitigate the issue, we will only verify roughly 100 equispaced datapoints for each query.
        logger.info(f"Data point fields retrieved: {', '.join(data[i].keys())}")
        assert set(data[i].keys()) == data_point_structure


@pytest.mark.parametrize(
    "station,starting_date,interval",
    [(VALID_STATION_IDENTIFICATORS[0], STARTING_DATES[-1], VALID_INTERVALS[1])]
)
def test_unauthorized_request(api_key_handler, make_request):
    """Test that a request made with an invalid key returns a 401 status code."""
    # Mock the key attribute stored at the key handler, leaving every other system untouched.
    with patch.object(api_key_handler, "_key", "fake.key"):
        response = make_request()
        assert response.json() == {'descripcion': 'API key invalido', 'estado': 401}
        

@pytest.mark.parametrize(
    "starting_date,interval",
    [(STARTING_DATES[-1], timedelta(hours=-15))]
)
@pytest.mark.parametrize("station", VALID_STATION_IDENTIFICATORS)
def test_negative_interval(make_request, station, starting_date, interval):
    """Test that a request made with starting_date later than end_date simply returns no data."""
    
    logger.info(f"Making data request for {station=}, {starting_date=} and {interval=}.")
    response = make_request()
    assert response.json() == {'descripcion': 'No hay datos que satisfagan esos criterios', 'estado': 404}


@pytest.mark.parametrize("station", VALID_STATION_IDENTIFICATORS)
@pytest.mark.parametrize("starting_date", 
    [datetime(year=2000, month=1, day=1) + i*timedelta(weeks=26) for i in range(12)]
)
@pytest.mark.parametrize("interval", [timedelta(hours=1)])
def test_time_zone_consistency(make_request, starting_date, request_get_retry, station, interval):
    """
    Test time zone consistency in the output. We observe that the data provided is always UTC+0000.

    We have learned that the database accessed with this endpoint is not thorough and there are missing timestamps.
    To remove that interference from this test, we will request the exact data points by adjusting the start/end dates
    so that the queries in CET and CEST are referring to the exact same universal times.

    About parametrization:
    - One interval is enough for this test. Jumps on time zone consistency happening in the short term would be odd.
    - Data on this endpoint is updated yearly. We will use two dates per year: one during summer, one during winter.
    - We want to validate this behavior for every database, so we will check the for stations.
    
    So one interval and two dates per year will suffice. To avoid making the exercise slower, we will test a few.
    """

    def _get_data_for_timezone(time_zone, starting_time):

        logger.info(f"Making data request for {station=}, {starting_time=} and {interval=} with CET time zone.")
        request_response = make_request(starting_date=starting_time, time_zone=time_zone)
        logger.info(f"Response text: {request_response.text}.")

        if (not request_response.ok):
        # Even if no data is retrieved, we still expect a 200 code for the API request itself.
            pytest.fail(f"Request failed. Inspect the logs for more information.")

        if request_response.json()["estado"] == 404:
            # This test serves no purpose in this case. Parametrization should probably be reviewed.
            pytest.skip("Parametrization not relevant.")

        # Data retrieval
        logger.info(f"Retrieving data from {request_response.json()['datos']}.")
        data_response = request_get_retry(request_response.json()["datos"])
        if not data_response.ok:
            pytest.fail(f"Data access failed: {data_response.text}")

        return data_response.json()

    utc_data = _get_data_for_timezone("UTC", starting_date-timedelta(hours=1))
    cet_data = _get_data_for_timezone("CET", starting_date)
    cest_data = _get_data_for_timezone("CEST", starting_date+timedelta(hours=1))

    # Verify times match
    utc_times = [datapoint["fhora"] for datapoint in utc_data]
    cet_times = [datapoint["fhora"] for datapoint in cet_data]
    cest_times = [datapoint["fhora"] for datapoint in cest_data]
    assert utc_times == cet_times == cest_times
