_Italic comments clarify aspects related to the exercise. They may provide justifications or expand on TODOs that weren't implemented to save time but would be included if this repository were a real-world case rather than a coding challenge. This applies to every README file containing italic comments._


#### Prerequisites
- Ensure Python 3.12 is installed and added to your PATH.
- Windows is recommended, although the code is portable. Linux should work with sufficient Python/Selenium build and configuration expertise.
- A Gmail account with an app password to programmatically access the IMAP service. See [Google Support](https://knowledge.workspace.google.com/kb/how-to-create-app-passwords-000009237) for more information.

The setup script will handle the rest.

#### Setup

To prepare the environment for testing, simply run `python ./setup_env.py` (Or any analogous command that leads to python 3.12 running this script). The following flags are available:
- `-c`: Clear the virtual environments and cache folders for a clean installation.
- `-C`: Clear the secrets folder to delete locally stored credentials.

_As far as I know, the configurations I’ve used for the dependency manager (Poetry) result in every cache and virtual environment being created within this same folder, avoiding AppData clutter._

_There are some elements I did not include on this setup process to save time, such as code style checks and linters._

#### Test Execution
Once the setup is finished, activate the virtual environment and run `pytest` to execute every test. For information on controlling the test execution conditions, see [Pytest how to](https://docs.pytest.org/en/stable/how-to/usage.html "Pytest CLI reference"). This test suit enables the following options:

- `--wait-for-capacity`: Maximum number of minutes to wait when the API request limit per key is exceeded. Defaults to 5.
- `--update-api-key`: Whether to update the API key stored on SECRETS. Defaults to False.
- `--html`: Path for the `.html` report. It is advised to use a subdirectory of `reports`, which is already gitignored. Defaults to None (No report).
- `--allow-missing-datapoints`: Whether to pass a test in which the data series retrieved is not exhaustive. Defaults to False.

_A combination of custom options (such as these) and test markers would be used to group tests depending on their scope. This is crucial to enable a CI strategy with proper granularity._

##### API Key generation
To execute the first part of the exercise and generate the API Key, run:

`pytest tests/end_to_end/test_API_Key_retrieval.py`

During the execution of this testing module, a Chrome window will be offered to fulfill the Captcha. Follow the instructions on the popup to pass the test successfully.

It is advised to run this testing module in isolation using the `--update-api-key` option until they pass once, so that a key can be generated for future test executions.

_On a real case, the CI agent would have a key safely stored so that there is always a valid key available as Environment Variable. Additionally, developers could have the key added as environment variable locally to use the same systems as the CI agent would. However, I have simply stored credentials on a json file (gitignored), because it is fast and because you can just delete the whole folder after running the exercise and leave your system as it was._

##### API Key validation
_pending_


##### _Aspects not implemented on this exercise_
_Some more elements that I left pending:_
- _Pre-commit automatic style checks and linters, as mentioned before._
- _Type hints: While Python is a dynamic, loosely typed programming language, type hints can still be used "as if" it were strongly typed programming language. This enhances maintainability, robusticy, and makes the code much easier to read. I would definitely start by implementing a type checker if I were to continue working on this project. The ApiKeyHandler class has been thoroughly type-hinted as an example._
- _Docstrings: While I have added some when context would help, I have not been exhaustive. Especially tests should include a docstring with significant information such as test author, associated test case work item ID/hyperlink (GitHub or Azure DevOps issue), etc._
- _CI/CD Strategy. As the test suite grows, the tests should be properly categorized using [markers](https://docs.pytest.org/en/stable/example/markers.html) and a smart test directory structure. The CI/CD strategy can vary a lot depending on the volume of daily/weekly PRs, but it is expected that some tests will run with each PR, some with nightly/weekly certification, and some as regression testing once before each release. Additionally, depending on the product, some subsystems/integration tests would only run on certain environments/scenarios; custom pytest cli options such as --enable-subsystem-xyz are very convenient to handle those circumstantes._