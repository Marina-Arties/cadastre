from app.services.trigram import trigram_similarity


class TestTrigramSimilarity:
    def test_identical_strings(self):
        assert trigram_similarity("москва", "москва") == 1.0

    def test_completely_different(self):
        score = trigram_similarity("москва", "ленинград")
        assert score < 0.3

    def test_similar_strings(self):
        score = trigram_similarity("улица ленина", "улица ленино")
        assert score > 0.7

    def test_typo(self):
        score = trigram_similarity("улица тверская", "улица тверскаяя")
        assert score > 0.7

    def test_empty_string(self):
        assert trigram_similarity("", "текст") == 0.0

    def test_both_empty(self):
        assert trigram_similarity("", "") == 0.0

    def test_short_string(self):
        score = trigram_similarity("дом", "дом")
        assert score == 1.0

    def test_padded_properly(self):
        score = trigram_similarity("абв", "абвг")
        assert 0.0 < score < 1.0
