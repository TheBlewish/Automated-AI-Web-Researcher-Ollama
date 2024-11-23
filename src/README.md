# Automated-AI-Web-Researcher-Ollama

## Description
Automated-AI-Web-Researcher is an innovative research assistant that leverages locally-run large language models through Ollama to conduct thorough, automated online research on any given topic or question. Unlike traditional LLM interactions, this tool actually performs structured research by breaking down queries into focused research areas, systematically investigating via web searching and then scraping of relevant websites each area, and compiling it's findings all saved automatically into a text document with all content found and links for the source of each, and whenever you want it to stop it's research you can input a command which then results in the research terminating and the LLM reviewing all the content it found and providing a comprehensive final summary to your original topic or question, and then you can also ask the LLM questions about it's research findings if you would like.

## Project Demonstration

[![My Project Demo](https://img.youtube.com/vi/hS7Q1B8N1mQ/0.jpg)](https://youtu.be/hS7Q1B8N1mQ "My Project Demo")

Click the image above to watch the demonstration of My Project.

## Here's how it works:

1. You provide a research query (e.g., "What year will global population begin to decrease rather than increase according to research?")
2. The LLM analyzes your query and generates 5 specific research focus areas, each with assigned priorities based on relevance to the topic or question.
3. Starting with the highest priority area, the LLM:
   - Formulates targeted search queries
   - Performs web searches using multiple providers (Tavily, Brave, Bing, Exa)
   - Analyzes search results selecting the most relevant web pages
   - Scrapes and extracts relevant information for selected web pages
   - Documents all content it has found during the research session into a research text file including links to websites that the content was retrieved from
4. After investigating all focus areas, the LLM based on information is found generates new focus areas, and repeating it's research cycle, often finding new relevant focus areas based on findings in research it has previously found leading to interesting and novel research focuses in some cases.
5. You can let it research as long as you would like at any time being able to input a quit command which then stops the research and causes the LLM to review all the content collected so far in full and generate a comprehensive summary to respond to your original query or topic. 
6. Then the LLM will enter a conversation mode where you can ask specific questions about the research findings if desired.

The key distinction is that this isn't just a chatbot - it's an automated research assistant that methodically investigates topics and maintains a documented research trail all from a single question or topic of your choosing, and depending on your system and model can do over a hundred searches and content retrievals in a relatively short amount of time, you can leave it running and come back to a full text document with over a hundred pieces of content from relevant websites, and then have it summarise the findings and then even ask it questions about what it found.

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

1. Clone the repository:

```sh
git clone https://github.com/TheBlewish/Automated-AI-Web-Researcher-Ollama
cd Automated-AI-Web-Researcher-Ollama
```

2. Create and activate a virtual environment:

```sh
python -m venv venv
source venv/bin/activate  # On Windows, use venv\Scripts\activate
```

3. Install dependencies:

```sh
pip install -r requirements.txt
```

4. Set up API keys:
Create a `.env` file in the project root with your API keys:
```
TAVILY_API_KEY=your_tavily_key
BRAVE_API_KEY=your_brave_key
BING_API_KEY=your_bing_key
EXA_API_KEY=your_exa_key
```
Note: The system will work with any combination of configured providers. If a provider's API key is not set, it will be skipped in the fallback chain. You don't need them all. If you don't add any, DuckDuckGo will be used.

5. Install and Configure Ollama:
- Install Ollama following instructions at https://ollama.ai
- Using your selected model file, create a custom model variant with the required context length
  (phi3:3.8b-mini-128k-instruct or phi3:14b-medium-128k-instruct are recommended)

Create a file named `modelfile` with these exact contents:

```
FROM your-model-name

PARAMETER num_ctx 38000
```

Replace "your-model-name" with your chosen model (e.g., phi3:3.8b-mini-128k-instruct).

Then create the model:

```sh
ollama create research-phi3 -f modelfile
```

Note: This specific configuration is necessary as recent Ollama versions have reduced context windows on models like phi3:3.8b-mini-128k-instruct despite the name suggesting high context which is why the modelfile step is necessary due to the high amount of information being used during the research process. 

## Usage

1. Start Ollama:

```sh
ollama serve
```

2. Run the researcher:

```sh
python Web-LLM.py
```

3. Start a research session:
- Type `@` followed by your research query
- Press CTRL+D to submit
- Example: `@What year is global population projected to start declining?`

4. During research you can use the following commands by typing the letter associated with each and submitting with CTRL+D:
- Use `s` to show status.
- Use `f` to show current focus.
- Use `p` to pause and assess research progress, which will give you an assessment from the LLM after reviewing the entire research content whether it can answer your query or not with the content it has so far collected, then it waits for you to input one of two commands, `c` to continue with the research or `q` to terminate it which will result in a summary like if you terminated it without using the pause feature.
- Use `q` to quit research.

5. After research completes:
- Wait for the summary to be generated, and review the LLM's findings.
- Enter conversation mode to ask specific questions about the findings.
- Access the detailed research content found, avaliable in the in a research session text file which will appear in the programs directory, which includes:
  * All retrieved content
  * Source URLs for all information
  * Focus areas investigated
  * Generated summary

## Configuration

The system can be configured through several files:

1. `llm_config.py`: LLM settings and model configuration
2. `system_config.py`: Search provider settings, including:
   - Default provider selection
   - Fallback order
   - Provider-specific parameters
   - Rate limiting controls

## Current Status
This is a prototype that demonstrates functional automated research capabilities. While still in development, it successfully performs structured research tasks. Currently tested and working well with the phi3:3.8b-mini-128k-instruct model when the context is set as advised previously.

## Dependencies
- Ollama
- Python packages listed in requirements.txt
- Recommended model: phi3:3.8b-mini-128k-instruct or phi3:14b-medium-128k-instruct (with custom context length as specified)
- API keys for desired search providers

## Contributing
Contributions are welcome! This is a prototype with room for improvements and new features.

## License
This project is licensed under the MIT License - see the [LICENSE] file for details.

## Acknowledgments
- Ollama team for their local LLM runtime
- Search providers: Tavily, Brave, Bing, Exa, and DuckDuckGo
- Contributors to the Python packages used in this project

## Personal Note
This tool represents an attempt to bridge the gap between simple LLM interactions and genuine research capabilities. By structuring the research process and maintaining documentation, it aims to provide more thorough and verifiable results than traditional LLM conversations. It also represents an attempt to improve on my previous project 'Web-LLM-Assistant-Llamacpp-Ollama' which simply gave LLM's the ability to search and scrape websites to answer questions. This new program, unlike it's predecessor I feel thos program takes that capability and uses it in a novel and actually very useful way, I feel that it is the most advanced and useful way I could conceive of building on my previous program, as a very new programmer this being my second ever program I feel very good about the result, I hope that it hits the mark! 
Given how much I have now been using it myself, unlike the previous program which felt more like a novelty then an actual tool, this is actually quite useful and unique, but I am quite biased!

Please enjoy! and feel free to submit any suggestions for improvements, so that we can make this automated AI researcher even more capable.

## Disclaimer
This project is for educational purposes only. Ensure you comply with the terms of service of all APIs and services used.
