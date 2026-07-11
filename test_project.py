import pytest
from project import extract_video_id, save_comments, search_comments, top_comments, word_frequency

FAKE_COMMENTS = [
    {"comment": "great tutorial. wonderful", "likes": 5, "author": "Alice"},
    {"comment": "this helped me a lot. this is wonderful", "likes": 10, "author": "Bob"},
    {"comment": "great explanation, very clear", "likes": 2, "author": "Charlie"},
    {"comment": "not helpful at all", "likes": 0, "author": "Dana"},
    {"comment": "awesome man", "likes": 5, "author": "Daniel"},
    {"comment": "superb", "likes": 5, "author": "Samuel"}
]
FAKE_VIDEO_ID = "SaH6RKbhwy8"

FAKE_WORD_COMMENTS = [
    {"comment": "Great tutorial! Great content.", "likes": 5, "author": "Alice"},
    {"comment": "This tutorial is really great, don't you think?", "likes": 3, "author": "Bob"},
    {"comment": "Amazing amazing tutorial, thanks!", "likes": 1, "author": "Charlie"},
]
FAKE_WORD_VIDEO_ID = "wF3xJ9k2Lmp"

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

def test_search_comments_valid(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments(FAKE_COMMENTS, FAKE_VIDEO_ID, db_path=db_path)
    result1 = search_comments("great", FAKE_VIDEO_ID, db_path=db_path)
    assert result1 == [
        ("great tutorial. wonderful", 5, "Alice"),
        ("great explanation, very clear", 2, "Charlie")
    ]
    result2 = search_comments("wonderful", FAKE_VIDEO_ID, db_path=db_path)
    assert result2 == [
        ("great tutorial. wonderful", 5, "Alice"),
        ("this helped me a lot. this is wonderful", 10, "Bob")
    ]
    result3 = search_comments("HELPFUL", FAKE_VIDEO_ID, db_path=db_path)
    assert result3 == [("not helpful at all", 0, "Dana")]

def test_search_comments_invalid(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments(FAKE_COMMENTS, FAKE_VIDEO_ID, db_path=db_path)
    result1 = search_comments("goat", FAKE_VIDEO_ID, db_path=db_path)
    assert result1 == []

def test_search_comments_video_isolation(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments(FAKE_COMMENTS, FAKE_VIDEO_ID, db_path=db_path)
    save_comments(
        [{"comment": "great video too", "likes": 3, "author": "Eve"}],
        "some_other_video_id",
        db_path=db_path
    )
    result = search_comments("great", FAKE_VIDEO_ID, db_path=db_path)
    assert result == [
        ("great tutorial. wonderful", 5, "Alice"),
        ("great explanation, very clear", 2, "Charlie")
    ]

def test_top_comments_valid(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments(FAKE_COMMENTS, FAKE_VIDEO_ID, db_path=db_path)
    result1 = top_comments(1, FAKE_VIDEO_ID, db_path=db_path)
    assert result1 == [("this helped me a lot. this is wonderful", 10, "Bob")]
    result2 = top_comments(3, FAKE_VIDEO_ID, db_path=db_path)
    assert result2 == [("this helped me a lot. this is wonderful", 10, "Bob"), ("great tutorial. wonderful",  5,
        "Alice"), ("awesome man",  5, "Daniel")
    ]
    result3 = top_comments(100, FAKE_VIDEO_ID, db_path=db_path)
    assert result3 == [("this helped me a lot. this is wonderful", 10, "Bob"), ("great tutorial. wonderful",  5,
        "Alice"), ("awesome man",  5, "Daniel"), ("superb", 5, "Samuel"), ("great explanation, very clear", 2,
        "Charlie"), ("not helpful at all", 0, "Dana")
    ]

def test_top_comments_invalid(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments(FAKE_COMMENTS, FAKE_VIDEO_ID, db_path=db_path)
    with pytest.raises(ValueError):
        top_comments(-5, FAKE_VIDEO_ID, db_path=db_path)
    with pytest.raises(ValueError):
        top_comments(0, FAKE_VIDEO_ID, db_path=db_path)

def test_top_comments_video_isolation(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments(FAKE_COMMENTS, FAKE_VIDEO_ID, db_path=db_path)
    save_comments(
        [{"comment": "great video too", "likes": 20, "author": "Eve"}],
        "some_other_video_id",
        db_path=db_path
    )
    result = top_comments(1, FAKE_VIDEO_ID, db_path=db_path)
    assert result == [("this helped me a lot. this is wonderful", 10, "Bob")]

def test_word_frequency_valid(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments(FAKE_WORD_COMMENTS, FAKE_WORD_VIDEO_ID, db_path=db_path)
    result1 = word_frequency(4, FAKE_WORD_VIDEO_ID, db_path=db_path)
    assert result1 == {"great": 3, "tutorial": 3, "think": 1, "amazing": 2}
    result2 = word_frequency(2, FAKE_WORD_VIDEO_ID, db_path=db_path)
    assert result2 == {"great": 3, "tutorial": 3}

def test_word_frequency_invalid(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments(FAKE_WORD_COMMENTS, FAKE_WORD_VIDEO_ID, db_path=db_path)
    with pytest.raises(ValueError):
        word_frequency(-5, FAKE_WORD_VIDEO_ID, db_path=db_path)
    with pytest.raises(ValueError):
        word_frequency(0, FAKE_WORD_VIDEO_ID, db_path=db_path)

def test_word_frequency_all_words_filtered(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments([{"comment": "the and 123 👍", "likes": 1, "author": "X"}],
                  FAKE_WORD_VIDEO_ID,
                  db_path=db_path)
    with pytest.raises(ValueError):
        word_frequency(1, FAKE_WORD_VIDEO_ID, db_path=db_path)

def test_word_frequency_no_comments(tmp_path):
    db_path = tmp_path / "test.db"
    save_comments([], FAKE_WORD_VIDEO_ID, db_path=db_path)
    with pytest.raises(ValueError):
        word_frequency(1, FAKE_WORD_VIDEO_ID, db_path=db_path)