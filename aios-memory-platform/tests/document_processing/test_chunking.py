from memory_platform.document_processing.chunking import chunk_text


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_short_text_single_chunk():
    chunks = chunk_text("This is a short paragraph.", max_tokens=400)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert "short paragraph" in chunks[0].content


def test_long_text_splits_into_multiple_chunks_within_budget():
    paragraphs = [f"Paragraph number {i} contains some unique filler content to pad it out further." for i in range(60)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, max_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1
    for c in chunks:
        assert c.token_count <= 130  # allow small slack for a single oversized unit
    # indices are sequential
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_overlap_carries_content_between_chunks():
    paragraphs = [f"Paragraph {i}: distinct sentence content here for chunk boundary testing purposes." for i in range(30)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, max_tokens=80, overlap_tokens=30)
    assert len(chunks) > 1
    # some overlap: the tail of chunk N should share at least one paragraph with the head of chunk N+1
    for i in range(len(chunks) - 1):
        tail_words = set(chunks[i].content.split()[-15:])
        head_words = set(chunks[i + 1].content.split()[:15])
        assert tail_words & head_words
