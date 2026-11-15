from app.services.extractor import platform_for, ExtractedStream
def test_platform_detection():
    assert platform_for("https://kick.com/example")=="Kick"
    assert platform_for("https://www.twitch.tv/example")=="Twitch"
    assert platform_for("https://www.youtube.com/watch?v=x")=="YouTube"
    assert platform_for("https://cdn.example.org/live.m3u8")=="HLS"
def test_only_actual_quality_is_listed():
    stream=ExtractedStream("HLS","t","c",None,True,[{"url":"x","height":720},{"url":"y","format_note":"audio only"}])
    assert stream.qualities==["720p","audio only"]
