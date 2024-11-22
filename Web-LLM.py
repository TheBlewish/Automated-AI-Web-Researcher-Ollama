import sys
import msvcrt
import os
from colorama import init, Fore, Style
import logging
import time
from io import StringIO
from Self_Improving_Search import EnhancedSelfImprovingSearch
from llm_config import get_llm_config
from llm_response_parser import UltimateLLMResponseParser
from llm_wrapper import LLMWrapper
from strategic_analysis_parser import StrategicAnalysisParser
from research_manager import ResearchManager

# Initialize colorama
if os.name != 'nt':
  print("This version is Windows-specific. Please use the Unix version for other operating systems.")
  sys.exit(1)

init()  # Initialize colorama

# Set up logging
log_directory = 'logs'
if not os.path.exists(log_directory):
  os.makedirs(log_directory)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_file = os.path.join(log_directory, 'web_llm.log')
file_handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.handlers = []
logger.addHandler(file_handler)
logger.propagate = False

# Disable other loggers
for name in logging.root.manager.loggerDict:
  if name != __name__:
      logging.getLogger(name).disabled = True

class OutputRedirector:
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

def print_header():
  print(Fore.CYAN + Style.BRIGHT + """
  ╔══════════════════════════════════════════════════════════╗
  ║             🌐 Advanced Research Assistant 🤖             ║
  ╚══════════════════════════════════════════════════════════╝
  """ + Style.RESET_ALL)
  print(Fore.YELLOW + """
  Welcome to the Advanced Research Assistant!

  Commands:
  - For web search: start message with '/'
    Example: "/latest news on AI advancements"

  - For research mode: start message with '@'
    Example: "@analyze the impact of AI on healthcare"

  Press CTRL+Z to submit input.
  """ + Style.RESET_ALL)

def get_multiline_input() -> str:
    """Windows-compatible multiline input handler with improved reliability"""
    print(f"{Fore.GREEN}📝 Enter your message (Press CTRL+Z to submit):{Style.RESET_ALL}")
    lines = []
    current_line = ""

    try:
        while True:
            if msvcrt.kbhit():
                char = msvcrt.getch()
                
                # Convert bytes to string for comparison
                char_code = ord(char)
                
                # CTRL+Z detection (Windows EOF)
                if char_code == 26:  # ASCII code for CTRL+Z
                    print()  # New line
                    if current_line:
                        lines.append(current_line)
                    return ' '.join(lines).strip() or "q"
                
                # Enter key
                elif char in [b'\r', b'\n']:
                    print()  # New line
                    lines.append(current_line)
                    current_line = ""
                
                # Backspace
                elif char_code == 8:  # ASCII code for backspace
                    if current_line:
                        current_line = current_line[:-1]
                        print('\b \b', end='', flush=True)
                
                # Regular character input
                elif 32 <= char_code <= 126:  # Printable ASCII range
                    try:
                        char_str = char.decode('utf-8')
                        current_line += char_str
                        print(char_str, end='', flush=True)
                    except UnicodeDecodeError:
                        continue

            time.sleep(0.01)  # Prevent high CPU usage

    except KeyboardInterrupt:
        print("\nInput interrupted")
        return "q"
    except Exception as e:
        logger.error(f"Input error: {str(e)}")
        return "q"

def initialize_system():
  """Initialize system with enhanced error checking and recovery"""
  try:
      print(Fore.YELLOW + "Initializing system..." + Style.RESET_ALL)

      # Load configuration
      llm_config = get_llm_config()
      
      # Validate Ollama connection
      if llm_config['llm_type'] == 'ollama':
          import requests
          max_retries = 3
          retry_delay = 2
          
          for attempt in range(max_retries):
              try:
                  response = requests.get(llm_config['base_url'], timeout=5)
                  if response.status_code == 200:
                      break
                  elif attempt < max_retries - 1:
                      print(f"{Fore.YELLOW}Retrying Ollama connection ({attempt + 1}/{max_retries})...{Style.RESET_ALL}")
                      time.sleep(retry_delay)
                  else:
                      raise ConnectionError("Cannot connect to Ollama server")
              except requests.exceptions.RequestException as e:
                  if attempt == max_retries - 1:
                      raise ConnectionError(
                          "\nCannot connect to Ollama server!"
                          "\nPlease ensure:"
                          "\n1. Ollama is installed"
                          "\n2. Ollama server is running (try 'ollama serve')"
                          "\n3. The model specified in llm_config.py is pulled"
                      )
                  time.sleep(retry_delay)

      # Initialize components with output redirection
      with OutputRedirector() as output:
          llm_wrapper = LLMWrapper()
          parser = UltimateLLMResponseParser()
          search_engine = EnhancedSelfImprovingSearch(llm_wrapper, parser)
          research_manager = ResearchManager(llm_wrapper, parser, search_engine)

          # Validate LLM
          test_response = llm_wrapper.generate("Test", max_tokens=10)
          if not test_response:
              raise ConnectionError("LLM failed to generate response")

      print(Fore.GREEN + "System initialized successfully." + Style.RESET_ALL)
      return llm_wrapper, parser, search_engine, research_manager

  except Exception as e:
      logger.error(f"Error initializing system: {str(e)}", exc_info=True)
      print(Fore.RED + f"System initialization failed: {str(e)}" + Style.RESET_ALL)
      return None, None, None, None

def handle_search_mode(search_engine, query):
  """Handles web search operations"""
  print(f"{Fore.CYAN}Initiating web search...{Style.RESET_ALL}")
  try:
      # Change search() to search_and_improve() which is the correct method name
      results = search_engine.search_and_improve(query)
      print(f"\n{Fore.GREEN}Search Results:{Style.RESET_ALL}")
      print(results)
  except Exception as e:
      logger.error(f"Search error: {str(e)}")
      print(f"{Fore.RED}Search failed: {str(e)}{Style.RESET_ALL}")

def handle_research_mode(research_manager, query):
  """Handles research mode operations"""
  print(f"{Fore.CYAN}Initiating research mode...{Style.RESET_ALL}")

  try:
      # Start the research
      research_manager.start_research(query)

      submit_key = "CTRL+Z" if os.name == 'nt' else "CTRL+D"
      print(f"\n{Fore.YELLOW}Research Running. Available Commands:{Style.RESET_ALL}")
      print(f"Type command and press {submit_key}:")
      print("'s' = Show status")
      print("'f' = Show focus")
      print("'q' = Quit research")

      while research_manager.is_active():
          try:
              command = get_multiline_input().strip().lower()
              if command == 's':
                  print("\n" + research_manager.get_progress())
              elif command == 'f':
                  if research_manager.current_focus:
                      print(f"\n{Fore.CYAN}Current Focus:{Style.RESET_ALL}")
                      print(f"Area: {research_manager.current_focus.area}")
                      print(f"Priority: {research_manager.current_focus.priority}")
                      print(f"Reasoning: {research_manager.current_focus.reasoning}")
                  else:
                      print(f"\n{Fore.YELLOW}No current focus area{Style.RESET_ALL}")
              elif command == 'q':
                  break
          except KeyboardInterrupt:
              break

      # Get final summary first
      summary = research_manager.terminate_research()

      # Ensure research UI is fully cleaned up
      research_manager._cleanup_research_ui()

      # Now in main terminal, show summary
      print(f"\n{Fore.GREEN}Research Summary:{Style.RESET_ALL}")
      print(summary)

      # Only NOW start conversation mode if we have a valid summary
      if hasattr(research_manager, 'research_complete') and \
         hasattr(research_manager, 'research_summary') and \
         research_manager.research_complete and \
         research_manager.research_summary:
          time.sleep(0.5)  # Small delay to ensure clean transition
          research_manager.start_conversation_mode()

      return

  except KeyboardInterrupt:
      print(f"\n{Fore.YELLOW}Research interrupted.{Style.RESET_ALL}")
      research_manager.terminate_research()
  except Exception as e:
      logger.error(f"Research error: {str(e)}")
      print(f"\n{Fore.RED}Research error: {str(e)}{Style.RESET_ALL}")
      research_manager.terminate_research()

def main():
  init()  # Initialize colorama
  print_header()
  
  try:
      components = initialize_system()
      if not all(components):
          sys.exit(1)
          
      llm, parser, search_engine, research_manager = components

      while True:
          try:
              user_input = get_multiline_input()
              
              # Skip empty inputs
              if not user_input:
                  continue
                  
              # Handle exit commands
              if user_input.lower() in ["@quit", "quit", "q"]:
                  break

              # Handle help command
              if user_input.lower() == 'help':
                  print_header()
                  continue

              # Process commands
              if user_input.startswith('/'):
                  handle_search_mode(search_engine, user_input[1:].strip())
              elif user_input.startswith('@'):
                  handle_research_mode(research_manager, user_input[1:].strip())
              else:
                  print(f"{Fore.YELLOW}Please start with '/' for search or '@' for research.{Style.RESET_ALL}")

          except KeyboardInterrupt:
              print(f"\n{Fore.YELLOW}Use 'q' to quit or continue with new input.{Style.RESET_ALL}")
              continue
          except Exception as e:
              logger.error(f"Error processing input: {str(e)}")
              print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
              continue

  except KeyboardInterrupt:
      print(f"\n{Fore.YELLOW}Program terminated by user.{Style.RESET_ALL}")
  except Exception as e:
      logger.critical(f"Critical error: {str(e)}")
      print(f"{Fore.RED}Critical error: {str(e)}{Style.RESET_ALL}")
  finally:
      try:
          if 'research_manager' in locals() and research_manager:
              research_manager.cleanup()
      except Exception as e:
          logger.error(f"Cleanup error: {str(e)}")
      print(Fore.YELLOW + "\nGoodbye!" + Style.RESET_ALL)
      sys.exit(0)

if __name__ == "__main__":
  main()
