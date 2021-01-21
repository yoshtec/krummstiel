from krummstiel import krummstiel


class TestKrummstiel:

    def test_wrong_ini1(self):
        args = ["--verbose", "--config", "tests/test_error1.ini"]
        assert krummstiel.main(args) == 2

    def test_wrong_ini2(self):
        args = ["--verbose", "--config", "tests/test_error2.ini"]
        assert krummstiel.main(args) == 2

    #def test_no_args(self):
    #    args = []
    #    assert krummstiel.main(args) == 0

    #def test_missing_args(self):
    #    pass
        #args = ["--config"]
        #assert krummstiel.main(args) == 2