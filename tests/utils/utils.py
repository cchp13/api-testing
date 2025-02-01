import json
from pathlib import Path

class ApiKeyHandler:
    def __init__(self, key_file: Path, api_key_key: str):
        """
        Initialize the ApiKeyHandler.

        Args:
            key_file (Path): Path to the JSON file containing the API key.
            api_key_key (str): Key in the JSON file that holds the API key.
        """
        self._key_file: Path = key_file
        self._api_key_key: str = api_key_key
        self._key: str = self._load_key()

    @property
    def key(self) -> str:
        """
        Get the current API key.

        Returns:
            Optional[str]: The API key.
        """
        return self._key

    def read_key(self) -> str:
        """
        Read the API key from the file.

        Returns:
            Optional[str]: The API key, or None if not found.
        """
        return self._load_key()

    def update_key(self, key: str) -> None:
        """
        Update the API key in the file.

        Args:
            key (str): The new API key to store.
        """
        self._save_key(key)
        self._key: str = key

    def _load_key(self) -> str:
        """
        Load the API key from the file.

        Returns:
            str: The API key.
        """
        with open(self._key_file, "r") as file:
            data = json.load(file)
            return data.get(self._api_key_key)

    def _save_key(self, key: str) -> None:
        """
        Save the API key to the file.

        Args:
            key (str): The API key to save.
        """
        data = {}
        if self._key_file.exists():
            try:
                with open(self._key_file, "r") as file:
                    data = json.load(file)
            except json.JSONDecodeError:
                pass  # If the file is corrupted, overwrite it

        data[self._api_key_key] = key
        with open(self._key_file, "w") as file:
            json.dump(data, file, indent=4)