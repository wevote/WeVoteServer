# import_export_jira/tests.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.test import TestCase
from datetime import datetime
from jira import JIRAError
from unittest.mock import Mock, patch
import pandas as pd

from .controllers import (
    format_date,
    sanitize_jira_label,
    JiraSubTask,
    JiraStory,
    JiraEpic,
    JiraExcelLoader,
    JiraApiControl,
)
from .models import JiraApiCounter


class FormatDateTests(TestCase):
    """Test format_date utility function."""

    def test_format_datetime(self):
        """Test formatting a datetime object."""
        dt = datetime(2024, 3, 15, 10, 30, 0)
        result = format_date(dt)
        self.assertEqual(result, "2024-03-15T10:30:00")

    def test_format_string(self):
        """Test formatting a string value."""
        result = format_date("2024-03-15")
        self.assertEqual(result, "2024-03-15")

    def test_format_none(self):
        """Test formatting None value."""
        result = format_date(None)
        self.assertIsNone(result)


class SanitizeJiraLabelTests(TestCase):
    """Test sanitize_jira_label utility function."""

    def test_sanitize_spaces(self):
        """Test that spaces are replaced with underscores."""
        result = sanitize_jira_label("2024 Primary Election")
        self.assertEqual(result, "_2024_Primary_Election")

    def test_sanitize_special_characters(self):
        """Test that special characters are removed."""
        result = sanitize_jira_label("Test@Label#123!")
        self.assertEqual(result, "TestLabel123")

    def test_sanitize_starts_with_number(self):
        """Test that labels starting with numbers get underscore prefix."""
        result = sanitize_jira_label("2024Election")
        self.assertEqual(result, "_2024Election")

    def test_sanitize_empty_string(self):
        """Test handling of empty string."""
        result = sanitize_jira_label("")
        self.assertEqual(result, "")

    def test_sanitize_valid_characters(self):
        """Test that valid characters are preserved."""
        result = sanitize_jira_label("Valid_Label-123.test")
        # Valid characters are preserved (starts with letter, no prefix needed)
        self.assertEqual(result, "Valid_Label-123.test")


class JiraDataClassTests(TestCase):
    """Test JIRA dataclasses."""

    def test_jira_subtask_to_dict(self):
        """Test JiraSubTask serialization."""
        subtask = JiraSubTask(
            task_type="email",
            task_url="http://example.com",
            state="CA",
            due_date=datetime(2024, 11, 5),
        )
        result = subtask.to_dict()
        self.assertEqual(result["task_type"], "email")
        self.assertEqual(result["state"], "CA")
        self.assertIn("2024-11-05", result["due_date"])

    def test_jira_story_to_dict(self):
        """Test JiraStory serialization."""
        story = JiraStory(
            story_title="Test Story",
            office="Governor",
            candidate_name="John Doe",
            candidate_id="CA-GOV-001",
            jurisdiction="Statewide",
            state="CA",
        )
        result = story.to_dict()
        self.assertEqual(result["story_title"], "Test Story")
        self.assertEqual(result["candidate_name"], "John Doe")
        self.assertEqual(result["sub_tasks"], [])

    def test_jira_epic_add_story(self):
        """Test adding stories to epic."""
        epic = JiraEpic(
            epic_title="Test Epic",
            election_date=datetime(2024, 11, 5),
            election_name="2024 General",
            election_id="2024-GEN",
            election_report_url="http://example.com",
        )
        story = JiraStory(
            story_title="Test",
            office="Gov",
            candidate_name="Doe",
            candidate_id="001",
            jurisdiction="State",
            state="CA",
        )
        epic.add_story(story)
        self.assertEqual(epic.get_total_candidates(), 1)


class JiraExcelLoaderTests(TestCase):
    """Test JiraExcelLoader class."""

    def test_load_invalid_file(self):
        """Test loading non-existent file raises error."""
        loader = JiraExcelLoader("/nonexistent/file.xlsx")
        with self.assertRaises(FileNotFoundError):
            loader.load()

    @patch("pandas.read_excel")
    def test_load_insufficient_rows(self, mock_read_excel):
        """Test validation for insufficient rows."""
        mock_read_excel.return_value = pd.DataFrame([[1] * 14])
        loader = JiraExcelLoader("/tmp/test.xlsx")
        with self.assertRaises(ValueError) as context:
            loader.load()
        self.assertIn("at least 2 rows", str(context.exception))

    @patch("pandas.read_excel")
    def test_load_insufficient_columns(self, mock_read_excel):
        """Test validation for insufficient columns."""
        mock_read_excel.return_value = pd.DataFrame([[1] * 5 for _ in range(5)])
        loader = JiraExcelLoader("/tmp/test.xlsx")
        with self.assertRaises(ValueError) as context:
            loader.load()
        self.assertIn("at least 14 columns", str(context.exception))

    @patch("pandas.read_excel")
    def test_load_no_valid_data(self, mock_read_excel):
        """Test validation when no valid data rows found."""
        # Create DataFrame with enough rows/columns but no epic titles
        data = [[None] * 17 for _ in range(5)]
        mock_read_excel.return_value = pd.DataFrame(data)
        loader = JiraExcelLoader("/tmp/test.xlsx")
        with self.assertRaises(ValueError) as context:
            loader.load()
        self.assertIn("No valid data found", str(context.exception))

    @patch("pandas.read_csv")
    def test_load_csv_success(self, mock_read_csv):
        """Test loading a valid CSV file."""
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
                "http://email.com",
                "http://basic.com",
                None,
                None,
            ]
        ]
        rows = [[""] * 18, [""] * 18] + data
        mock_read_csv.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader("/tmp/test.csv")
        epics = loader.load()
        self.assertEqual(len(epics), 1)
        self.assertEqual(len(epics[0].stories), 1)
        mock_read_csv.assert_called_once()

    @patch("pandas.read_excel")
    def test_load_single_header_row_does_not_drop_first_story(
        self, mock_read_excel
    ):
        """
        Regression test: files with a single header row (column names only,
        no extra section-title row) must not lose the first data row's story.
        """
        header = [
            "Election Date",
            "Epic Title",
            "Election Name",
            "Election Id",
            "Report URL",
            "Office",
            "Jurisdiction",
            "State",
            "County Code",
            "County",
            "Local Name",
            "Candidate Name",
            "Candidate Id",
            "Story Title",
        ] + [""] * 4
        first_row = [
            "2024-11-05",
            "2024 General: Senate",
            "General",
            "G-001",
            "url",
            "Senate",
            "Statewide",
            "CA",
            "001",
            "County",
            "",
            "First Candidate",
            "C-001",
            "First Candidate - Senate",
        ] + [""] * 4
        second_row = [
            "2024-11-05",
            "2024 General: Senate",
            "General",
            "G-001",
            "url",
            "Senate",
            "Statewide",
            "CA",
            "001",
            "County",
            "",
            "Second Candidate",
            "C-002",
            "Second Candidate - Senate",
        ] + [""] * 4
        mock_read_excel.return_value = pd.DataFrame([header, first_row, second_row])
        loader = JiraExcelLoader("/tmp/test.xlsx")
        epics = loader.load()
        self.assertEqual(len(epics), 1)
        candidate_names = [s.candidate_name for s in epics[0].stories]
        self.assertIn("First Candidate", candidate_names)
        self.assertIn("Second Candidate", candidate_names)
        self.assertEqual(len(epics[0].stories), 2)

    @patch("pandas.read_csv")
    def test_load_csv_with_override(self, mock_read_csv):
        """Test file_format='csv' override on an xlsx-named file."""
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
                None,
                None,
                None,
                None,
            ]
        ]
        rows = [[""] * 18, [""] * 18] + data
        mock_read_csv.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader("/tmp/test.xlsx", file_format="csv")
        epics = loader.load()
        self.assertEqual(len(epics), 1)
        mock_read_csv.assert_called_once()

    def test_load_unsupported_format(self):
        """Test loading a file with unsupported extension raises error."""
        loader = JiraExcelLoader("/tmp/test.dat")
        with self.assertRaises(ValueError) as context:
            loader.load()
        self.assertIn("Unsupported file format", str(context.exception))

    @patch("pandas.read_excel")
    def test_dynamic_subtasks_custom_names(self, mock_read_excel):
        """Test manually entered subtask names are applied to every story,
        independent of any file columns (manual mode doesn't read file data)."""
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
            ]
        ]
        rows = [[""] * 14, [""] * 14] + data
        mock_read_excel.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader(
            "/tmp/test.xlsx", subtask_names=["Research", "Verify", "Final Review"]
        )
        epics = loader.load()
        stories = epics[0].stories
        self.assertEqual(len(stories[0].sub_tasks), 3)
        self.assertEqual(stories[0].sub_tasks[0].task_type, "Research")
        self.assertIsNone(stories[0].sub_tasks[0].task_url)
        self.assertEqual(stories[0].sub_tasks[1].task_type, "Verify")
        self.assertEqual(stories[0].sub_tasks[2].task_type, "Final Review")

    @patch("pandas.read_excel")
    def test_dynamic_subtasks_zero(self, mock_read_excel):
        """Test zero subtasks creates no subtask objects."""
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
                "http://email.com",
                None,
                None,
                None,
            ]
        ]
        rows = [[""] * 18, [""] * 18] + data
        mock_read_excel.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader("/tmp/test.xlsx", subtask_names=[])
        epics = loader.load()
        self.assertEqual(len(epics[0].stories[0].sub_tasks), 0)

    @patch("pandas.read_excel")
    def test_dynamic_subtasks_four(self, mock_read_excel):
        """Test creating 4 subtasks (max)."""
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
                "http://u1.com",
                "http://u2.com",
                "http://u3.com",
                "http://u4.com",
            ]
        ]
        rows = [[""] * 18, [""] * 18] + data
        mock_read_excel.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader(
            "/tmp/test.xlsx", subtask_names=["Research", "Verify", "Review", "Publish"]
        )
        epics = loader.load()
        self.assertEqual(len(epics[0].stories[0].sub_tasks), 4)
        self.assertEqual(epics[0].stories[0].sub_tasks[3].task_type, "Publish")

    @patch("pandas.read_excel")
    def test_dynamic_subtasks_skips_empty_cols(self, mock_read_excel):
        """Test file-driven subtasks are only created for non-empty URL
        columns (per-story blank cells are legitimately skipped). This only
        applies in file-driven mode (subtask_names=None, auto-detected from
        headers) — manual mode ignores file columns entirely."""
        header_row = ["Election Date"] + [""] * 13 + [
            "Research",
            "Verify",
            "Review",
            None,
        ]
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
                "http://u1.com",
                None,
                "http://u3.com",
                None,
            ]
        ]
        rows = [["dummy"] * 18, header_row] + data
        mock_read_excel.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader("/tmp/test.xlsx")
        epics = loader.load()
        self.assertEqual(len(epics[0].stories[0].sub_tasks), 2)
        self.assertEqual(epics[0].stories[0].sub_tasks[0].task_type, "Research")
        self.assertEqual(epics[0].stories[0].sub_tasks[0].task_url, "http://u1.com")
        self.assertEqual(epics[0].stories[0].sub_tasks[1].task_type, "Review")
        self.assertEqual(epics[0].stories[0].sub_tasks[1].task_url, "http://u3.com")

    def test_load_empty_file_path(self):
        """Test that empty file_path raises ValueError."""
        loader = JiraExcelLoader("")
        with self.assertRaises(ValueError) as context:
            loader.load()
        self.assertIn("file_path must be a non-empty string", str(context.exception))

    @patch("pandas.read_excel")
    def test_dynamic_subtasks_skips_empty_names(self, mock_read_excel):
        """Test that empty subtask names are skipped during creation."""
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
                "http://u1.com",
                "http://u2.com",
                "http://u3.com",
                None,
            ]
        ]
        rows = [[""] * 18, [""] * 18] + data
        mock_read_excel.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader(
            "/tmp/test.xlsx", subtask_names=["Research", "", "Review"]
        )
        epics = loader.load()
        self.assertEqual(len(epics[0].stories[0].sub_tasks), 2)
        self.assertEqual(epics[0].stories[0].sub_tasks[0].task_type, "Research")
        self.assertEqual(epics[0].stories[0].sub_tasks[1].task_type, "Review")

    @patch("pandas.read_excel")
    def test_dynamic_subtasks_beyond_file_columns(self, mock_read_excel):
        """Test that manually-named subtasks are still created even when the
        file has no matching column for them — manual names aren't tied to
        file columns, so the subtask is created with no task_url."""
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
            ]
        ]
        rows = [[""] * 14, [""] * 14] + data
        mock_read_excel.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader("/tmp/test.xlsx", subtask_names=["Research", "Verify"])
        epics = loader.load()
        sub_tasks = epics[0].stories[0].sub_tasks
        self.assertEqual(len(sub_tasks), 2)
        self.assertEqual(sub_tasks[0].task_type, "Research")
        self.assertIsNone(sub_tasks[0].task_url)
        self.assertEqual(sub_tasks[1].task_type, "Verify")
        self.assertIsNone(sub_tasks[1].task_url)

    @patch("pandas.read_excel")
    def test_get_summary_returns_header_suggestions(self, mock_read_excel):
        """Test that get_summary returns header_suggestions from row 0."""
        header_row = ["dummy"] * 14 + ["Research URL", "Verify URL", "Review URL", None]
        data_row = [
            "2024-11-05",
            "2024 General: Test",
            "General",
            "G-001",
            "url",
            "Office",
            "Jurisdiction",
            "CA",
            "001",
            "County",
            "Local",
            "John Doe",
            "JD-001",
            "Story Title",
            "http://u1.com",
            "http://u2.com",
            "http://u3.com",
            None,
        ]
        rows = [header_row, [""] * 18, data_row]
        mock_read_excel.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader("/tmp/test.xlsx")
        summary = loader.get_summary()
        self.assertIn("header_suggestions", summary)
        self.assertEqual(
            summary["header_suggestions"], ["Research URL", "Verify URL", "Review URL"]
        )

    @patch("pandas.read_excel")
    def test_get_summary_header_suggestions_empty_when_no_headers(
        self, mock_read_excel
    ):
        """Test that header_suggestions is empty when row 0 has no subtask headers."""
        data = [
            [
                "2024-11-05",
                "2024 General: Test",
                "General",
                "G-001",
                "url",
                "Office",
                "Jurisdiction",
                "CA",
                "001",
                "County",
                "Local",
                "John Doe",
                "JD-001",
                "Story Title",
                None,
                None,
                None,
                None,
            ]
        ]
        rows = [[""] * 18, [""] * 18] + data
        mock_read_excel.return_value = pd.DataFrame(rows)
        loader = JiraExcelLoader("/tmp/test.xlsx")
        summary = loader.get_summary()
        self.assertEqual(summary["header_suggestions"], [])


class JiraApiCounterTests(TestCase):
    """Test JiraApiCounter model and manager."""

    def test_create_counter_entry_success(self):
        """Test successful counter entry creation."""
        result = JiraApiCounter.objects.create_counter_entry("create_epic")
        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "ENTRY_SAVED")
        self.assertEqual(JiraApiCounter.objects.count(), 1)

    def test_create_counter_entry_stores_action(self):
        """Test that counter entry stores the action type."""
        JiraApiCounter.objects.create_counter_entry("bulk_create_50")
        counter = JiraApiCounter.objects.first()
        self.assertEqual(counter.kind_of_action, "bulk_create_50")
        self.assertIsNotNone(counter.datetime_of_action)

    def test_counter_str_representation(self):
        """Test string representation of counter."""
        JiraApiCounter.objects.create_counter_entry("test_action")
        counter = JiraApiCounter.objects.first()
        str_repr = str(counter)
        self.assertIn("test_action", str_repr)


class JiraApiControlTests(TestCase):
    """Test JiraApiControl class."""

    @patch("import_export_jira.controllers.JIRA")
    def test_init_success(self, mock_jira_class):
        """Test successful initialization."""
        mock_jira_class.return_value = Mock()
        control = JiraApiControl(
            jira_url="https://jira.example.com",
            username="test@example.com",
            api_token="token123",
            project_key="TEST",
        )
        self.assertEqual(control.project_key, "TEST")
        self.assertEqual(control.stats["epics_created"], 0)

    @patch("import_export_jira.controllers.JIRA")
    def test_extract_election_label(self, mock_jira_class):
        """Test election label extraction and sanitization."""
        mock_jira_class.return_value = Mock()
        control = JiraApiControl("url", "user", "token", "KEY")

        # Test with valid pattern
        label = control._extract_election_label("2024 Primary: Arkansas")
        self.assertEqual(label, "_2024_Primary")

        # Test with no match
        label = control._extract_election_label("No Pattern Here")
        self.assertIsNone(label)

    @patch("import_export_jira.controllers.JIRA")
    def test_create_issues_bulk_empty_list(self, mock_jira_class):
        """Test bulk creation with empty list."""
        mock_jira_class.return_value = Mock()
        control = JiraApiControl("url", "user", "token", "KEY")
        result = control.create_issues_bulk([])
        self.assertEqual(result, [])

    @patch("import_export_jira.controllers.JIRA")
    def test_rate_limiting(self, mock_jira_class):
        """Test that rate limiting adds delays between API calls."""
        mock_jira_class.return_value = Mock()
        control = JiraApiControl("url", "user", "token", "KEY", rate_limit_delay=0.1)

        import time

        start_time = time.time()
        control._rate_limit()
        control._rate_limit()
        control._rate_limit()
        elapsed = time.time() - start_time

        # Should have at least 2 delays (0.1s each)
        self.assertGreater(elapsed, 0.15)
        self.assertEqual(control.stats["api_calls"], 3)

    @patch("import_export_jira.controllers.JIRA")
    def test_rate_limiting_disabled(self, mock_jira_class):
        """Test that rate limiting can be disabled."""
        mock_jira_class.return_value = Mock()
        control = JiraApiControl("url", "user", "token", "KEY", rate_limit_delay=0)

        import time

        start_time = time.time()
        control._rate_limit()
        control._rate_limit()
        control._rate_limit()
        elapsed = time.time() - start_time

        # Should be very fast with no rate limiting
        self.assertLess(elapsed, 0.05)


class RetryLogicTests(TestCase):
    """Test retry and backoff logic."""

    def test_retry_on_rate_limit(self):
        """Test that 429 rate limit errors trigger retry."""
        from import_export_jira.controllers import retry_on_jira_error

        mock_func = Mock()
        # First call raises 429, second succeeds
        error = JIRAError(status_code=429, text="Rate limited")
        mock_func.side_effect = [error, "success"]

        decorated = retry_on_jira_error(max_retries=1, initial_delay=0.01)(mock_func)
        result = decorated()

        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 2)

    def test_no_retry_on_client_error(self):
        """Test that 4xx client errors don't retry (except 429)."""
        from import_export_jira.controllers import retry_on_jira_error

        mock_func = Mock()
        error = JIRAError(status_code=400, text="Bad request")
        mock_func.side_effect = error

        decorated = retry_on_jira_error(max_retries=3, initial_delay=0.01)(mock_func)

        with self.assertRaises(JIRAError):
            decorated()

        # Should fail immediately without retries
        self.assertEqual(mock_func.call_count, 1)

    def test_retry_exhaustion(self):
        """Test that retries eventually give up."""
        from import_export_jira.controllers import retry_on_jira_error

        mock_func = Mock()
        error = JIRAError(status_code=500, text="Server error")
        mock_func.side_effect = error

        decorated = retry_on_jira_error(max_retries=2, initial_delay=0.01)(mock_func)

        with self.assertRaises(JIRAError):
            decorated()

        # Should try 3 times total (initial + 2 retries)
        self.assertEqual(mock_func.call_count, 3)
