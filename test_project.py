import pytest
from project import extract_video_id

def test_extract_video_id_valid():
    assert extract_video_id("https://youtu.be/8qQW4LTWgtc?si=CYSuulbV1hK6BpeS") == "8qQW4LTWgtc"
    assert extract_video_id("https://www.youtube.com/watch?v=SoH6RKbhwy8") == "SoH6RKbhwy8"
    assert extract_video_id("https://www.youtube.com/watch?v=Pvctslm6e_A") == "Pvctslm6e_A"

def test_extract_video_id_invalid():
    with pytest.raises(ValueError):
        extract_video_id("")
    with pytest.raises(ValueError):
        extract_video_id("https://www.youtube.com/watch?q=Pvctslm6e_A")
    with pytest.raises(ValueError):
        extract_video_id("12345")
    with pytest.raises(ValueError):
        extract_video_id("https://youtu.be/")
    with pytest.raises(ValueError):
        extract_video_id("https://www.youtube.com/")