from unittest.mock import patch, MagicMock
from ltbox.utils import get_latest_release_version

@patch("urllib.request.urlopen")
def test_get_latest_release_version_success(mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = b'{"tag_name": "v1.2.3"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    version = get_latest_release_version("user", "repo")
    assert version == "v1.2.3"

@patch("urllib.request.urlopen")
def test_get_latest_release_version_failure(mock_urlopen):
    mock_urlopen.side_effect = Exception("Network Error")

    version = get_latest_release_version("user", "repo")
    assert version is None
