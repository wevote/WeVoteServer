# import_export_jira/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import os
import re
import time
import logging
import pandas as pd
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
from jira import JIRA
from jira.exceptions import JIRAError
from .models import JiraApiCounter

logger = logging.getLogger(__name__)

# Rate limiting and retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0  # seconds
MAX_RETRY_DELAY = 30.0  # seconds
RATE_LIMIT_DELAY = 0.5  # seconds between API calls


def retry_on_jira_error(
    max_retries=MAX_RETRIES,
    initial_delay=INITIAL_RETRY_DELAY,
    max_delay=MAX_RETRY_DELAY,
):
    """
    Decorator to retry JIRA API calls with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except JIRAError as e:
                    last_exception = e
                    # Check if error is retryable (rate limit, timeout, server error)
                    status_code = getattr(e, "status_code", None)

                    # Don't retry client errors (400-499) except rate limits (429)
                    if status_code and 400 <= status_code < 500 and status_code != 429:
                        logger.error(
                            f"Non-retryable JIRA error (status {status_code}): {e}"
                        )
                        raise

                    if attempt < max_retries:
                        logger.warning(
                            f"JIRA API call failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {delay}s: {e}"
                        )
                        time.sleep(delay)
                        delay = min(
                            delay * 2, max_delay
                        )  # Exponential backoff with cap
                    else:
                        logger.error(
                            f"JIRA API call failed after {max_retries + 1} attempts: {e}"
                        )
                        raise last_exception

            # Should never reach here, but just in case
            raise last_exception

        return wrapper

    return decorator


# Excel column indices
COL_ELECTION_DATE = 0
COL_EPIC_TITLE = 1
COL_ELECTION_NAME = 2
COL_ELECTION_ID = 3
COL_ELECTION_REPORT_URL = 4
COL_OFFICE = 5
COL_JURISDICTION = 6
COL_STATE = 7
COL_COUNTY_CODE = 8
COL_COUNTY = 9
COL_LOCAL_NAME = 10
COL_CANDIDATE_NAME = 11
COL_CANDIDATE_ID = 12
COL_STORY_TITLE = 13
COL_SUBTASK_URL_START = 14
MAX_SUBTASK_COLUMNS = 4


def format_date(date_value: Optional[Union[datetime, str]]) -> Optional[str]:
    """Format date value to ISO string format."""
    if isinstance(date_value, datetime):
        return date_value.isoformat()
    elif date_value:
        return str(date_value)
    return None


def sanitize_jira_label(label: str) -> str:
    """
    Sanitize a string to be valid as a JIRA label.
    JIRA labels cannot contain spaces and special characters like @, #, !, etc.

    Args:
        label: Raw label string

    Returns:
        Sanitized label safe for JIRA
    """
    if not label:
        return label
    # Replace spaces with underscores
    label = label.replace(" ", "_")
    # Remove special characters that JIRA doesn't allow in labels
    # Keep alphanumeric, underscore, hyphen, and period
    label = re.sub(r"[^a-zA-Z0-9_\-\.]", "", label)
    # Ensure label doesn't start with a number (JIRA restriction)
    if label and label[0].isdigit():
        label = "_" + label
    return label


@dataclass
class JiraSubTask:
    task_type: str
    task_url: Optional[str] = None
    task_id: Optional[str] = None
    state: Optional[str] = None
    election_date: Optional[datetime] = None
    county: Optional[str] = None
    due_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "task_url": self.task_url,
            "task_id": self.task_id,
            "state": self.state,
            "election_date": format_date(self.election_date),
            "county": self.county,
            "due_date": format_date(self.due_date),
        }


@dataclass
class JiraStory:
    story_title: str
    office: str
    candidate_name: str
    candidate_id: str
    jurisdiction: str
    state: str
    county_code: Optional[str] = None
    county: Optional[str] = None
    local_name: Optional[str] = None
    election_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    sub_tasks: List[JiraSubTask] = field(default_factory=list)

    def add_sub_task(self, sub_task: JiraSubTask):
        self.sub_tasks.append(sub_task)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_title": self.story_title,
            "office": self.office,
            "candidate_name": self.candidate_name,
            "candidate_id": self.candidate_id,
            "jurisdiction": self.jurisdiction,
            "state": self.state,
            "county_code": self.county_code,
            "county": self.county,
            "local_name": self.local_name,
            "election_date": format_date(self.election_date),
            "due_date": format_date(self.due_date),
            "sub_tasks": [st.to_dict() for st in self.sub_tasks],
        }


@dataclass
class JiraEpic:
    epic_title: str
    election_date: datetime
    election_name: str
    election_id: str
    election_report_url: str
    state: Optional[str] = None
    county: Optional[str] = None
    due_date: Optional[datetime] = None
    stories: List[JiraStory] = field(default_factory=list)

    def add_story(self, story: JiraStory):
        self.stories.append(story)

    def get_total_candidates(self) -> int:
        return len(self.stories)

    def get_total_sub_tasks(self) -> int:
        return sum(len(s.sub_tasks) for s in self.stories)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "epic_title": self.epic_title,
            "election_date": format_date(self.election_date),
            "election_name": self.election_name,
            "election_id": self.election_id,
            "election_report_url": self.election_report_url,
            "state": self.state,
            "county": self.county,
            "due_date": format_date(self.due_date),
            "stories": [s.to_dict() for s in self.stories],
        }


class JiraCustomFields:
    EPIC_NAME = "customfield_10011"
    EPIC_LINK = "customfield_10014"
    DUE_DATE = "customfield_10623"
    ELECTION_ID = "customfield_10624"
    STATE = "customfield_10763"
    COUNTY = "customfield_10693"
    CANDIDATE_NAME = "customfield_10695"
    OFFICE = "customfield_10658"


class JiraExcelLoader:
    """
    Loader for parsing Arkansas-style election Excel files into JIRA epic/story/subtask structures.
    """

    def __init__(
        self,
        file_path: str,
        file_format: Optional[str] = None,
        subtask_names: Optional[List[str]] = None,
    ):
        self.file_path = file_path
        self.file_format = file_format
        self.subtask_names = subtask_names  # None means auto-detect from file headers
        self.df: Optional[pd.DataFrame] = None
        self.epics: Optional[List[JiraEpic]] = None
        self.header_row_index: int = 0

    def _detect_header_row_count(self) -> int:
        """
        Detect how many leading rows are headers by finding the first row
        whose Election Date column holds a real, parseable date rather than
        header text (e.g. "Election Date" or a section title like "JIRA EPIC").

        Returns:
            Number of leading header rows (defaults to 2 if detection fails,
            matching the legacy Arkansas-style template).
        """
        max_check = min(5, self.df.shape[0])
        for row_idx in range(max_check):
            val = self.df.iloc[row_idx, COL_ELECTION_DATE]
            if pd.isna(val):
                continue
            if isinstance(val, (datetime, pd.Timestamp)):
                return row_idx
            try:
                pd.to_datetime(val)
                return row_idx
            except (ValueError, TypeError):
                continue
        logger.warning(
            "Could not auto-detect header row count from Election Date column; "
            "defaulting to 2 header rows."
        )
        return 2

    def load(self) -> List[JiraEpic]:
        """
        Load and parse the Excel file into JIRA data structures.

        Returns:
            List of JiraEpic objects

        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
            pd.errors.ParserError: If Excel file is corrupted
        """
        if not self.file_path:
            raise ValueError("file_path must be a non-empty string")
        ext = os.path.splitext(self.file_path)[1].lower()
        if self.file_format == "csv" or (not self.file_format and ext == ".csv"):
            read_func = pd.read_csv
            read_kwargs = {"header": None, "sep": ","}
        elif self.file_format == "excel" or (
            not self.file_format and ext in (".xlsx", ".xls")
        ):
            read_func = pd.read_excel
            read_kwargs = {"header": None}
        else:
            raise ValueError(
                f"Unsupported file format for '{self.file_path}'. "
                f"Use .xlsx, .xls, or .csv files, or set file_format='csv'/'excel'."
            )

        try:
            self.df = read_func(self.file_path, **read_kwargs)
        except FileNotFoundError:
            logger.error(f"File not found: {self.file_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            raise ValueError(f"Invalid or corrupted file: {e}") from e

        # Validate minimum structure
        if self.df.shape[0] < 2:
            raise ValueError("File must have at least 2 rows (headers + data)")
        if self.df.shape[1] < COL_STORY_TITLE + 1:
            raise ValueError(
                f"File must have at least {COL_STORY_TITLE + 1} columns, found {self.df.shape[1]}"
            )

        # Detect how many leading rows are headers. Some files have a single
        # header row (column names only); others (e.g. the Arkansas-style
        # template) have an extra section-title row above the column names.
        # Hardcoding this caused the first real data row to be silently
        # dropped for single-header-row files.
        header_row_count = self._detect_header_row_count()
        self.header_row_index = header_row_count - 1

        # Validate that we have data rows (not just headers)
        data_df = self.df.iloc[header_row_count:].reset_index(drop=True)
        if data_df.empty:
            raise ValueError("Excel file contains no data rows")

        # Log file statistics and warn for large files
        num_rows = len(data_df)
        logger.info(
            f"Loading file with {num_rows} data rows and {self.df.shape[1]} columns"
        )

        # Warn for large files that may cause performance issues
        if num_rows > 1000:
            logger.warning(
                f"Large file detected: {num_rows} rows. "
                f"Processing may take several minutes and use significant memory."
            )
        if num_rows > 5000:
            logger.warning(
                f"Very large file detected: {num_rows} rows. "
                f"Consider splitting into smaller batches to avoid timeout or memory issues."
            )

        manual_subtasks = self.subtask_names is not None
        if self.subtask_names is None:
            self.subtask_names = []
            for i in range(MAX_SUBTASK_COLUMNS):
                col = COL_SUBTASK_URL_START + i
                if col < self.df.shape[1] and pd.notna(
                    self.df.iloc[self.header_row_index, col]
                ):
                    val = str(self.df.iloc[self.header_row_index, col]).strip()
                    if val:
                        self.subtask_names.append(val)

        epics_dict: Dict[str, JiraEpic] = {}
        rows_with_epic_title = 0

        for row_idx, row in data_df.iterrows():
            epic_title = (
                row.iloc[COL_EPIC_TITLE] if pd.notna(row.iloc[COL_EPIC_TITLE]) else None
            )
            if not epic_title:
                continue

            rows_with_epic_title += 1

            if epic_title not in epics_dict:
                election_date = (
                    row.iloc[COL_ELECTION_DATE]
                    if pd.notna(row.iloc[COL_ELECTION_DATE])
                    else None
                )
                state = row.iloc[COL_STATE] if pd.notna(row.iloc[COL_STATE]) else None
                county = (
                    row.iloc[COL_COUNTY] if pd.notna(row.iloc[COL_COUNTY]) else None
                )

                epics_dict[epic_title] = JiraEpic(
                    epic_title=epic_title,
                    election_date=election_date,
                    election_name=row.iloc[COL_ELECTION_NAME]
                    if pd.notna(row.iloc[COL_ELECTION_NAME])
                    else "",
                    election_id=row.iloc[COL_ELECTION_ID]
                    if pd.notna(row.iloc[COL_ELECTION_ID])
                    else "",
                    election_report_url=row.iloc[COL_ELECTION_REPORT_URL]
                    if pd.notna(row.iloc[COL_ELECTION_REPORT_URL])
                    else "",
                    state=state,
                    county=county,
                    due_date=election_date,
                )

            epic = epics_dict[epic_title]
            office = row.iloc[COL_OFFICE] if pd.notna(row.iloc[COL_OFFICE]) else ""
            candidate_name = (
                row.iloc[COL_CANDIDATE_NAME]
                if pd.notna(row.iloc[COL_CANDIDATE_NAME])
                else ""
            )
            story_title = (
                row.iloc[COL_STORY_TITLE]
                if pd.notna(row.iloc[COL_STORY_TITLE])
                else f"{office} - {candidate_name}"
            )

            story = JiraStory(
                story_title=story_title,
                office=office,
                candidate_name=candidate_name,
                candidate_id=row.iloc[COL_CANDIDATE_ID]
                if pd.notna(row.iloc[COL_CANDIDATE_ID])
                else "",
                jurisdiction=row.iloc[COL_JURISDICTION]
                if pd.notna(row.iloc[COL_JURISDICTION])
                else "",
                state=row.iloc[COL_STATE] if pd.notna(row.iloc[COL_STATE]) else "",
                county_code=row.iloc[COL_COUNTY_CODE]
                if pd.notna(row.iloc[COL_COUNTY_CODE])
                else None,
                county=row.iloc[COL_COUNTY] if pd.notna(row.iloc[COL_COUNTY]) else None,
                local_name=row.iloc[COL_LOCAL_NAME]
                if pd.notna(row.iloc[COL_LOCAL_NAME])
                else None,
                election_date=epic.election_date,
                due_date=epic.due_date,
            )

            common_subtask_fields = {
                "state": story.state,
                "election_date": story.election_date,
                "county": story.county,
                "due_date": story.due_date,
            }

            for i, name in enumerate(self.subtask_names[:MAX_SUBTASK_COLUMNS]):
                if not name:
                    continue
                if manual_subtasks:
                    # Manually entered subtask descriptions replace file-driven
                    # subtasks entirely — create one per story regardless of
                    # the file's columns.
                    story.add_sub_task(
                        JiraSubTask(
                            task_type=name,
                            task_url=None,
                            **common_subtask_fields,
                        )
                    )
                else:
                    # File-driven: only create this subtask when the story
                    # actually has a value in the matching column.
                    col = COL_SUBTASK_URL_START + i
                    if col < self.df.shape[1] and pd.notna(row.iloc[col]):
                        story.add_sub_task(
                            JiraSubTask(
                                task_type=name,
                                task_url=row.iloc[col],
                                **common_subtask_fields,
                            )
                        )

            epic.add_story(story)

        # Validate that we successfully parsed some data
        if rows_with_epic_title == 0:
            raise ValueError(
                f"No valid data found. File should have Epic Title in column {COL_EPIC_TITLE + 1}. "
                f"Check that your file matches the expected Arkansas-style format."
            )

        self.epics = list(epics_dict.values())
        logger.info(
            f"Loaded {len(self.epics)} epics with "
            f"{sum(len(e.stories) for e in self.epics)} stories and "
            f"{sum(e.get_total_sub_tasks() for e in self.epics)} subtasks"
        )
        return self.epics

    def get_summary(self) -> Dict[str, Any]:
        if self.epics is None:
            self.load()
        epic_summaries = []
        for epic in self.epics:
            epic_summaries.append(
                {
                    "epic_title": epic.epic_title,
                    "election_date": epic.election_date,
                    "election_id": epic.election_id,
                    "total_candidates": epic.get_total_candidates(),
                    "total_sub_tasks": epic.get_total_sub_tasks(),
                }
            )

        header_suggestions = []
        for i in range(MAX_SUBTASK_COLUMNS):
            col = COL_SUBTASK_URL_START + i
            if col < self.df.shape[1] and pd.notna(
                self.df.iloc[self.header_row_index, col]
            ):
                val = str(self.df.iloc[self.header_row_index, col]).strip()
                if val:
                    header_suggestions.append(val)

        return {
            "total_epics": len(self.epics),
            "header_suggestions": header_suggestions,
            "epics": epic_summaries,
            "totals": {
                "total_candidates": sum(e["total_candidates"] for e in epic_summaries),
                "total_sub_tasks": sum(e["total_sub_tasks"] for e in epic_summaries),
            },
        }


class JiraApiControl:
    """
    Controller for managing JIRA API operations including creating epics, stories, and subtasks.
    Includes rate limiting and retry logic for robust API usage.
    """

    def __init__(
        self,
        jira_url: str,
        username: str,
        api_token: str,
        project_key: str,
        rate_limit_delay: float = RATE_LIMIT_DELAY,
    ):
        """
        Initialize JIRA API connection.

        Args:
            jira_url: Base URL of the JIRA instance
            username: JIRA username/email
            api_token: JIRA API token
            project_key: JIRA project key (e.g., 'WV')
            rate_limit_delay: Delay between API calls in seconds

        Raises:
            JIRAError: If connection to JIRA fails
        """
        self.jira_url = jira_url
        self.project_key = project_key
        self.rate_limit_delay = rate_limit_delay
        self.last_api_call_time = 0

        try:
            self.jira = JIRA(server=jira_url, basic_auth=(username, api_token))
        except JIRAError as e:
            logger.error(f"Failed to connect to JIRA: {e}")
            raise

        self.created_epics = {}
        self.created_stories = {}
        self.created_subtasks = []
        self.stats = {
            "epics_created": 0,
            "epics_failed": 0,
            "stories_created": 0,
            "stories_failed": 0,
            "subtasks_created": 0,
            "subtasks_failed": 0,
            "api_calls": 0,
            "api_retries": 0,
        }

    def _rate_limit(self):
        """Apply rate limiting between API calls."""
        if self.rate_limit_delay > 0:
            elapsed = time.time() - self.last_api_call_time
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                time.sleep(sleep_time)
        self.last_api_call_time = time.time()
        self.stats["api_calls"] += 1

    @staticmethod
    def _extract_election_label(epic_title: str) -> Optional[str]:
        """
        Extract and sanitize election label from epic title.

        Args:
            epic_title: Epic title string (e.g., "2024 Primary: State Elections")

        Returns:
            Sanitized label or None if pattern not found
        """
        match = re.search(r"(20\d{2}.*?):", epic_title)
        if match:
            label = match.group(1).strip()
            return sanitize_jira_label(label)
        return None

    @retry_on_jira_error()
    def _create_issues_bulk_with_retry(self, chunk: List[Dict]) -> List:
        """
        Internal method to create issues in bulk with retry logic.

        Args:
            chunk: List of issue field dictionaries

        Returns:
            List of JIRA result objects
        """
        self._rate_limit()
        return self.jira.create_issues(field_list=chunk)

    def create_issues_bulk(
        self, issue_list: List[Dict], chunk_size: int = 50
    ) -> List[Optional[str]]:
        """
        Create multiple JIRA issues in bulk, processing in chunks.

        Args:
            issue_list: List of issue field dictionaries
            chunk_size: Number of issues to create per API call

        Returns:
            List of issue keys (or None for failures)
        """
        if not issue_list:
            return []
        all_keys = []
        total_chunks = (len(issue_list) + chunk_size - 1) // chunk_size
        logger.info(
            f"Creating {len(issue_list)} issues in {total_chunks} bulk operations"
        )

        for chunk_num, i in enumerate(range(0, len(issue_list), chunk_size), 1):
            chunk = issue_list[i : i + chunk_size]
            try:
                logger.info(
                    f"Processing bulk chunk {chunk_num}/{total_chunks} ({len(chunk)} issues)"
                )
                results = self._create_issues_bulk_with_retry(chunk)
                JiraApiCounter.objects.create_counter_entry(f"bulk_create_{len(chunk)}")
                for result in results:
                    if "issue" in result and result["issue"]:
                        all_keys.append(result["issue"].key)
                    else:
                        all_keys.append(None)
                logger.info(f"Chunk {chunk_num}/{total_chunks} completed successfully")
            except JIRAError as e:
                logger.error(
                    f"Bulk issue creation failed for chunk {chunk_num}/{total_chunks}: {e}"
                )
                all_keys.extend([None] * len(chunk))
        return all_keys

    @retry_on_jira_error()
    def _create_epic_with_retry(self, fields: Dict) -> Any:
        """
        Internal method to create epic with retry logic.

        Args:
            fields: JIRA fields dictionary

        Returns:
            JIRA issue object
        """
        self._rate_limit()
        return self.jira.create_issue(fields=fields)

    def create_epic(self, epic: JiraEpic) -> Optional[str]:
        """
        Create a JIRA Epic issue.

        Args:
            epic: JiraEpic object containing epic data

        Returns:
            Epic key if successful, None if failed
        """
        try:
            if epic.epic_title in self.created_epics:
                logger.info(f"Epic '{epic.epic_title}' already exists, skipping")
                return self.created_epics[epic.epic_title]

            logger.info(f"Creating epic: {epic.epic_title}")
            election_label = self._extract_election_label(epic.epic_title)
            labels = [
                "POLITICAL_DATA",
                "auto-generated",
                sanitize_jira_label(epic.election_id),
            ]
            if election_label:
                labels.append(election_label)

            fields = {
                "project": {"key": self.project_key},
                "summary": epic.epic_title,
                "description": f"Election: {epic.election_name}\nID: {epic.election_id}\nReport: {epic.election_report_url}",
                "issuetype": {"name": "Epic"},
                "labels": labels,
                JiraCustomFields.EPIC_NAME: epic.epic_title,
                JiraCustomFields.DUE_DATE: epic.due_date.strftime("%Y-%m-%d")
                if epic.due_date
                else None,
                JiraCustomFields.ELECTION_ID: epic.election_id,
                JiraCustomFields.STATE: epic.state,
                JiraCustomFields.COUNTY: epic.county,
            }
            new_issue = self._create_epic_with_retry(fields)
            JiraApiCounter.objects.create_counter_entry("create_epic")
            self.created_epics[epic.epic_title] = new_issue.key
            self.stats["epics_created"] += 1
            logger.info(f"Created epic {new_issue.key}: {epic.epic_title}")
            return new_issue.key
        except JIRAError as e:
            logger.error(f"Failed to create Epic '{epic.epic_title}': {e}")
            self.stats["epics_failed"] += 1
            return None

    def create_story_fields(
        self, story: JiraStory, epic_key: str, election_label: Optional[str]
    ) -> Dict:
        """
        Create field dictionary for a JIRA story.

        Args:
            story: JiraStory object
            epic_key: Parent epic key
            election_label: Sanitized election label

        Returns:
            Dictionary of JIRA fields
        """
        labels = [
            "POLITICAL_DATA",
            "candidate-story",
            sanitize_jira_label(story.jurisdiction),
            sanitize_jira_label(story.state),
        ]
        if election_label:
            labels.append(election_label)
        return {
            "project": {"key": self.project_key},
            "summary": story.story_title,
            "description": f"Candidate: {story.candidate_name}\nOffice: {story.office}\nState: {story.state}",
            "issuetype": {"name": "Story"},
            "labels": labels,
            JiraCustomFields.EPIC_LINK: epic_key,
            JiraCustomFields.CANDIDATE_NAME: story.candidate_name,
            JiraCustomFields.OFFICE: story.office,
            JiraCustomFields.DUE_DATE: story.due_date.strftime("%Y-%m-%d")
            if story.due_date
            else None,
            JiraCustomFields.STATE: story.state,
            JiraCustomFields.COUNTY: story.county,
        }

    def create_subtask_fields(
        self,
        subtask: JiraSubTask,
        parent_key: str,
        candidate_name: str,
        election_label: Optional[str],
    ) -> Dict:
        """
        Create field dictionary for a JIRA subtask.

        Args:
            subtask: JiraSubTask object
            parent_key: Parent story key
            candidate_name: Name of candidate
            election_label: Sanitized election label

        Returns:
            Dictionary of JIRA fields
        """
        labels = ["POLITICAL_DATA", sanitize_jira_label(subtask.task_type)]
        if election_label:
            labels.append(election_label)
        return {
            "project": {"key": self.project_key},
            "summary": f"{subtask.task_type.title()} - {candidate_name}",
            "description": f"URL: {subtask.task_url}" if subtask.task_url else "",
            "issuetype": {"name": "Sub-task"},
            "parent": {"key": parent_key},
            "labels": labels,
            JiraCustomFields.CANDIDATE_NAME: candidate_name,
            JiraCustomFields.DUE_DATE: subtask.due_date.strftime("%Y-%m-%d")
            if subtask.due_date
            else None,
            JiraCustomFields.COUNTY: subtask.county,
        }

    def load_all_epics(self, epics: List[JiraEpic]) -> Dict:
        """
        Load all epics, stories, and subtasks into JIRA.

        Args:
            epics: List of JiraEpic objects to create

        Returns:
            Dictionary with creation statistics including duration
        """
        start_time = time.time()
        logger.info(f"Starting JIRA import of {len(epics)} epics")

        for epic_num, epic in enumerate(epics, 1):
            logger.info(f"Processing epic {epic_num}/{len(epics)}: {epic.epic_title}")
            epic_key = self.create_epic(epic)
            if not epic_key:
                logger.warning(f"Skipping stories for failed epic: {epic.epic_title}")
                continue

            logger.info(f"Creating {len(epic.stories)} stories for epic {epic_key}")
            election_label = self._extract_election_label(epic.epic_title)
            story_dicts = [
                self.create_story_fields(s, epic_key, election_label)
                for s in epic.stories
            ]
            story_keys = self.create_issues_bulk(story_dicts)

            created_stories = [k for k in story_keys if k]
            self.stats["stories_created"] += len(created_stories)
            self.stats["stories_failed"] += len(story_dicts) - len(created_stories)

            subtask_dicts = []
            for story, story_key in zip(epic.stories, story_keys):
                if story_key:
                    for st in story.sub_tasks:
                        subtask_dicts.append(
                            self.create_subtask_fields(
                                st, story_key, story.candidate_name, election_label
                            )
                        )

            if subtask_dicts:
                logger.info(
                    f"Creating {len(subtask_dicts)} subtasks for epic {epic_key}"
                )
                sub_keys = self.create_issues_bulk(subtask_dicts)
                created_subs = [k for k in sub_keys if k]
                self.stats["subtasks_created"] += len(created_subs)
                self.stats["subtasks_failed"] += len(subtask_dicts) - len(created_subs)

        end_time = time.time()
        self.stats["total_duration_ms"] = (end_time - start_time) * 1000

        logger.info(
            f"JIRA import completed in {self.stats['total_duration_ms']:.0f}ms. "
            f"Created: {self.stats['epics_created']} epics, "
            f"{self.stats['stories_created']} stories, "
            f"{self.stats['subtasks_created']} subtasks. "
            f"Failed: {self.stats['epics_failed']} epics, "
            f"{self.stats['stories_failed']} stories, "
            f"{self.stats['subtasks_failed']} subtasks. "
            f"API stats: {self.stats['api_calls']} calls total."
        )

        return self.stats
