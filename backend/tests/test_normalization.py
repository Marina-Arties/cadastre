from app.services.normalization import normalize_address


class TestNormalization:
    def test_lowercase(self):
        assert normalize_address("Москва, Тверская") == "москва тверская"

    def test_abbreviation_ul(self):
        result = normalize_address("ул. Ленина")
        assert "улица ленина" == result

    def test_abbreviation_ul_no_dot(self):
        result = normalize_address("ул Ленина")
        assert "улица ленина" == result

    def test_abbreviation_dom(self):
        result = normalize_address("д. 15")
        assert "дом 15" == result

    def test_abbreviation_dom_no_dot(self):
        result = normalize_address("д 15")
        assert "дом 15" == result

    def test_abbreviation_prospekt(self):
        result = normalize_address("пр-т Мира")
        assert "проспект мира" == result

    def test_abbreviation_per(self):
        result = normalize_address("пер. Тихий")
        assert "переулок" in result
        assert "тихий" in result

    def test_abbreviation_bulvar(self):
        result = normalize_address("б-р Гагарина")
        assert "бульвар гагарина" == result

    def test_abbreviation_pl(self):
        result = normalize_address("пл. Пушкина")
        assert "площадь пушкина" == result

    def test_abbreviation_kv(self):
        result = normalize_address("кв. 42")
        assert "квартира 42" == result

    def test_abbreviation_kv_no_dot(self):
        result = normalize_address("кв 42")
        assert "квартира 42" == result

    def test_abbreviation_g(self):
        result = normalize_address("г. Москва")
        assert "город москва" == result

    def test_abbreviation_obl(self):
        result = normalize_address("Московская обл.")
        assert "московская область" == result

    def test_extra_spaces(self):
        result = normalize_address("  г.   Москва  ,   ул.   Тверская  ")
        assert "город москва улица тверская" == result

    def test_punctuation_removal(self):
        result = normalize_address("г. Москва, ул. Тверская, д. 1")
        assert "город москва улица тверская дом 1" == result

    def test_empty_string(self):
        assert normalize_address("") == ""

    def test_only_spaces(self):
        assert normalize_address("   ") == ""
