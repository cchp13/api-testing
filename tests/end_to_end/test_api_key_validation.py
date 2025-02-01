
from datetime import datetime, timedelta
import math
import time
from unittest.mock import patch
from urllib.parse import quote

import requests
import pytest


ESTACION_RADIOMETRICA_JCI_ARCHIVE_DATE = datetime(2007,3,7)
DATA_TIME_RESOLUTION = timedelta(minutes=10)
API_REQUEST_CAP_SLEEP = 5  # Seconds between attempts after api request cap is reached.


# Input parameters
# Dates and deltas could be randomized, but I would need more information about what to expect from the database.
# I included a very old datapoint since the antartic bases were founded around 1988-1989.
VALID_STATION_IDENTIFICATORS = ["89064", "89064R", "89064RA", "89070"]
STARTING_DATES = [datetime(1990, 1, 25), datetime(2005, 12, 5), datetime(2010, 12, 5), datetime(2019, 12, 5), datetime(2023, 12, 5)]
VALID_TIME_DELTAS = [timedelta(minutes=15), timedelta(minutes=25), timedelta(hours=6) , timedelta(days=29)]


def request_get_retry(url, attempts = 5, headers = None, querystring = None):
    # In order to focus on data validity, we will try to avoid failing tests due to non-functional issues.
    n = 0
    response = requests.get(url=url, headers=headers, params=querystring)
    while not response.ok and n<attempts:
        time.sleep(1)
        response = requests.get(url=url, headers=headers, params=querystring)
        n+=1
    return response


@pytest.fixture()
def make_request(base_api_url, api_key_handler, station, starting_date, time_delta, request_cap_wait):
    def _request_response(starting_date=starting_date, time_zone="CET"):
        if (
            station == "89064R" and starting_date < ESTACION_RADIOMETRICA_JCI_ARCHIVE_DATE
            or station == "89064RA" and starting_date > ESTACION_RADIOMETRICA_JCI_ARCHIVE_DATE
        ):
            pytest.skip("Parameter combination not applicable.")

        end_date = starting_date + time_delta

        # Prepare request components
        starting_date_string = starting_date.strftime(f"%Y-%m-%dT%H:%M:%S{time_zone}")
        end_date_string = end_date.strftime(f"%Y-%m-%dT%H:%M:%S{time_zone}")
        url = f"{base_api_url}/antartida/datos/fechaini/{starting_date_string}/fechafin/{end_date_string}/estacion/{station}"
        querystring = {"api_key": api_key_handler.key}
        headers = {'cache-control': "no-cache"}

        # Request to target endpoint
        response = request_get_retry(url, headers=headers, querystring=querystring)

        if response.json()["estado"] == 429:
            m = 0
            M = request_cap_wait * 60 / API_REQUEST_CAP_SLEEP
            while response.json()["estado"] == 429 and m<M:
                # Loop to wait for api request limit to expire
                response = request_get_retry(url=url, headers=headers, querystring=querystring)
                time.sleep(API_REQUEST_CAP_SLEEP)
                m+=1

            if response.json()["estado"] == 429:
                # Note that we may fail during the first iteration of the outer loop if we fail for this reason.
                pytest.fail("Failed due to API request cap. Increase value of --wait-for-cap option to avoid issue.")
            
        return response
    
    return _request_response


@pytest.mark.parametrize("station", VALID_STATION_IDENTIFICATORS)
@pytest.mark.parametrize("starting_date", STARTING_DATES)
@pytest.mark.parametrize("time_delta", VALID_TIME_DELTAS)
def test_api_key_valid_request(make_request, time_delta, data_point_structure):

    request_response = make_request()
    if (not request_response.ok):
    # Even if no data is retrieved, we still expect a 200 code for the API request itself.
        pytest.fail(f"Request failed: {request_response.json()}")

    ## Data availability
    if request_response.json()["estado"] == 404:
        # Whether this is a passed or failed test would depend on the specific business logic behind the API
        # consumption and the particular scope of these tests. I have finally opted for consider this a passing
        # behavior, since being able to properly inform about the lack of data for this query is expected behavior.
        assert "No hay datos que satisfagan esos criterios" in request_response.json()["descripcion"]
        return

    ## Data retrieval
    time.sleep(0.5)
    data_response = request_get_retry(request_response.json()["datos"])
    if not data_response.ok:
        pytest.fail(f"Data access failed: {data_response.json()}")

    data = data_response.json()
    N = len(data)

    ## Data validity
    # Number of data points should be consistent with time interval selected.
    n_points_estimated = time_delta // DATA_TIME_RESOLUTION
    if not(n_points_estimated <= N <= (n_points_estimated + 1)):
        pytest.fail(f"Expected {n_points_estimated} or {n_points_estimated + 1} datapoints, received {N}")

    # Verify consistency of data structure
    for i in range(0, math.ceil(N/100), N):
        # Since the data series is a list of dictionaries, there is no way to ensure consistent structure other than
        # checking each element. Beigh thorough may be an unnecessary consumption of testing resources. To avoid the
        # issue, we will only verify roughly 100 equispaced datapoints.
        assert set(data[i].keys()) == data_point_structure


@pytest.mark.parametrize(
    "station,starting_date,time_delta",
    [(VALID_STATION_IDENTIFICATORS[0], STARTING_DATES[-1], VALID_TIME_DELTAS[1])]
)
def test_unauthorized_request(api_key_handler, make_request):
    """Test that a request made with an invalid key returns a 4XX status code."""
    
    # Simply mock the key attribute at the key handler, leaving every other system untouched.
    with patch.object(api_key_handler, "_key", "fake.key"):
        response = make_request()
        assert response.json() == {'descripcion': 'API key invalido', 'estado': 401}
        

@pytest.mark.parametrize(
    "station,starting_date,time_delta",
    [(VALID_STATION_IDENTIFICATORS[0], STARTING_DATES[-1], timedelta(hours=-15))]
)
def test_negative_deltas(make_request):
    """Test that a request made with starting_date later than end_date simply returns no data."""
    
    response = make_request()
    assert response.json() == {'descripcion': 'No hay datos que satisfagan esos criterios', 'estado': 404}

@pytest.mark.parametrize("station", VALID_STATION_IDENTIFICATORS[:1])
@pytest.mark.parametrize("starting_date", STARTING_DATES[-2:])

@pytest.mark.parametrize("time_delta", [timedelta(hours=1)])
def test_time_zone_consistency(make_request, starting_date):
    """
    Test time zone consistency in the output. We observe that the data provided is always UCT+0000.

    We have learnt that the database accessed with this endpoint is not thorough and there are missing timestamps.
    To remove that interference from this test, we will request the exact data points by adjusting the start/end dates
    so that the queries in CET and CEST are referring to the exact same universal times.

    About parametrization:
    - One time delta is enough for this test. Jumps on time zone consistency happening in the short term would be odd.
    - Data on this endpoint is updated yearly. We will use two dates per year: one during summer, one during winter.
    """

    request_response_cet = make_request(starting_date=starting_date, time_zone="CET")
    if (not request_response_cet.ok):
    # In this case, we cannot cover this functionality if there is no data.
        pytest.skip(f"No data to be validated for the current query.")

    # CET data retrieval
    time.sleep(0.5)
    data_CET = request_get_retry(request_response_cet.json()["datos"]).json()

    request_response_cest = make_request(starting_date=starting_date+timedelta(hours=1), time_zone="CEST")
    if (not request_response_cest.ok):
    # In this case, we cannot cover this functionality if there is no data.
        pytest.fail(f"Should be exact same data.")

    #  CEST retrieval
    time.sleep(0.5)
    data_CEST = request_get_retry(request_response_cest.json()["datos"]).json()

    assert data_CET[0]["fhora"] == data_CEST[0]["fhora"]

@pytest.mark.skip
def test_JCI_db_switch():
    raise NotImplementedError
