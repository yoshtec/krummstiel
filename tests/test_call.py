from krummstiel import krummstiel
from click.testing import CliRunner


class TestKrummstiel:

    def test_wrong_ini1(self):
        runner = CliRunner()
        result = runner.invoke(krummstiel.backup, ['--config', "./tests/test_error1.ini", "-vv"])
        assert result.exit_code == 2

    def test_wrong_ini2(self):
        runner = CliRunner()
        result = runner.invoke(krummstiel.backup, ['--config', "./tests/test_error2.ini", "-vv"])
        assert result.exit_code == 2

    # def test_no_args(self):
    #    args = []
    #    assert krummstiel.main(args) == 0

    # def test_missing_args(self):
    #    pass
    # args = ["--config"]
    # assert krummstiel.main(args) == 2
