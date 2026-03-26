# ScamTrap AI

ScamTrap AI is a honeypot system that simulates user interactions with potential scammers to analyze fraudulent communication patterns and collect structured data.

## Why I Built This

This project started after a family member was targeted by a scam. While exploring the problem, I found that in 2025 alone, India reported 28 lakh phishing cases resulting in ₹22,495 crore in losses.

Despite the scale, there is very little structured data on how scammers actually operate — how they respond, what tactics they use, and how conversations evolve.

ScamTrap AI is my attempt to start building that dataset.

## What It Does

- Simulates realistic user conversations with scammers  
- Engages with scam messages using context-aware replies  
- Extracts key signals from conversations:
  - UPI IDs  
  - Bank account details  
  - IFSC codes  
  - Phishing links  
- Uses keyword heuristics and pattern matching with confidence scoring  
- Stores interactions as structured data for further analysis  

## How It Works

1. Incoming scam message is processed  
2. System generates a contextual reply using an LLM  
3. Conversation continues to simulate human behavior  
4. Responses are analyzed using regex + heuristic rules  
5. Sensitive entities and patterns are extracted  
6. Data is stored in structured format for analysis  

## Current Progress

- Built an initial prototype  
- Tested on 20+ scam messages  

## Tech Stack

- **Backend:** FastAPI (deployed on Render)  
- **Frontend:** Netlify dashboard  
- **Core Logic:** Python, Regex, Heuristics  
- **AI Layer:** LLM-based response generation  

## Demo

(Coming soon)

## Future Work

- Improve scam classification accuracy  
- Expand dataset of scam interactions  
- Identify recurring scam strategies  
- Build detection and prevention systems using collected data  

## Status

Actively being developed.

## Author

Devyan Nitharwal
