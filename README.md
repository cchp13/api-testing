_Italic comments clarify aspects related to the exercise. They may provide justifications or expand on TODOs that weren't implemented to save time but would be included if this repository were a real-world case rather than a coding challenge. This applies to every README file containing italic comments._


#### Prerequisites
- Ensure Python 3.12 is installed and added to your PATH.
- Windows is recommended, although the code is portable. Linux should work with sufficient Python/Selenium build and configuration expertise.
- An email account to retrieve emails containing the API key. Gmail is advised, as it is the only one I have used for this exercise. Note that you will need an app password to programmatically access the IMAP service. See [Google Support](https://knowledge.workspace.google.com/kb/how-to-create-app-passwords-000009237) for more information.


#### Quickstart

On a windows system with Python 3.12 available, run the following commands:

```
python setup_env.py  # Provide required inputs
pytest tests/end_to_end/test_api_key_retrieval.py
pytest tests/end_to_end/ --allow-missing-datapoints --html=reports/t1/r.html
```

This will:
- Ask for email credentials for API Key email retrieval.
- Run the API Key retrieval tests. Store the key in the secrets folder.
- Use the key to run the data retrieval and validation tests.
- Generate an html report in the reports folder.

#### Setup

To prepare the environment for testing, run `python ./setup_env.py` (Or any analogous command that leads to python 3.12 running this script). The following flags are available to reset certain environment elements:
- `-c`: Clear the virtual environments and cache folders for a clean installation.
- `-C`: Clear the secrets folder to delete locally stored credentials.

_As far as I know, the configurations I’ve used for the dependency manager (Poetry) result in every cache and virtual environment being created within this same folder, avoiding AppData clutter._


#### Test Execution
Once the setup is finished, activate the virtual environment and run

`pytest tests/end_to_end`

to execute every test. For information on controlling the test execution conditions, see [Pytest how to](https://docs.pytest.org/en/stable/how-to/usage.html "Pytest CLI reference"). This test suit enables the following options:

- `--wait-for-capacity`: Maximum number of minutes to wait when the API request limit per key is exceeded. Defaults to 5.
- `--html`: Target path for the `.html` report. It is advised to use a subdirectory of `reports`, which is already gitignored. Defaults to None (No file report).
- `--allow-missing-datapoints`: Whether to pass a test in which the data series retrieved is not exhaustive (not every interval of 10 minutes is covered). Defaults to False.

_A combination of custom options (such as these) and test markers would be used to group tests depending on their scope. This is crucial to enable a CI strategy with proper granularity._

##### API Key generation
To execute the first part of the exercise and generate the API Key, run:

`pytest tests/end_to_end/test_api_key_retrieval.py`

During the execution of this testing module, a Chrome window will be offered to fulfill the Captcha. Follow the instructions on the popup to pass the test successfully.

It is advised to run this testing module in isolation until they pass once, so that a key can be generated for future test executions.

_On a real case, the CI agent would have a key safely stored so that there is always a valid key available as Environment Variable. Additionally, developers could have the key added as environment variable locally to replicate CI conditions. However, I have simply stored credentials on a json file (gitignored), because it is fast and because you can just delete the whole folder after running the exercise and leave your system as it was._

##### API Key validation
To execute the API Key validation tests, run:

`pytest tests/end_to_end/test_api_key_validation.py [--allow-missing-datapoints] [--html=reports/t1/r.html]`

These tests do not require any user input.

#### Comments on the bonus points.

1. "Implement data validation to ensure that the temperature, pressure, and speed values meet realistic thresholds." I have not implemented this because the naive approach (defining a numeric threshold and iterating over the values to check if it is exceeded) seemed technically trivial. On the other hand, anything beyond this approach would be inextricably linked to the specific data processing that follows retrieval. In a real scenario, I would discuss with the team the specific needs behind the data validation request (because, as a matter of fact, that straightforward loop-and-compare approach might just be sufficient), as well as the downstream data processes, to assess if there is a better moment in the data lifecycle to perform that validation.

2. "Evidence how you might handle the situation where the data in a public test environment is constantly changing".
- If frequent and/or sudden changes in external inputs/behaviors are impairing our ability to develop our own application, mocking the external services may be key. For our exercise, we can retrieve a broad enough set of data requests from the AEMET API, store it, and launch a mocking service that will serve that data to our tests. That offline data may be updated as frequently as it suits us, in a controlled manner. This doesn't nullify the need to adapt to changes, but it makes the transition as smooth as possible.
- I would emphasize modularity and separation of concerns when designing testing utilities. Over-coupling impairs our ability to adapt to external changes. Maintainability and clarity are always central, but they matter even more when we know we are likely to modify the systems in the near future.
- Make the tests focus on behavior, and abstract the specific implementation away from them.
- Define a comprehensive set of single-purpose fixtures that contain the externals that may be subject to change. Make proper use of dependency injection to convey that information down into our internals and into the tests. This is what I tried to illustrate in the "AEMET" section in the `tests/conftest.py` file, where variables such as datapoint fields or frontend text elements, which may change at any moment, are defined.

#### Improvements that I have not implemented on this exercise, but are relevant next steps.

- Non-functional testing. This focuses on response data validation. These tests attempt by any means to get a valid response from the API, retrying queries a few times and waiting for the API request limit to reset. This approach addresses some non-functional requirements, such as performance (e.g., how slow are the requests?) and reliability (e.g., how often do valid requests fail?).
- Pre-commit automatic style checks, to ensure consistent coding style.
- Type hints: Although Python is a dynamic, loosely typed programming language, type hints can be used "as if" it were strongly typed. This enhances maintainability, robustness, and makes the code easier to read. If I were to continue working on this project, I would start by implementing a type checker. The `ApiKeyHandler` class has been thoroughly type-hinted as an example. These efforts would be supported by linters integrated into the pre-commit checks.
- Docstrings: While I have added some docstrings where context would be helpful, I have not been exhaustive. Tests, in particular, should include docstrings with significant information, such as the test author, associated test case work item ID or hyperlink (e.g., GitHub or Azure DevOps issue), etc.
- CI/CD Strategy. As the test suite grows, tests should be properly categorized using [markers](https://docs.pytest.org/en/stable/example/markers.html) and a well-organized test directory structure. The CI/CD strategy can vary significantly depending on the volume of daily or weekly pull requests (PRs). However, it is expected that some tests will run with each PR, some with nightly or weekly certification, and some as regression testing before each release. Additionally, depending on the product, certain subsystems or integration tests would only run in specific environments or scenarios. Custom `pytest` CLI options, such as `--enable-subsystem-xyz`, are very convenient for handling these circumstances.