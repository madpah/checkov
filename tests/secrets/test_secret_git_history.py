from __future__ import annotations
from unittest import mock
from pytest_mock import MockerFixture

from detect_secrets import SecretsCollection

from checkov.secrets.runner import Runner
from checkov.runner_filter import RunnerFilter
from detect_secrets.settings import transient_settings
from checkov.common.output.secrets_record import COMMIT_REMOVED_STR, COMMIT_ADDED_STR

from tests.secrets.git_history.test_utils import mock_git_repo_commits1, mock_git_repo_commits2, mock_git_repo_commits3, \
    mock_git_repo_commits_too_much, mock_git_repo_commits_remove_file, mock_git_repo_commits_rename_file, \
    mock_git_repo_commits_modify_and_rename_file, mock_remove_file_with_two_equal_secret, \
    mock_remove_file_with_two_secret, mock_git_repo_multiline_json, mock_git_repo_multiline_terraform, \
    mock_git_repo_multiline_yml


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_commits1)
def test_scan_git_history() -> None:
    valid_dir_path = "test"

    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 3
    assert len(report.parsing_errors) == 0
    assert len(report.passed_checks) == 0
    assert len(report.parsing_errors) == 0
    assert len(report.skipped_checks) == 0
    for failed_check in report.failed_checks:
        assert failed_check.added_commit_hash or failed_check.removed_commit_hash


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_commits1)
def test_scan_history_secrets() -> None:
    valid_dir_path = "test"
    secrets = SecretsCollection()
    plugins_used = [
        {'name': 'AWSKeyDetector'},
    ]
    from checkov.secrets.scan_git_history import GitHistoryScanner

    with transient_settings({
        # Only run scans with only these plugins.
        'plugins_used': plugins_used
    }) as settings:
        settings.disable_filters(*['detect_secrets.filters.common.is_invalid_file'])
        GitHistoryScanner(valid_dir_path, secrets).scan_history()
    assert len(secrets.data) == 3


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_commits2)
def test_scan_git_history_merge_added_removed() -> None:
    """
    add, move, remove, add, move = secret with the first added_commit_hash and not removed_commit_hash
    """
    valid_dir_path = "test"

    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 1
    for failed_check in report.failed_checks:
        assert failed_check.removed_commit_hash is None
        assert failed_check.added_commit_hash == '11e59e4e578c6ebcb48aae1e5e078a54c62920eb'


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_commits2)
def test_scan_history_secrets_merge_added_removed() -> None:
    valid_dir_path = "test"
    secrets = SecretsCollection()
    plugins_used = [
        {'name': 'AWSKeyDetector'},
    ]
    from checkov.secrets.scan_git_history import GitHistoryScanner

    with transient_settings({
        # Only run scans with only these plugins.
        'plugins_used': plugins_used
    }) as settings:
        settings.disable_filters(*['detect_secrets.filters.common.is_invalid_file'])
        GitHistoryScanner(valid_dir_path, secrets).scan_history()
    assert len(secrets.data) == 1


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_commits3)
def test_scan_git_history_merge_added_removed2() -> None:
    """
        add, move, add, remove one = 2 secret one with removed_commit_hash && added_commit_hash
        and one with only added_commit_hash
    """
    valid_dir_path = "/Users/lshindelman/development/test2"

    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 2
    assert ((report.failed_checks[0].removed_commit_hash == '697308e61171e33224757e620aaf67b1a877c99d'
             and report.failed_checks[1].removed_commit_hash is None)
            or (report.failed_checks[1].removed_commit_hash == '697308e61171e33224757e620aaf67b1a877c99d'
                and report.failed_checks[0].removed_commit_hash is None))
    assert ((report.failed_checks[0].added_commit_hash == '900b1e8f6f336a92e8f5fca3babca764e32c3b3d'
             and report.failed_checks[1].added_commit_hash == '3c8cb7eedb3986308c96713fc65b006adcf3bc44')
            or (report.failed_checks[1].added_commit_hash == '900b1e8f6f336a92e8f5fca3babca764e32c3b3d'
                and report.failed_checks[0].added_commit_hash == '3c8cb7eedb3986308c96713fc65b006adcf3bc44'))
    # print testing
    assert_for_commit_str(report.failed_checks[0].to_string() + report.failed_checks[1].to_string(),
                          commit_type=COMMIT_REMOVED_STR,
                          commit_hash='697308e61171e33224757e620aaf67b1a877c99d')
    assert_for_commit_str(report.failed_checks[0].to_string() + report.failed_checks[1].to_string(),
                          commit_type=COMMIT_ADDED_STR,
                          commit_hash='3c8cb7eedb3986308c96713fc65b006adcf3bc44')
    assert_for_commit_str(report.failed_checks[0].to_string() + report.failed_checks[1].to_string(),
                          commit_type=COMMIT_ADDED_STR,
                          commit_hash='900b1e8f6f336a92e8f5fca3babca764e32c3b3d')


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_commits_too_much)
def test_scan_history_secrets_timeout() -> None:
    """
    add way too many cases to check in 1 second
    """
    valid_dir_path = "test"
    secrets = SecretsCollection()
    plugins_used = [
        {'name': 'AWSKeyDetector'},
    ]
    from checkov.secrets.scan_git_history import GitHistoryScanner

    with transient_settings({
        # Only run scans with only these plugins.
        'plugins_used': plugins_used
    }) as settings:
        settings.disable_filters(*['detect_secrets.filters.common.is_invalid_file'])
        finished = GitHistoryScanner(valid_dir_path, secrets, None, 1).scan_history()

    assert finished is False


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_commits_remove_file)
def test_scan_git_history_remove_file() -> None:
    valid_dir_path = "remove_file"

    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 1
    assert (report.failed_checks[0].removed_commit_hash == '4bd08cd0b2874025ce32d0b1e9cd84ca20d59ce1' and
            report.failed_checks[0].added_commit_hash == '63342dbee285973a37770bbb1ff4258a3184901e')


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_commits_rename_file)
def test_scan_git_history_rename_file() -> None:
    valid_dir_path = "/test/git/history/rename/file"

    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 2
    assert (report.failed_checks[0].removed_commit_hash is None and
            report.failed_checks[0].added_commit_hash == '2e1a500e688990e065fc6f1202bc64ed0ba53027')
    assert (report.failed_checks[1].removed_commit_hash == '2e1a500e688990e065fc6f1202bc64ed0ba53027' and
            report.failed_checks[1].added_commit_hash == 'adef7360b86c62666f0a70521214220763b9c593')


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff',
            mock_git_repo_commits_modify_and_rename_file)
def test_scan_git_history_modify_and_rename_file() -> None:
    valid_dir_path = "test_scan_git_history_modify_and_rename_file"

    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 1
    assert (report.failed_checks[0].removed_commit_hash == '61ee79aea3d151a40c8e054295f330d233eaf7d5' and
            report.failed_checks[0].added_commit_hash == '62da8e5e04ec5c3a474467e9012bf3427cff0407')


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff',
            mock_remove_file_with_two_equal_secret)
def test_scan_git_history_rename_file_with_two_equal_secrets() -> None:
    valid_dir_path = "test_scan_git_history_rename_file_with_two_equal_secrets"
    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 2
    assert (report.failed_checks[0].removed_commit_hash == report.failed_checks[1].removed_commit_hash and
            report.failed_checks[1].removed_commit_hash is not None)


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_remove_file_with_two_secret)
def test_scan_git_history_rename_file_with_two_secrets() -> None:
    valid_dir_path = "test_scan_git_history_rename_file_with_two_secrets"
    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 2
    assert (report.failed_checks[0].removed_commit_hash == report.failed_checks[1].removed_commit_hash and
            report.failed_checks[1].removed_commit_hash is not None)


def assert_for_commit_str(report_str: [str], commit_type: str, commit_hash: str, found: bool = True) -> None:
    to_find = f'; {commit_type}: {commit_hash}'
    assert (to_find in report_str) == found


# added all file scenarios from multiline tests
@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff',
            mock_git_repo_multiline_json)
def test_scan_git_history_multiline_keyword_json() -> None:
    valid_dir_path = "multiline_keyword_json"

    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 5
    assert report.parsing_errors == []
    assert report.passed_checks == []
    assert report.skipped_checks == []


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_multiline_terraform)
def test_scan_git_history_multiline_keyword_terraform() -> None:
    valid_dir_path = "mock_git_repo_multiline_terraform"

    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    #  then
    failing_resources = {
        "dcbf46de362e1b6942054b89ee293984e9a8a40a",
        "ac236b0474a9a702f99dbe244a14548783ace5c5",
        "9ed4f1457a9c27dd868c1f21276c6d7098d2bacf",
        "06af723e58378574456be0b4c41a89194aaed0c3",
        "5db2fafebcfed9b4c9ffc570c46ef2ca94a3881a",
    }

    failed_check_resources = {c.resource for c in report.failed_checks}

    assert len(report.failed_checks) == len(failing_resources)
    assert report.parsing_errors == []
    assert report.passed_checks == []
    assert report.skipped_checks == []
    assert failing_resources == failed_check_resources


@mock.patch('checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff', mock_git_repo_multiline_yml)
def test_scan_git_history_multiline_keyword_yml() -> None:
    valid_dir_path = "mock_git_repo_multiline_yml"
    runner = Runner()

    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 5
    assert report.parsing_errors == []
    assert report.passed_checks == []
    assert report.skipped_checks == []


def test_scan_git_history_middle(mocker: MockerFixture) -> None:
    """
    this test tries to run a full scan over 5 commits,
    then run two separate runs over the first 2 and the last 3 (the second will give the secret store to the third)
    then compares the results from run 1 to the last run
    """
    valid_dir_path = "test"

    all_commits = mock_git_repo_commits1('', '')
    commits_keys = [x for x in all_commits.keys()]
    mocker.patch(
        "checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff",
        return_value=all_commits,
    )
    runner = Runner()
    report = runner.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report.failed_checks) == 3
    for failed_check in report.failed_checks:
        assert failed_check.added_commit_hash or failed_check.removed_commit_hash

    mocker.patch(
        "checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff",
        return_value={commits_keys[0]: all_commits[commits_keys[0]],
                      commits_keys[1]: all_commits[commits_keys[1]]},
    )
    runner2 = Runner()
    report2 = runner2.run(root_folder=valid_dir_path, external_checks_dir=None,
                        runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report2.failed_checks) == 1
    sec_store = runner2.get_history_secret_store()

    mocker.patch(
        "checkov.secrets.scan_git_history.GitHistoryScanner._get_commits_diff",
        return_value={commits_keys[2]: all_commits[commits_keys[2]],
                      commits_keys[3]: all_commits[commits_keys[3]],
                      commits_keys[4]: all_commits[commits_keys[4]]},
    )
    runner3 = Runner()
    runner3.set_history_secret_store(sec_store)
    report3 = runner2.run(root_folder=valid_dir_path, external_checks_dir=None,
                          runner_filter=RunnerFilter(framework=['secrets'], enable_git_history_secret_scan=True))
    assert len(report3.failed_checks) == 3
    assert len(report3.parsing_errors) == 0
    assert len(report3.passed_checks) == 0
    assert len(report3.parsing_errors) == 0
    assert len(report3.skipped_checks) == 0
    for failed_check in report3.failed_checks:
        assert failed_check.added_commit_hash or failed_check.removed_commit_hash

