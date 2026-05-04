# Deviations from Original Plan

This document tracks changes and deviations from the original project plan as the implementation progresses.

## List of Changes

- **LLM Provider Transition**: The project has transitioned from using the OpenAI API to using Google's Gemini API for core agent functionalities and embeddings.
- **Supervisor LLM Model**: Implementation of the Supervisor LLM (`core/supervisor.py`) utilizes the **Gemini 2.5 Flash** model for high-precision semantic review of potential bias in hiring decisions.
