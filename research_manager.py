import msvcrt
import os
import sys
import threading
import time
import re
import json
import logging
import curses
import signal
from typing import List, Dict, Set, Optional, Tuple, Union
from dataclasses import dataclass
from queue import Queue
from datetime import datetime
from io import StringIO
from colorama import init, Fore, Style
import select
from threading import Event
from urllib.parse import urlparse
from pathlib import Path

# Initialize colorama for cross-platform color support
if os.name == 'nt':
  import msvcrt
else:
  raise ImportError("This version is Windows-specific. Please use the Unix version for other operating systems.")

# Set up logging
log_directory = 'logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = os.path.join(log_directory, 'research_llm.log')
file_handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.handlers = []
logger.addHandler(file_handler)
logger.propagate = False

# Suppress other loggers
for name in logging.root.manager.loggerDict:
    if name != __name__:
        logging.getLogger(name).disabled = True

@dataclass
class ResearchFocus:
    """Represents a specific area of research focus"""
    area: str
    priority: int
    source_query: str = ""
    timestamp: str = ""
    search_queries: List[str] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.search_queries is None:
            self.search_queries = []

@dataclass
class AnalysisResult:
    """Contains the complete analysis result"""
    original_question: str
    focus_areas: List[ResearchFocus]
    raw_response: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class StrategicAnalysisParser:
    def __init__(self, llm=None):
        self.llm = llm
        self.logger = logging.getLogger(__name__)
        # Simplify patterns to match exactly what we expect
        self.patterns = {
            'priority': [
                r"Priority:\s*(\d+)",  # Match exactly what's in our prompt
            ]
        }

    def strategic_analysis(self, original_query: str) -> Optional[AnalysisResult]:
        """Generate and process research areas with retries until success"""
        max_retries = 3
        try:
            self.logger.info("Starting strategic analysis...")
            prompt = f"""
You must select exactly 5 areas to investigate in order to explore and gather information to answer the research question:
"{original_query}"

You MUST provide exactly 5 areas numbered 1-5. Each must have a priority, YOU MUST ensure that you only assign one priority per area.
Assign priority based on the likelihood of a focus area being investigated to provide information that directly will allow you to respond to "{original_query}" with 5 being most likely and 1 being least.
Follow this EXACT format without any deviations or additional text:

1. [First research topic]
Priority: [number 1-5]

2. [Second research topic]
Priority: [number 1-5]

3. [Third research topic]
Priority: [number 1-5]

4. [Fourth research topic]
Priority: [number 1-5]

5. [Fifth research topic]
Priority: [number 1-5]
"""
            for attempt in range(max_retries):
                response = self.llm.generate(prompt, max_tokens=1000)
                focus_areas = self._extract_research_areas(response)

                if focus_areas:  # If we got any valid areas
                    # Sort by priority (highest first)
                    focus_areas.sort(key=lambda x: x.priority, reverse=True)

                    return AnalysisResult(
                        original_question=original_query,
                        focus_areas=focus_areas,
                        raw_response=response,
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                else:
                    self.logger.warning(f"Attempt {attempt + 1}: No valid areas generated, retrying...")
                    print(f"\nRetrying research area generation (Attempt {attempt + 1}/{max_retries})...")

            # If all retries failed, try one final time with a stronger prompt
            prompt += "\n\nIMPORTANT: You MUST provide exactly 5 research areas with priorities. This is crucial."
            response = self.llm.generate(prompt, max_tokens=1000)
            focus_areas = self._extract_research_areas(response)

            if focus_areas:
                focus_areas.sort(key=lambda x: x.priority, reverse=True)
                return AnalysisResult(
                    original_question=original_query,
                    focus_areas=focus_areas,
                    raw_response=response,
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )

            self.logger.error("Failed to generate any valid research areas after all attempts")
            return None

        except Exception as e:
            self.logger.error(f"Error in strategic analysis: {str(e)}")
            return None

    def _extract_research_areas(self, text: str) -> List[ResearchFocus]:
        """Extract research areas with enhanced parsing to handle priorities in various formats."""
        areas = []
        lines = text.strip().split('\n')

        current_area = None
        current_priority = None

        for i in range(len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            # Check for numbered items (e.g., '1. Area Name')
            number_match = re.match(r'^(\d+)\.\s*(.*)', line)
            if number_match:
                # If we have a previous area, add it to our list
                if current_area is not None:
                    areas.append(ResearchFocus(
                        area=current_area.strip(' -:'),
                        priority=current_priority or 3,
                    ))
                # Start a new area
                area_line = number_match.group(2)

                # Search for 'priority' followed by a number, anywhere in the area_line
                priority_inline_match = re.search(
                    r'(?i)\bpriority\b\s*(?:[:=]?\s*)?(\d+)', area_line)
                if priority_inline_match:
                    # Extract and set the priority
                    try:
                        current_priority = int(priority_inline_match.group(1))
                        current_priority = max(1, min(5, current_priority))
                    except ValueError:
                        current_priority = 3  # Default priority if parsing fails
                    # Remove the 'priority' portion from area_line
                    area_line = area_line[:priority_inline_match.start()] + area_line[priority_inline_match.end():]
                    area_line = area_line.strip(' -:')
                else:
                    current_priority = None  # Priority might be on the next line

                current_area = area_line.strip()

            elif re.match(r'(?i)^priority\s*(?:[:=]?\s*)?(\d+)', line):
                # Extract priority from the line following the area
                try:
                    priority_match = re.match(r'(?i)^priority\s*(?:[:=]?\s*)?(\d+)', line)
                    current_priority = int(priority_match.group(1))
                    current_priority = max(1, min(5, current_priority))
                except (ValueError, IndexError):
                    current_priority = 3  # Default priority if parsing fails

            # Check if this is the last line or the next line is a new area
            next_line_is_new_area = (i + 1 < len(lines)) and re.match(r'^\d+\.', lines[i + 1].strip())
            if next_line_is_new_area or i + 1 == len(lines):
                if current_area is not None:
                    # Append the current area and priority to the list
                    areas.append(ResearchFocus(
                        area=current_area.strip(' -:'),
                        priority=current_priority or 3,
                    ))
                    current_area = None
                    current_priority = None

        return areas

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'(\d+\))', r'\1.', text)
        text = re.sub(r'(?i)priority:', 'P:', text)
        return text.strip()

    def _add_area(self, areas: List[ResearchFocus], area: str, priority: Optional[int]):
        """Add area with basic validation"""
        if not area or len(area.split()) < 3:  # Basic validation
            return

        areas.append(ResearchFocus(
            area=area,
            priority=priority or 3,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            search_queries=[]
        ))

    def _normalize_focus_areas(self, areas: List[ResearchFocus]) -> List[ResearchFocus]:
        """Normalize and prepare final list of areas"""
        if not areas:
            return []

        # Sort by priority
        areas.sort(key=lambda x: x.priority, reverse=True)

        # Ensure priorities are properly spread
        for i, area in enumerate(areas):
            area.priority = max(1, min(5, area.priority))

        return areas[:5]

    def format_analysis_result(self, result: AnalysisResult) -> str:
        """Format the results for display"""
        if not result:
            return "No valid analysis result generated."

        formatted = [
            f"\nResearch Areas for: {result.original_question}\n"
        ]

        for i, focus in enumerate(result.focus_areas, 1):
            formatted.extend([
                f"\n{i}. {focus.area}",
                f"   Priority: {focus.priority}"
            ])

        return "\n".join(formatted)

class OutputRedirector:
    """Redirects stdout and stderr to a string buffer"""
    def __init__(self, stream=None):
        self.stream = stream or StringIO()
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def __enter__(self):
        sys.stdout = self.stream
        sys.stderr = self.stream
        return self.stream

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr

class TerminalUI:
    """Manages terminal display with fixed input area at bottom"""
    def __init__(self):
        self.stdscr = None
        self.input_win = None
        self.output_win = None
        self.status_win = None
        self.max_y = 0
        self.max_x = 0
        self.input_buffer = ""
        self.is_setup = False
        self.old_terminal_settings = None
        self.should_terminate = Event()
        self.shutdown_event = Event()
        self.research_thread = None
        self.last_display_height = 0  # Track display height for corruption fix


    def setup(self):
        """Initialize the terminal UI"""
        if self.is_setup:
            return

        # Save terminal settings
        if not os.name == 'nt':  # Unix-like systems
            self.old_terminal_settings = termios.tcgetattr(sys.stdin.fileno())

        self.stdscr = curses.initscr()
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)

        # Enable only scroll wheel events, not all mouse events
        # curses.mousemask(curses.BUTTON4_PRESSED | curses.BUTTON5_PRESSED)

        # Remove this line that was causing the spam
        # print('\033[?1003h')  # We don't want mouse movement events

        # Get terminal dimensions
        self.max_y, self.max_x = self.stdscr.getmaxyx()

        # Create windows
        self.output_win = curses.newwin(self.max_y - 4, self.max_x, 0, 0)
        self.status_win = curses.newwin(1, self.max_x, self.max_y - 4, 0)
        self.input_win = curses.newwin(3, self.max_x, self.max_y - 3, 0)

        # Setup colors
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        # Enable scrolling
        self.output_win.scrollok(True)
        self.output_win.idlok(True)
        self.input_win.scrollok(True)

        self.is_setup = True
        self._refresh_input_prompt()

    def cleanup(self):
        """Public cleanup method with enhanced terminal restoration"""
        if not self.is_setup:
            return
        try:
            # Ensure all windows are properly closed
            for win in [self.input_win, self.output_win, self.status_win]:
                if win:
                    win.clear()
                    win.refresh()

            # Restore terminal state
            if self.stdscr:
                self.stdscr.keypad(False)
                curses.nocbreak()
                curses.echo()
                curses.endwin()

            # Restore original terminal settings
            if self.old_terminal_settings and not os.name == 'nt':
                termios.tcsetattr(
                    sys.stdin.fileno(),
                    termios.TCSADRAIN,
                    self.old_terminal_settings
                )
        except Exception as e:
            logger.error(f"Error during terminal cleanup: {str(e)}")
        finally:
            self.is_setup = False
            self.stdscr = None
            self.input_win = None
            self.output_win = None
            self.status_win = None

    def _cleanup(self):
        """Enhanced resource cleanup with better process handling"""
        self.should_terminate.set()

        # Handle research thread with improved termination
        if self.research_thread and self.research_thread.is_alive():
            try:
                self.research_thread.join(timeout=1.0)
                if self.research_thread.is_alive():
                    import ctypes
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(
                        ctypes.c_long(self.research_thread.ident),
                        ctypes.py_object(SystemExit))
                    time.sleep(0.1)  # Give thread time to exit
                    if self.research_thread.is_alive():  # Double-check
                        ctypes.pythonapi.PyThreadState_SetAsyncExc(
                            ctypes.c_long(self.research_thread.ident),
                            0)  # Reset exception
            except Exception as e:
                logger.error(f"Error terminating research thread: {str(e)}")

        # Clean up LLM with improved error handling
        if hasattr(self, 'llm') and hasattr(self.llm, '_cleanup'):
            try:
                self.llm.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up LLM: {str(e)}")

        # Ensure terminal is restored
        try:
            curses.endwin()
        except:
            pass

        # Final cleanup of UI
        self.cleanup()

    def _refresh_input_prompt(self, prompt="Enter command: "):
        """Refresh the fixed input prompt at bottom with display fix"""
        if not self.is_setup:
            return

        try:
            # Clear the entire input window first
            self.input_win.clear()

            # Calculate proper cursor position
            cursor_y = 0
            cursor_x = len(prompt) + len(self.input_buffer)

            # Add the prompt and buffer
            self.input_win.addstr(0, 0, f"{prompt}{self.input_buffer}", curses.color_pair(1))

            # Position cursor correctly
            try:
                self.input_win.move(cursor_y, cursor_x)
            except curses.error:
                pass  # Ignore if cursor would be off-screen

            self.input_win.refresh()
        except curses.error:
            pass

    def update_output(self, text: str):
        """Update output window with display corruption fix"""
        if not self.is_setup:
            return

        try:
            # Clean ANSI escape codes
            clean_text = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)

            # Store current position
            current_y, _ = self.output_win.getyx()

            # Clear any potential corruption
            if current_y > self.last_display_height:
                self.output_win.clear()

            self.output_win.addstr(clean_text + "\n", curses.color_pair(2))
            new_y, _ = self.output_win.getyx()
            self.last_display_height = new_y

            self.output_win.refresh()
            self._refresh_input_prompt()
        except curses.error:
            pass

    def update_status(self, text: str):
        """Update the status line above input area"""
        if not self.is_setup:
            return

        try:
            self.status_win.clear()
            self.status_win.addstr(0, 0, text, curses.color_pair(3))
            self.status_win.refresh()
            self._refresh_input_prompt()  # Ensure prompt is refreshed after status update
        except curses.error:
            pass

    def get_input(self, prompt: Optional[str] = None) -> Optional[str]:
        """Windows-compatible input handling"""
        try:
            if prompt:
                self.update_status(prompt)
            if not self.is_setup:
                self.setup()
            self.input_buffer = ""
            self._refresh_input_prompt()

            while True:
                if self.should_terminate.is_set():
                    return None

                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    
                    if ch == b'\x04':  # Ctrl+D
                        result = self.input_buffer.strip()
                        self.input_buffer = ""
                        if not result:
                            self.cleanup()
                            return "@quit"
                        return result

                    elif ch == b'\x03':  # Ctrl+C
                        self.should_terminate.set()
                        self.cleanup()
                        return "@quit"

                    elif ch == b'\r':  # Enter
                        result = self.input_buffer.strip()
                        if result:
                            self.input_buffer = ""
                            return result
                        continue

                    elif ch == b'\x08':  # Backspace
                        if self.input_buffer:
                            self.input_buffer = self.input_buffer[:-1]
                            self._refresh_input_prompt()

                    elif 32 <= ord(ch[0]) <= 126:  # Printable characters
                        self.input_buffer += ch.decode('utf-8')
                        self._refresh_input_prompt()

        except Exception as e:
            logger.error(f"Error in get_input: {str(e)}")
            self.should_terminate.set()
            self.cleanup()
        return "@quit"

    def force_exit(self):
        """Force immediate exit with enhanced cleanup"""
        try:
            self.should_terminate.set()
            self.shutdown_event.set()
            self._cleanup()  # Call private cleanup first
            self.cleanup()   # Then public cleanup
            curses.endwin()  # Final attempt to restore terminal
        except:
            pass
        finally:
            os._exit(0)  # Ensure exit

class NonBlockingInput:
  """Windows-compatible non-blocking input"""
  def __init__(self):
      pass

  def __enter__(self):
      return self

  def __exit__(self, type, value, traceback):
      pass

  def check_input(self, timeout=0.1):
      """Check for input without blocking"""
      if msvcrt.kbhit():
          return msvcrt.getch().decode('utf-8')
      return None

class ResearchManager:
    """Manages the research process including analysis, search, and documentation"""
    def __init__(self, llm_wrapper, parser, search_engine, max_searches_per_cycle: int = 5):
        self.llm = llm_wrapper
        self.parser = parser
        self.search_engine = search_engine
        self.max_searches = max_searches_per_cycle
        self.should_terminate = threading.Event()
        self.shutdown_event = Event()
        self.research_started = threading.Event()
        self.research_thread = None
        self.thinking = False
        self.stop_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at'
        }

        # State tracking
        self.searched_urls: Set[str] = set()
        self.current_focus: Optional[ResearchFocus] = None
        self.original_query: str = ""
        self.focus_areas: List[ResearchFocus] = []
        self.is_running = False

        # New conversation mode attributes
        self.research_complete = False
        self.research_summary = ""
        self.conversation_active = False
        self.research_content = ""

        # Initialize document paths
        self.document_path = None
        self.session_files = []

        # Initialize UI and parser
        self.ui = TerminalUI()
        self.strategic_parser = StrategicAnalysisParser(llm=self.llm)

        # Initialize new flags for pausing and assessment
        self.research_paused = False
        self.awaiting_user_decision = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        self.shutdown_event.set()
        self.should_terminate.set()
        self._cleanup()

    def print_thinking(self):
        """Display thinking indicator to user"""
        self.ui.update_output("🧠 Thinking...")

    @staticmethod
    def get_initial_input() -> str:
        """Get the initial research query from user"""
        print(f"{Fore.GREEN}📝 Enter your message (Press CTRL+D to submit):{Style.RESET_ALL}")
        lines = []
        try:
            while True:
                line = input()
                if line:  # Only add non-empty lines
                    lines.append(line)
                if not line:  # Empty line (just Enter pressed)
                    break
        except EOFError:  # Ctrl+D pressed
            pass
        except KeyboardInterrupt:  # Ctrl+C pressed
            print("\nOperation cancelled")
            sys.exit(0)

        return " ".join(lines).strip()

    def formulate_search_queries(self, focus_area: ResearchFocus) -> List[str]:
        """Generate search queries for a focus area"""
        try:
            self.print_thinking()

            prompt = f"""
In order to research this query/topic:

Context: {self.original_query}

Base a search query to investigate the following research focus, which is related to the original query/topic:

Area: {focus_area.area}

Create a search query that will yield specific, search results thare are directly relevant to your focus area.
Format your response EXACTLY like this:

Search query: [Your 2-5 word query]
Time range: [d/w/m/y/none]

Do not provide any additional information or explanation, note that the time range allows you to see results within a time range (d is within the last day, w is within the last week, m is within the last month, y is within the last year, and none is results from anytime, only select one, using only the corresponding letter for whichever of these options you select as indicated in the response format) use your judgement as many searches will not require a time range and some may depending on what the research focus is.
"""
            response_text = self.llm.generate(prompt, max_tokens=50, stop=None)
            query, time_range = self.parse_query_response(response_text)

            if not query:
                self.ui.update_output(f"{Fore.RED}Error: Empty search query. Using focus area as query...{Style.RESET_ALL}")
                return [focus_area.area]

            self.ui.update_output(f"{Fore.YELLOW}Original focus: {focus_area.area}{Style.RESET_ALL}")
            self.ui.update_output(f"{Fore.YELLOW}Formulated query: {query}{Style.RESET_ALL}")
            self.ui.update_output(f"{Fore.YELLOW}Time range: {time_range}{Style.RESET_ALL}")

            return [query]

        except Exception as e:
            logger.error(f"Error formulating query: {str(e)}")
            return [focus_area.area]

    def parse_search_query(self, query_response: str) -> Dict[str, str]:
        """Parse search query formulation response with improved time range detection"""
        try:
            lines = query_response.strip().split('\n')
            result = {
                'query': '',
                'time_range': 'none'
            }

            # First try to find standard format
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()

                    if 'query' in key:
                        result['query'] = self._clean_query(value)
                    elif ('time' in key or 'range' in key) and value.strip().lower() in ['d', 'w', 'm', 'y', 'none']:
                        result['time_range'] = value.strip().lower()

            # If no time range found, look for individual characters
            if result['time_range'] == 'none':
                # Get all text except the query itself
                full_text = query_response.lower()
                if result['query']:
                    full_text = full_text.replace(result['query'].lower(), '')

                # Look for isolated d, w, m, or y characters
                time_chars = set()
                for char in ['d', 'w', 'm', 'y']:
                    # Check if char exists by itself (not part of another word)
                    matches = re.finditer(r'\b' + char + r'\b', full_text)
                    for match in matches:
                        # Verify it's not part of a word
                        start, end = match.span()
                        if (start == 0 or not full_text[start-1].isalpha()) and \
                           (end == len(full_text) or not full_text[end].isalpha()):
                            time_chars.add(char)

                # If exactly one time char found, use it
                if len(time_chars) == 1:
                    result['time_range'] = time_chars.pop()

            return result
        except Exception as e:
            logger.error(f"Error parsing search query: {str(e)}")
            return {'query': '', 'time_range': 'none'}

    def _cleanup(self):
        """Enhanced cleanup to handle conversation mode"""
        self.conversation_active = False
        self.should_terminate.set()

        if self.research_thread and self.research_thread.is_alive():
            try:
                self.research_thread.join(timeout=1.0)
                if self.research_thread.is_alive():
                    import ctypes
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(
                        ctypes.c_long(self.research_thread.ident),
                        ctypes.py_object(SystemExit)
                    )
            except Exception as e:
                logger.error(f"Error terminating research thread: {str(e)}")

        if hasattr(self.llm, 'cleanup'):
            try:
                self.llm.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up LLM: {str(e)}")

        if hasattr(self.ui, 'cleanup'):
            self.ui.cleanup()

    def _initialize_document(self):
        """Initialize research session document"""
        try:
            # Get all existing research session files
            self.session_files = []
            for file in os.listdir():
                if file.startswith("research_session_") and file.endswith(".txt"):
                    try:
                        num = int(file.split("_")[2].split(".")[0])
                        self.session_files.append(num)
                    except ValueError:
                        continue

            # Determine next session number
            next_session = 1 if not self.session_files else max(self.session_files) + 1
            self.document_path = f"research_session_{next_session}.txt"

            # Initialize the new document
            with open(self.document_path, 'w', encoding='utf-8') as f:
                f.write(f"Research Session {next_session}\n")
                f.write(f"Topic: {self.original_query}\n")
                f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*80 + "\n\n")
                f.flush()

        except Exception as e:
            logger.error(f"Error initializing document: {str(e)}")
            self.document_path = "research_findings.txt"
            with open(self.document_path, 'w', encoding='utf-8') as f:
                f.write("Research Findings:\n\n")
                f.flush()

    def add_to_document(self, content: str, source_url: str, focus_area: str):
        """Add research findings to current session document"""
        try:
            with open(self.document_path, 'a', encoding='utf-8') as f:
                if source_url not in self.searched_urls:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"Research Focus: {focus_area}\n")
                    f.write(f"Source: {source_url}\n")
                    f.write(f"Content:\n{content}\n")
                    f.write(f"{'='*80}\n")
                    f.flush()
                    self.searched_urls.add(source_url)
                    self.ui.update_output(f"Added content from: {source_url}")
        except Exception as e:
            logger.error(f"Error adding to document: {str(e)}")
            self.ui.update_output(f"Error saving content: {str(e)}")

    def _process_search_results(self, results: Dict[str, str], focus_area: str):
        """Process and store search results"""
        if not results:
            return

        for url, content in results.items():
            if url not in self.searched_urls:
                self.add_to_document(content, url, focus_area)

    def _research_loop(self):
        """Main research loop with comprehensive functionality"""
        self.is_running = True
        try:
            self.research_started.set()

            while not self.should_terminate.is_set() and not self.shutdown_event.is_set():
                # Check if research is paused
                if self.research_paused:
                    time.sleep(1)
                    continue

                self.ui.update_output("\nAnalyzing research progress...")

                # Generate focus areas
                self.ui.update_output("\nGenerating research focus areas...")
                analysis_result = self.strategic_parser.strategic_analysis(self.original_query)

                if not analysis_result:
                    self.ui.update_output("\nFailed to generate analysis result. Retrying...")
                    continue

                focus_areas = analysis_result.focus_areas
                if not focus_areas:
                    self.ui.update_output("\nNo valid focus areas generated. Retrying...")
                    continue

                self.ui.update_output(f"\nGenerated {len(focus_areas)} research areas:")
                for i, focus in enumerate(focus_areas, 1):
                    self.ui.update_output(f"\nArea {i}: {focus.area}")
                    self.ui.update_output(f"Priority: {focus.priority}")

                # Process each focus area in priority order
                for focus_area in focus_areas:
                    if self.should_terminate.is_set():
                        break

                    # Check if research is paused
                    while self.research_paused and not self.should_terminate.is_set():
                        time.sleep(1)

                    if self.should_terminate.is_set():
                        break

                    self.current_focus = focus_area
                    self.ui.update_output(f"\nInvestigating: {focus_area.area}")

                    queries = self.formulate_search_queries(focus_area)
                    if not queries:
                        continue

                    for query in queries:
                        if self.should_terminate.is_set():
                            break

                        # Check if research is paused
                        while self.research_paused and not self.should_terminate.is_set():
                            time.sleep(1)

                        if self.should_terminate.is_set():
                            break

                        try:
                            self.ui.update_output(f"\nSearching: {query}")
                            results = self.search_engine.perform_search(query, time_range='none')

                            if results:
                                # self.search_engine.display_search_results(results)
                                selected_urls = self.search_engine.select_relevant_pages(results, query)

                                if selected_urls:
                                    self.ui.update_output("\n⚙️ Scraping selected pages...")
                                    scraped_content = self.search_engine.scrape_content(selected_urls)
                                    if scraped_content:
                                        for url, content in scraped_content.items():
                                            if url not in self.searched_urls:
                                                self.add_to_document(content, url, focus_area.area)

                        except Exception as e:
                            logger.error(f"Error in search: {str(e)}")
                            self.ui.update_output(f"Error during search: {str(e)}")

                    if self.check_document_size():
                        self.ui.update_output("\nDocument size limit reached. Finalizing research.")
                        return

                # After processing all areas, cycle back to generate new ones
                self.ui.update_output("\nAll current focus areas investigated. Generating new areas...")

        except Exception as e:
            logger.error(f"Error in research loop: {str(e)}")
            self.ui.update_output(f"Error in research process: {str(e)}")
        finally:
            self.is_running = False

    def start_research(self, topic: str):
        """Start research with new session document"""
        try:
            self.ui.setup()
            self.original_query = topic
            self._initialize_document()

            self.ui.update_output(f"Starting research on: {topic}")
            self.ui.update_output(f"Session document: {self.document_path}")
            self.ui.update_output("\nCommands available during research:")
            self.ui.update_output("'s' = Show status")
            self.ui.update_output("'f' = Show current focus")
            self.ui.update_output("'p' = Pause and assess the research progress")  # New command
            self.ui.update_output("'q' = Quit research\n")

            # Reset events
            self.should_terminate.clear()
            self.research_started.clear()
            self.research_paused = False  # Ensure research is not paused at the start
            self.awaiting_user_decision = False

            # Start research thread
            self.research_thread = threading.Thread(target=self._research_loop, daemon=True)
            self.research_thread.start()

            # Wait for research to actually start
            if not self.research_started.wait(timeout=10):
                self.ui.update_output("Error: Research failed to start within timeout period")
                self.should_terminate.set()
                return

            while not self.should_terminate.is_set():
                cmd = self.ui.get_input("Enter command: ")
                if cmd is None or self.shutdown_event.is_set():
                    if self.should_terminate.is_set() and not self.research_complete:
                        self.ui.update_output("\nGenerating research summary... please wait...")
                        summary = self.terminate_research()
                        self.ui.update_output("\nFinal Research Summary:")
                        self.ui.update_output(summary)
                    break
                if cmd:
                    self._handle_command(cmd)

        except Exception as e:
            logger.error(f"Error in research process: {str(e)}")
        finally:
            self._cleanup()

    def check_document_size(self) -> bool:
        """Check if document size is approaching context limit"""
        try:
            with open(self.document_path, 'r', encoding='utf-8') as f:
                content = f.read()
            estimated_tokens = len(content.split()) * 1.3
            max_tokens = self.llm.llm_config.get('n_ctx', 2048)
            current_ratio = estimated_tokens / max_tokens

            if current_ratio > 0.8:
                logger.warning(f"Document size at {current_ratio*100:.1f}% of context limit")
                self.ui.update_output(f"Warning: Document size at {current_ratio*100:.1f}% of context limit")

            return current_ratio > 0.9
        except Exception as e:
            logger.error(f"Error checking document size: {str(e)}")
            return True

    def _handle_command(self, cmd: str):
        """Handle user commands during research"""
        if cmd.lower() == 's':
            self.ui.update_output(self.get_progress())
        elif cmd.lower() == 'f':
            if self.current_focus:
                self.ui.update_output("\nCurrent Focus:")
                self.ui.update_output(f"Area: {self.current_focus.area}")
                self.ui.update_output(f"Priority: {self.current_focus.priority}")
            else:
                self.ui.update_output("\nNo current focus area")
        elif cmd.lower() == 'p':
            self.pause_and_assess()
        elif cmd.lower() == 'q':
            self.ui.update_output("\nInitiating research termination...")
            self.should_terminate.set()
            self.ui.update_output("\nGenerating research summary... please wait...")
            summary = self.terminate_research()
            self.ui.update_output("\nFinal Research Summary:")
            self.ui.update_output(summary)

    def pause_and_assess(self):
        """Pause the research and assess if the collected content is sufficient."""
        try:
            # Pause the research thread
            self.ui.update_output("\nPausing research for assessment...")
            self.research_paused = True

            # Start progress indicator in a separate thread
            self.summary_ready = False
            indicator_thread = threading.Thread(
                target=self.show_progress_indicator,
                args=("Assessing the researched information...",)
            )
            indicator_thread.daemon = True
            indicator_thread.start()

            # Read the current research content
            if not os.path.exists(self.document_path):
                self.summary_ready = True
                indicator_thread.join()
                self.ui.update_output("No research data found to assess.")
                self.research_paused = False
                return

            with open(self.document_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                self.summary_ready = True
                indicator_thread.join()
                self.ui.update_output("No research data was collected to assess.")
                self.research_paused = False
                return

            # Prepare the prompt for the AI assessment
            assessment_prompt = f"""
Based on the following research content, please assess whether the original query "{self.original_query}" can be answered sufficiently with the collected information.

Research Content:
{content}

Instructions:
1. If the research content provides enough information to answer the original query in detail, respond with: "The research is sufficient to answer the query."
2. If not, respond with: "The research is insufficient and it would be advisable to continue gathering information."
3. Do not provide any additional information or details.

Assessment:
"""

            # Generate the assessment
            assessment = self.llm.generate(assessment_prompt, max_tokens=200)

            # Stop the progress indicator
            self.summary_ready = True
            indicator_thread.join()

            # Display the assessment
            self.ui.update_output("\nAssessment Result:")
            self.ui.update_output(assessment.strip())

            # Provide user with options to continue or quit
            self.ui.update_output("\nEnter 'c' to continue the research or 'q' to terminate and generate the summary.")
            self.awaiting_user_decision = True  # Flag to indicate we are waiting for user's decision

            while self.awaiting_user_decision:
                cmd = self.ui.get_input("Enter command ('c' to continue, 'q' to quit): ")
                if cmd is None:
                    continue  # Ignore invalid inputs
                cmd = cmd.strip().lower()
                if cmd == 'c':
                    self.ui.update_output("\nResuming research...")
                    self.research_paused = False
                    self.awaiting_user_decision = False
                elif cmd == 'q':
                    self.ui.update_output("\nTerminating research and generating summary...")
                    self.awaiting_user_decision = False
                    self.should_terminate.set()
                    summary = self.terminate_research()
                    self.ui.update_output("\nFinal Research Summary:")
                    self.ui.update_output(summary)
                    break
                else:
                    self.ui.update_output("Invalid command. Please enter 'c' to continue or 'q' to quit.")

        except Exception as e:
            logger.error(f"Error during pause and assess: {str(e)}")
            self.ui.update_output(f"Error during assessment: {str(e)}")
            self.research_paused = False
        finally:
            self.summary_ready = True  # Ensure the indicator thread can exit

    def get_progress(self) -> str:
        """Get current research progress"""
        return f"""
Research Progress:
- Original Query: {self.original_query}
- Sources analyzed: {len(self.searched_urls)}
- Status: {'Active' if self.is_running else 'Stopped'}
- Current focus: {self.current_focus.area if self.current_focus else 'Initializing'}
"""

    def is_active(self) -> bool:
        """Check if research is currently active"""
        return self.is_running and self.research_thread and self.research_thread.is_alive()

    def terminate_research(self) -> str:
        """Terminate research and return to main terminal"""
        try:
            print("Initiating research termination...")
            sys.stdout.flush()

            # Start progress indicator in a separate thread immediately
            indicator_thread = threading.Thread(target=self.show_progress_indicator)
            indicator_thread.daemon = True
            indicator_thread.start()

            if not os.path.exists(self.document_path):
                self.summary_ready = True
                indicator_thread.join(timeout=1.0)
                self._cleanup()
                return "No research data found to summarize."

            with open(self.document_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self.research_content = content  # Store for conversation mode

            if not content or content == "Research Findings:\n\n":
                self.summary_ready = True
                indicator_thread.join(timeout=1.0)
                self._cleanup()
                return "No research data was collected to summarize."

            try:
                # Generate summary using LLM
                summary_prompt = f"""
                Analyze the following content to provide a comprehensive research summary and a response to the user's original query "{self.original_query}" ensuring that you conclusively answer the query in detail:

                Research Content:
                {content}

                Important Instructions:
                > Summarize the research findings that are relevant to the Original topic/question: "{self.original_query}"
                > Ensure that in your summary you directly answer the original question/topic conclusively to the best of your ability in detail.
                > Read the original topic/question again "{self.original_query}" and abide by any additional instructions that it contains, exactly as instructed in your summary otherwise provide it normally should it not have any specific instructions

                Summary:
                """

                summary = self.llm.generate(summary_prompt, max_tokens=4000)

                # Signal that summary is complete to stop the progress indicator
                self.summary_ready = True
                indicator_thread.join(timeout=1.0)

                # Store summary and mark research as complete
                self.research_summary = summary
                self.research_complete = True

                # Format summary
                formatted_summary = f"""
                {'='*80}
                RESEARCH SUMMARY
                {'='*80}

                Original Query: {self.original_query}
                Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

                {summary}

                {'='*80}
                End of Summary
                {'='*80}
                """

                # Write to document
                with open(self.document_path, 'a', encoding='utf-8') as f:
                    f.write("\n\n" + formatted_summary)

                # Clean up research UI
                if hasattr(self, 'ui') and self.ui:
                    self.ui.cleanup()

                return formatted_summary

            except Exception as e:
                self.summary_ready = True
                indicator_thread.join(timeout=1.0)
                raise e

        except Exception as e:
            error_msg = f"Error generating summary: {str(e)}"
            logger.error(error_msg)
            return error_msg

        finally:
            # Clean up research UI
            self._cleanup_research_ui()

    def show_progress_indicator(self, message="Generating summary, please wait..."):
        """Show a rotating progress indicator until the summary is ready."""
        symbols = ['|', '/', '-', '\\']
        idx = 0
        self.summary_ready = False  # Track whether the summary is complete
        while not self.summary_ready:
            sys.stdout.write(f"\r{message} {symbols[idx]}")
            sys.stdout.flush()
            idx = (idx + 1) % len(symbols)
            time.sleep(0.2)  # Adjust the speed of the rotation if needed
        sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")  # Clear the line when done

    def _cleanup_research_ui(self):
        """Clean up just the research UI components"""
        if hasattr(self, 'ui') and self.ui:
            self.ui.cleanup()

    def show_thinking_indicator(self, message: str, stop_flag_name: str):
        """Show a rotating thinking indicator with custom message"""
        symbols = ['|', '/', '-', '\\']
        idx = 0
        while getattr(self, stop_flag_name):  # Use dynamic attribute lookup
            sys.stdout.write(f"\r{message} {symbols[idx]}")
            sys.stdout.flush()
            idx = (idx + 1) % len(symbols)
            time.sleep(0.2)
        sys.stdout.write("\r" + " " * (len(message) + 2) + "\r")  # Clear the line when done

    def start_conversation_mode(self):
        """Start interactive conversation mode with CTRL+D input handling and thinking indicator"""
        self.conversation_active = True
        self.thinking = False

        # Print header with clear instructions
        print("\n" + "="*80)
        print(Fore.CYAN + "Research Conversation Mode" + Style.RESET_ALL)
        print("="*80)
        print(Fore.YELLOW + "\nInstructions:")
        print("- Type your question and press CTRL+D to submit")
        print("- Type 'quit' and press CTRL+D to exit")
        print("- Your messages appear in green")
        print("- AI responses appear in cyan" + Style.RESET_ALL + "\n")

        while self.conversation_active:
            try:
                # Show prompt with user input in green
                print(Fore.GREEN + "Your question (Press CTRL+D to submit):" + Style.RESET_ALL)
                user_input = self.get_multiline_conversation_input()

                # Handle exit commands
                if not user_input or user_input.lower() in ['quit', 'exit', 'q']:
                    print(Fore.YELLOW + "\nExiting conversation mode..." + Style.RESET_ALL)
                    self.conversation_active = False
                    break

                # Skip empty input
                if not user_input.strip():
                    continue

                # Echo the submitted question for clarity
                print(Fore.GREEN + "Submitted question:" + Style.RESET_ALL)
                print(Fore.GREEN + user_input + Style.RESET_ALL + "\n")

                # Start thinking indicator in a separate thread
                self.thinking = True  # Set flag before starting thread
                thinking_thread = threading.Thread(
                    target=self.show_thinking_indicator,
                    args=("Thinking...", "thinking")
                )
                thinking_thread.daemon = True
                thinking_thread.start()

                try:
                    # Generate response
                    response = self._generate_conversation_response(user_input)

                    # Stop thinking indicator
                    self.thinking = False
                    thinking_thread.join()

                    # Display response in cyan
                    print(Fore.CYAN + "AI Response:" + Style.RESET_ALL)
                    print(f"{Fore.CYAN}{response}{Style.RESET_ALL}\n")
                    print("-" * 80 + "\n")  # Separator between QA pairs

                except Exception as e:
                    self.thinking = False  # Ensure thinking indicator stops
                    thinking_thread.join()
                    raise e

            except KeyboardInterrupt:
                self.thinking = False  # Ensure thinking indicator stops
                print(Fore.YELLOW + "\nOperation cancelled. Submit 'quit' to exit." + Style.RESET_ALL)
            except Exception as e:
                logger.error(f"Error in conversation mode: {str(e)}")
                print(Fore.RED + f"Error processing question: {str(e)}" + Style.RESET_ALL)

    def _generate_conversation_response(self, user_query: str) -> str:
        """Generate contextual responses with improved context handling"""
        try:
            # Add debug logging to verify content
            logger.info(f"Research summary length: {len(self.research_summary) if self.research_summary else 0}")
            logger.info(f"Research content length: {len(self.research_content) if self.research_content else 0}")

            # First verify we have content
            if not self.research_content and not self.research_summary:
                # Try to reload from file if available
                try:
                    if os.path.exists(self.document_path):
                        with open(self.document_path, 'r', encoding='utf-8') as f:
                            self.research_content = f.read().strip()
                except Exception as e:
                    logger.error(f"Failed to reload research content: {str(e)}")

            # Prepare context, ensuring we have content
            context = f"""
Research Content:
{self.research_content}

Research Summary:
{self.research_summary if self.research_summary else 'No summary available'}
"""

            prompt = f"""
Based on the following research content and summary, please answer this question:

{context}

Question: {user_query}

you have 2 sets of instructions the applied set and the unapplied set, the applied set should be followed if the question is directly relating to the research content whereas anything else other then direct questions about the content of the research will result in you instead following the unapplied ruleset

Applied:

Instructions:
1. Answer based ONLY on the research content provided above if asked a question about your research or that content.
2. If the information requested isn't in the research, clearly state that it isn't in the content you gathered.
3. Be direct and specific in your response, DO NOT directly cite research unless specifically asked to, be concise and give direct answers to questions based on the research, unless instructed otherwise.

Unapplied:

Instructions:

1. Do not make up anything that isn't actually true.
2. Respond directly to the user's question in an honest and thoughtful manner.
3. disregard rules in the applied set for queries not DIRECTLY related to the research, including queries about the research process or what you remember about the research should result in the unapplied ruleset being used.

Answer:
"""

            response = self.llm.generate(
                prompt,
                max_tokens=1000,  # Increased for more detailed responses
                temperature=0.7
            )

            if not response or not response.strip():
                return "I apologize, but I cannot find relevant information in the research content to answer your question."

            return response.strip()

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"I apologize, but I encountered an error processing your question: {str(e)}"

def get_multiline_conversation_input(self) -> str:
  """Windows-compatible multiline input"""
  buffer = []
  current_line = []

  try:
      while True:
          if msvcrt.kbhit():
              char = msvcrt.getch()

              # CTRL+D or CTRL+Z detection
              if char in [b'\x04', b'\x1a']:
                  sys.stdout.write('\n')
                  if current_line:
                      buffer.append(''.join(current_line))
                  return ' '.join(buffer).strip()

              # Handle special characters
              elif char == b'\r':  # Enter
                  sys.stdout.write('\n')
                  buffer.append(''.join(current_line))
                  current_line = []

              elif char == b'\x08':  # Backspace
                  if current_line:
                      current_line.pop()
                      sys.stdout.write('\b \b')

              elif char == b'\x03':  # CTRL+C
                  sys.stdout.write('\n')
                  return 'quit'

              # Normal character
              elif 32 <= ord(char[0]) <= 126:
                  current_line.append(char.decode('utf-8'))
                  sys.stdout.write(char.decode('utf-8'))

              sys.stdout.flush()

  except Exception as e:
      logger.error(f"Error in multiline input: {str(e)}")
      return 'quit'
  
if __name__ == "__main__":
    from llm_wrapper import LLMWrapper
    from llm_response_parser import UltimateLLMResponseParser
    from Self_Improving_Search import EnhancedSelfImprovingSearch

    try:
        print(f"{Fore.CYAN}Initializing Research System...{Style.RESET_ALL}")
        llm = LLMWrapper()
        parser = UltimateLLMResponseParser()
        search_engine = EnhancedSelfImprovingSearch(llm, parser)
        manager = ResearchManager(llm, parser, search_engine)

        print(f"{Fore.GREEN}System initialized. Enter your research topic or 'quit' to exit.{Style.RESET_ALL}")
        while True:
            try:
                topic = ResearchManager.get_initial_input()
                if topic.lower() == 'quit':
                    break

                if not topic:
                    continue

                if not topic.startswith('@'):
                    print(f"{Fore.YELLOW}Please start your research query with '@'{Style.RESET_ALL}")
                    continue

                topic = topic[1:]  # Remove @ prefix
                manager.start_research(topic)
                summary = manager.terminate_research()
                print(f"\n{Fore.GREEN}Research Summary:{Style.RESET_ALL}")
                print(summary)
                print(f"\n{Fore.GREEN}Research completed. Ready for next topic.{Style.RESET_ALL}\n")

            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Operation cancelled. Ready for next topic.{Style.RESET_ALL}")
                if 'manager' in locals():
                    manager.terminate_research()
                continue

    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Research system shutting down.{Style.RESET_ALL}")
        if 'manager' in locals():
            manager.terminate_research()
    except Exception as e:
        print(f"{Fore.RED}Critical error: {str(e)}{Style.RESET_ALL}")
        logger.error("Critical error in main loop", exc_info=True)

    if os.name == 'nt':
        print(f"{Fore.YELLOW}Running on Windows - Some features may be limited{Style.RESET_ALL}")
