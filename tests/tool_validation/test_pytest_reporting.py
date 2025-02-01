
import pytest

def test_failure():
    """Expected to fail."""
    pytest.fail("tool validation failure")


@pytest.fixture()
def setup_error():
    raise Exception("Setup error.")
    yield


def test_setup_error(setup_error):
    """Expected to fail due to setup error."""
    pass


@pytest.fixture()
def teardown_error():
    yield
    raise Exception("Setup error.")


def test_teardown_error(teardown_error):
    """Expected to pass, followed by to teardown error."""
    pass
