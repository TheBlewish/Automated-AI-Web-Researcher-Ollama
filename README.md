# Automated-AI-Web-Researcher-Ollama

## Description
Automated-AI-Web-Researcher is an innovative research assistant that leverages locally run large language models through Ollama to conduct thorough, automated online research on any given topic or question. Unlike traditional LLM interactions, this tool actually performs structured research by breaking down queries into focused research areas, systematically investigating each area via web searching and scraping relevant websites, and compiling its findings. The findings are automatically saved into a text document with all the content found and links to the sources. Whenever you want it to stop its research, you can input a command, which will terminate the research. The LLM will then review all of the content it found and provide a comprehensive final summary of your original topic or question. Afterward, you can ask the LLM questions about its research findings.

## Project Demonstration
[![My Project Demo](https://img.youtube.com/vi/hS7Q1B8N1mQ/0.jpg)](https://youtu.be/hS7Q1B8N1mQ "My Project Demo")

Click the image above to watch the demonstration of my project.

## Here's How It Works:
1. You provide a research query (e.g., "What year will the global population begin to decrease rather than increase according to research?").
2. The LLM analyzes your query and generates 5 specific research focus areas, each with assigned priorities based on relevance to the topic or question.
3. Starting with the highest priority area, the LLM:
    - Formulates targeted search queries
    - Performs web searches using multiple providers (Tavily, Brave, Bing, Exa)
    - Analyzes search results, selecting the most relevant web pages
    - Scrapes and extracts relevant information from the selected web pages
    - Documents all content found during the research session into a research text file, including links to the websites that the content was retrieved from
4. After investigating all focus areas, the LLM generates new focus areas based on the information found and repeats its research cycle, often discovering new relevant focus areas based on previous findings, leading to interesting and novel research focuses in some cases.
5. You can let it research as long as you like, with the ability to input a quit command at any time. This will stop the research and cause the LLM to review all the content collected so far in full, generating a comprehensive summary in response to your original query or topic.
6. The LLM will then enter a conversation mode where you can ask specific questions about the research findings if desired.

The key distinction is that this isn't just a chatbot—it's an automated research assistant that methodically investigates topics and maintains a documented research trail, all from a single question or topic of your choosing. Depending on your system and model, it can perform over a hundred searches and content retrievals in a relatively short amount of time. You can leave it running and return to a full text document with over a hundred pieces of content from relevant websites and then have it summarize the findings, after which you can ask it questions about what it found.

## Features
- Automated research planning with prioritized focus areas
- Multi-provider search system with automatic fallback
- Systematic web searching and content analysis
- All research content and source URLs saved into a detailed text document
- Research summary generation
- Post-research Q&A capability about findings
- Self-improving search mechanism with provider optimization
- Rich console output with status indicators
- Comprehensive answer synthesis using web-sourced information
- Research conversation mode for exploring findings

## Search Providers
The system supports multiple search providers with automatic fallback:

1. Tavily (Primary)
   - AI-powered search with relevance scoring
   - Includes AI-generated summaries
   - Optimized for research queries

2. Brave Search
   - High-quality web results
   - Built-in relevance scoring
   - Real-time indexing

3. Bing
   - Comprehensive web coverage
   - News and recent content
   - Academic results

4. Exa
   - Specialized search capabilities
   - High-precision results
   - Content highlighting

5. DuckDuckGo (Fallback)
   - Privacy-focused results
   - No API key required
   - Reliable fallback option

## Installation
1. **Clone the repository:**

    ```sh
    git clone https://github.com/TheBlewish/Automated-AI-Web-Researcher-Ollama
    cd Automated-AI-Web-Researcher-Ollama
    ```

2. **Create and activate a virtual environment:**

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use venv\Scripts\activate
    ```

3. **Install dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

4. **Set up API keys:**

    Create a `.env` file in the project root with your API keys:

    ```
    TAVILY_API_KEY=your_tavily_key
    BRAVE_API_KEY=your_brave_key
    BING_API_KEY=your_bing_key
    EXA_API_KEY=your_exa_key
    ```

    **Note:** The system will work with any combination of configured providers. If a provider's API key is not set, it will be skipped in the fallback chain. You don't need all of them. If you don't add any API keys, DuckDuckGo will be used.

5. **Install and configure Ollama:**

    Install Ollama following the instructions at [https://ollama.ai](https://ollama.ai).

    Using your selected model file, create a custom model variant with the required context length (`phi3:3.8b-mini-128k-instruct` or `phi3:14b-medium-128k-instruct` are recommended).

    Create a file named `modelfile` with the following exact contents:

    ```
    FROM your-model-name

    PARAMETER num_ctx 38000
    ```

    Replace "your-model-name" with your chosen model (e.g., `phi3:3.8b-mini-128k-instruct`).

    Then create the model:

    ```sh
    ollama create research-phi3 -f modelfile
    ```

    **Note:** This specific configuration is necessary as recent Ollama versions have reduced context windows on models like `phi3:3.8b-mini-128k-instruct` despite the name suggesting high context, which is why the `modelfile` step is necessary due to the large amount of information used during the research process.

## Usage
1. **Start Ollama:**

    ```sh
    ollama serve
    ```

2. **Run the researcher:**

    ```sh
    python Web-LLM.py
    ```

3. **Start a research session:**
    - Type `@` followed by your research query.
    - Press `CTRL+D` to submit.
    - Example: `@What year is the global population projected to start declining?`

4. **During research, you can use the following commands by typing the associated letter and submitting with `CTRL+D`:**
    - Use `s` to show status.
    - Use `f` to show the current focus.
    - Use `p` to pause and assess research progress, which will give you an assessment from the LLM after reviewing the entire research content to determine whether it can answer your query with the content collected so far. It will then wait for you to input one of two commands: `c` to continue with the research or `q` to terminate it, resulting in a summary as if you had terminated it without using the pause feature.
    - Use `q` to quit research.

5. **After the research completes:**
    - Wait for the summary to be generated and review the LLM's findings.
    - Enter conversation mode to ask specific questions about its findings.
    - Access the detailed research content found, available in a research session text file which will be located in the program's directory. This includes:
        - All retrieved content
        - Source URLs for all of the information
        - Focus areas investigated
        - Generated summary

## Configuration
The system can be configured through several files:

1. `llm_config.py`: LLM settings and model configuration
2. `system_config.py`: Search provider settings, including:
    - Default provider selection
    - Fallback order
    - Provider-specific parameters
    - Rate limiting controls

## Running on Windows
To use this application on Windows, you'll need to install **WSL 2** (if you already have it, skip to step 4).

1. Open an administrator terminal and run the following command:
    ```cmd
    wsl --install
    ```
2. Once the installation is complete, press the Windows key and search for "Ubuntu" to launch WSL 2.
3. Follow the on-screen instructions to complete the Ubuntu setup.
4. Proceed from the beginning with the installation and usage steps in the WSL terminal.

## Current Status
This is a prototype that demonstrates functional automated research capabilities. While still in development, it successfully performs structured research tasks. It has been tested and works well with the `phi3:3.8b-mini-128k-instruct` model when the context is set as advised previously.

## Dependencies
- Ollama
- Python packages listed in `requirements.txt`
- Recommended models: `phi3:3.8b-mini-128k-instruct` or `phi3:14b-medium-128k-instruct` (with custom context length as specified)
- API keys for desired search providers

## Contributing
Contributions are welcome! This is a prototype with room for improvements and new features.

## License
This project is licensed under the MIT License—see the [LICENSE](LICENSE) file for details.

## Acknowledgments
- Ollama team for their local LLM runtime
- Search providers: Tavily, Brave, Bing, Exa, and DuckDuckGo
- Contributors to the Python packages used in this project

## Personal Note
This tool represents an attempt to bridge the gap between simple LLM interactions and genuine research capabilities. By structuring the research process and maintaining documentation, it aims to provide more thorough and verifiable results than traditional LLM conversations. It also represents an attempt to improve on my previous project, 'Web-LLM-Assistant-Llamacpp-Ollama,' which simply gave LLMs the ability to search and scrape websites to answer questions. Unlike its predecessor, I feel this program takes that capability and uses it in a novel and very useful way. As a very new programmer, with this being my second ever program, I feel very good about the result. I hope that it hits the mark!

Given how much I have been using it myself, unlike the previous program, which felt more like a novelty than an actual tool, this is actually quite useful and unique—but I am quite biased!

Please enjoy! And feel free to submit any suggestions for improvements so that we can make this automated AI researcher even more capable.

## Disclaimer
This project is for educational purposes only. Ensure you comply with the terms of service of all APIs and services used.
