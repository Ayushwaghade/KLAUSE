import pytest
from unittest.mock import MagicMock, patch
from app.core.dispatcher import Dispatcher
from app.models.agent import ToolObservation
from app.tools.system_tools import download_image
from app.core.context import context

@patch("urllib.request.urlopen")
def test_download_image_bing_success(mock_urlopen):
    # Mock Bing search page response (success)
    mock_search_resp = MagicMock()
    mock_search_resp.read.return_value = (
        b"<html><body>"
        b"&quot;murl&quot;:&quot;https://wallpaperaccess.com/full/9448123.jpg&quot;"
        b"</body></html>"
    )
    
    # Mock download response
    mock_dl_resp = MagicMock()
    mock_dl_resp.read.return_value = b"bing-image-binary-data"
    
    mock_urlopen.return_value.__enter__.side_effect = [mock_search_resp, mock_dl_resp]
    
    res = download_image("spiderman", "spiderman.jpg")
    assert "Success" in res
    assert "Bing" in res
    assert "spiderman.jpg" in res

@patch("urllib.request.urlopen")
def test_download_image_pexels_success(mock_urlopen):
    # Mock Bing search page response (failure / empty)
    mock_bing_resp = MagicMock()
    mock_bing_resp.read.return_value = b"<html><body>No matches</body></html>"
    
    # Mock Pexels search page response (success)
    mock_search_resp = MagicMock()
    mock_search_resp.read.return_value = (
        b"<html><body>"
        b"<img src='https://images.pexels.com/photos/12345/pexels-photo-12345.jpeg'>"
        b"</body></html>"
    )
    
    # Mock download response
    mock_dl_resp = MagicMock()
    mock_dl_resp.read.return_value = b"pexels-image-binary-data"
    
    mock_urlopen.return_value.__enter__.side_effect = [mock_bing_resp, mock_search_resp, mock_dl_resp]
    
    res = download_image("cute cat", "cat.jpg")
    assert "Success" in res
    assert "Pexels" in res
    assert "cat.jpg" in res

@patch("urllib.request.urlopen")
def test_download_image_stocksnap_fallback(mock_urlopen):
    # Mock Bing search page response (failure / empty)
    mock_bing_resp = MagicMock()
    mock_bing_resp.read.return_value = b""
    
    # Mock Pexels search page response (failure / empty)
    mock_pexels_resp = MagicMock()
    mock_pexels_resp.read.return_value = b"<html><body>No matches</body></html>"
    
    # Mock StockSnap search page response (success)
    mock_stocksnap_resp = MagicMock()
    mock_stocksnap_resp.read.return_value = (
        b"<html><body>"
        b"<img src='https://cdn.stocksnap.io/img-thumbs/280h/outdoors-dog_Z1DLGX7470.jpg'>"
        b"</body></html>"
    )
    
    # Mock download response
    mock_dl_resp = MagicMock()
    mock_dl_resp.read.return_value = b"stocksnap-image-binary-data"
    
    mock_urlopen.return_value.__enter__.side_effect = [mock_bing_resp, mock_pexels_resp, mock_stocksnap_resp, mock_dl_resp]
    
    res = download_image("cute dog", "dog.jpg")
    assert "Success" in res
    assert "StockSnap" in res
    assert "dog.jpg" in res

@patch("urllib.request.urlopen")
def test_download_image_not_found(mock_urlopen):
    # Mock Bing empty
    mock_bing_resp = MagicMock()
    mock_bing_resp.read.return_value = b""
    
    # Mock Pexels empty
    mock_pexels_resp = MagicMock()
    mock_pexels_resp.read.return_value = b""
    
    # Mock StockSnap empty
    mock_stocksnap_resp = MagicMock()
    mock_stocksnap_resp.read.return_value = b""
    
    mock_urlopen.return_value.__enter__.side_effect = [mock_bing_resp, mock_pexels_resp, mock_stocksnap_resp]
    
    res = download_image("nonexistent_image_query_xyz", "none.jpg")
    assert "Error" in res

def test_dispatcher_boundary_checks_download_image(tmp_path):
    dispatcher = Dispatcher(confirm_fn=lambda prompt: False) # Always reject write exceptions
    
    # Configure session folder
    context.session_data_folder = str(tmp_path)
    
    # Case 1: Write inside session data folder -> should proceed (we will mock execution to return success)
    with patch("app.core.dispatcher.tool_registry") as mock_registry:
        mock_tool = MagicMock()
        mock_tool.destructive = False
        mock_tool.func = lambda query, dest_path: "Success"
        mock_registry.__contains__.return_value = True
        mock_registry.__getitem__.return_value = mock_tool
        
        inside_path = str(tmp_path / "inside.jpg")
        obs = dispatcher.execute("download_image", {"query": "cat", "dest_path": inside_path})
        assert obs.success is True
        assert obs.error is None
        
        # Case 2: Write outside session data folder -> should fail due to rule violation
        outside_path = "C:/Windows/System32/outside.jpg"
        obs_outside = dispatcher.execute("download_image", {"query": "cat", "dest_path": outside_path})
        assert obs_outside.success is False
        assert "RULE_VIOLATION" in obs_outside.error
        
    context.session_data_folder = None
