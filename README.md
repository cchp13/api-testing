_Italic comments clarify aspects related to the exercise. They may provide justifications or expand on TODOs that weren't implemented to save time, but would be included were this repository to be a real case rather than a coding challenge. This applies to every README file with italic comments._


#### Prerequisites
Make sure Python 3.12 is installed and added to your path. The setup script will take care of the rest.

#### Setup

To setup the environment for testing, simply run `python ./setup_env.py` (Or any analogous command that leads to python 3.12 running this script). The following flags are available:
- `-c`: Clear the virtual environments and cache folders for a clean installation.
- `-C`: Clear the secrets folder to delete locally stored credentials.

_As far as I know, the configurations I have used for the dependency manager (poetry) result in every cache and virtual environment being created within this same folder, avoiding appdata clutter._

#### Test Execution
Once the setup is finished, activate the virtual environment and run `pytest` to execute every test. For information on controlling the test execution conditions, see [Pytest how to](https://docs.pytest.org/en/stable/how-to/usage.html "Pytest CLI reference").

##### API Key generation
To execute the first part of the exercise and generate the API Key, run:

`pytest tests/test_API_Key_retrieval.py`

During the execution of this testing module, a Chrome window will be offered to fulfill the Captcha. Follow the instructions on the popup to pass the test successfully.

It is advised to run this testing module in isolation at least once so that a fallback key can be generated for future test executions.

_On a real case, the CI agent would have a key safely stored on its Secrets section so that there is always a valid key available on an Environment Variable. Additionally, developers could have the key added as environment variable locally to use the same systems as the CI agent would. However, I have simply stored credentials on a json file (gitignored), because it is fast and because you can just delete the whole folder after running the exercise and leave your system as it was._

##### API Key validation
_pending_