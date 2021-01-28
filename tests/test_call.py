from krummstiel import krummstiel


class TestKrummstiel:
    def test_wrong_ini1(self):
        assert krummstiel.main(config="tests/test_error1.ini", verbose=2) == 2

    def test_wrong_ini2(self):
        assert krummstiel.main(config="tests/test_error2.ini", verbose=2) == 2

    # def test_no_args(self):
    #    args = []
    #    assert krummstiel.main(args) == 0

    # def test_missing_args(self):
    #    pass
    # args = ["--config"]
    # assert krummstiel.main(args) == 2
