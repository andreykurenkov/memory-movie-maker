

# **Memory Movie Maker: Product Requirements & Technical Design**

## **1\. Product Requirements Document (PRD)**

### **1.1. Vision & Opportunity**

**Product Name:** Memory Movie Maker  
**Vision:** To create an intelligent, conversational video editing tool that empowers anyone to transform their raw photos and videos into polished, emotionally resonant "memory movies" with minimal effort.  
**Problem Statement:** People capture countless digital memories (photos, video clips) during significant life events like vacations, weddings, and holidays. However, these assets often remain disorganized and unshared because traditional video editing is time-consuming, requires technical skill, and presents a steep learning curve.1 Existing automated tools offer limited creative control and often fail to capture the specific "vibe" or narrative of the event.  
**Opportunity:** By leveraging advanced agentic AI, we can create a "do-it-for-me" solution that understands user intent through natural language. This tool will automate the most tedious aspects of editing—selection, trimming, and synchronization—while allowing for intuitive, conversational refinement, making high-quality video creation accessible to everyone.

### **1.2. Target Audience**

* **Families & Parents:** Individuals wanting to create memorable compilations of children's milestones, family vacations, and holidays without investing hours in editing.  
* **Travelers & Adventurers:** Users who want to quickly produce exciting summaries of their trips to share on social media or with friends.  
* **Event Goers:** People attending weddings, concerts, or parties who want to combine their footage with others' to create a collective memory.  
* **Casual Content Creators:** Social media users who need a fast, easy way to generate engaging video content from raw footage.

### **1.3. User Stories & Requirements**

#### **Core User Stories (MVP)**

* **US1:** As a user, I want to upload a folder of photos and video clips so the system can use them as source material.  
* **US2:** As a user, I want to upload a music track so it can be used as the video's soundtrack.  
* **US3:** As a user, I want to provide a simple text prompt describing the desired length, aspect ratio, and "vibe" (e.g., "a 2-minute upbeat, vertical video of my Hawaii trip") to guide the initial creation.  
* **US4:** As a user, I want to mark specific photos or videos as "required" to ensure they are included in the final cut.  
* **US5:** As a user, I want the AI to autonomously analyze my media, select the best moments, and create a first draft that is rhythmically synchronized to the music.  
* **US6:** As a user, I want to view the generated video in a simple web interface.  
* **US7:** As a user, I want to provide iterative feedback in plain English (e.g., "make the beginning slower," "add more shots of the sunset") to refine the video.  
* **US8:** As a user, I want to receive a new version of the video quickly after providing feedback.

#### **Functional Requirements**

* **Media Ingestion:** Support for common image (JPEG, PNG) and video (MP4, MOV) formats.  
* **AI Analysis:** Multimodal analysis of visual content for quality, subjects, and aesthetics. Deep audio analysis for rhythm (beats, tempo) and energy.  
* **Automated Composition:** An intelligent engine to curate clips, determine pacing, and synchronize cuts to the music.  
* **Agentic Self-Correction:** The system must autonomously review and improve its own output before presenting it to the user.  
* **Natural Language Refinement:** An NLP module to interpret user feedback and translate it into concrete editing commands.2  
* **Web Interface:** A minimal web GUI for file upload, prompt input, video playback, and feedback submission.

#### **Non-Functional Requirements**

* **Performance:** The initial, agent-driven render may take up to 10-20 minutes. Subsequent user-driven refinements should be significantly faster.  
* **Technology Stack:** The system will be built in Python, leveraging the Google Agent Development Kit (ADK), Gemini API, and Essentia audio analysis library.  
* **Deployment:** The MVP will be designed for local execution, with a forward-looking architecture suitable for future cloud deployment.

---

## **2\. Technical Design Document (TDD)**

### **2.1. System Architecture: A Multi-Agent System (MAS)**

The system is architected as an autonomous, multi-agent system (MAS) using Google's Agent Development Kit (ADK). This code-first, modular framework allows for the creation of specialized agents that collaborate to achieve the final goal, promoting testability and scalability. The core of the architecture is an **agentic self-correction loop**, where the system generates, evaluates, and refines the video autonomously before user interaction.

#### **Component Diagram**

The system comprises five distinct agents orchestrated by a RootAgent:

1. **RootAgent (Orchestrator):** The central controller that manages the end-to-end workflow. It receives user input, invokes other agents in sequence, and manages the ProjectState object.  
2. **AnalysisAgent:** A specialist agent responsible for all media analysis. It uses tools to extract rich metadata from visual and audio inputs.  
3. **CompositionAgent:** The creative engine. It generates the video timeline based on analyzed data and renders the video file.  
4. **EvaluationAgent:** A "critic" agent that assesses the rendered video against the user's prompt, providing qualitative feedback for improvement.  
5. **RefinementAgent:** An NLP specialist that translates natural language feedback (from the EvaluationAgent or the user) into structured, machine-readable editing commands.2

#### **Data Flow**

* **Autonomous Creation:** User Input \-\> RootAgent \-\> AnalysisAgent \-\> CompositionAgent (renders v1) \-\> EvaluationAgent (critiques v1) \-\> RefinementAgent (creates edit command) \-\> CompositionAgent (renders v2) \-\>... \-\> Final Video is presented to the user.  
* **User-Driven Refinement:** User Feedback \-\> RootAgent \-\> RefinementAgent \-\> CompositionAgent \-\> New Video.

### **2.2. Core Data Models**

The entire state of a video project is encapsulated in a single, serializable JSON object, ProjectState, which serves as the single source of truth passed between agents.5

| Field Path | Type | Description |
| :---- | :---- | :---- |
| projectId | String | A unique identifier for the project. |
| userInputs.media | Array\<MediaAsset\> | All user-provided photos and videos. |
| userInputs.music | Array\<MediaAsset\> | User-selected music tracks (MVP supports one). |
| userInputs.initialPrompt | String | The initial high-level user description. |
| userInputs.targetDuration | Integer | Desired final video length in seconds. |
| userInputs.aspectRatio | String | Desired output aspect ratio (e.g., "16:9"). |
| analysis.musicProfiles | Array\<AudioAnalysisProfile\> | Full analysis results for the music tracks. |
| analysis.mediaPool | Array\<MediaAsset\> | Media assets enriched with AI metadata. |
| timeline.segments | Array\<TimelineSegment\> | The ordered "shot list" for the final video. |
| history.prompts | Array | A log of all user and agent-generated prompts. |

* **MediaAsset:** Represents a single media file, containing its path, type, and a geminiAnalysis object to cache structured metadata (description, aesthetic score, tags, etc.).  
* **AudioAnalysisProfile:** Stores detailed analysis of a music track, including beat\_timestamps, tempo (BPM), a normalized energy\_curve, and a vibe object (e.g., danceability, mood).6  
* **TimelineSegment:** Represents a single shot on the final timeline, linking to a MediaAsset and specifying the in/out points and duration.

### **2.3. Detailed Agent Design**

#### **AnalysisAgent**

This agent uses specialized tools for media analysis.

* **Visual Analysis Tool (Gemini):** This tool interfaces with the Gemini API to analyze each photo and video.7 A structured prompt will be used to request a JSON output containing:  
  description, aesthetic\_score, quality\_issues, main\_subjects, tags, best\_moment\_timestamp (for videos), and motion\_level.8  
* **Audio Analysis Tool (Essentia):** For precise waveform analysis, this tool uses the **Essentia** library, a high-performance tool for Music Information Retrieval.12 It will extract:  
  * **Rhythm:** Beat timestamps and overall tempo using RhythmExtractor2013.15  
  * **Energy:** A frame-by-frame RMS energy curve to map the music's intensity.13  
  * **Vibe:** High-level descriptors like danceability and mood using Essentia's pre-trained deep learning models.18

#### **CompositionAgent**

This agent handles the creative assembly and rendering.

* **Curation Algorithm:** Implements a **chronological clustering** method. It groups media by capture time, scores each asset based on aesthetic quality and thematic relevance to the music's "vibe," and selects the highest-scoring clips to fill the target duration while maintaining a narrative flow.  
* **Pacing Algorithm:** This algorithm generates the timeline.segments array. It iterates through the music's beat\_timestamps and uses the energy\_curve to make dynamic pacing decisions. High-energy sections will trigger shorter clips and faster cuts, while low-energy sections will use longer shots.20  
* **Rendering Tool (MoviePy/FFmpeg):** For the MVP, **MoviePy** will be used to programmatically construct the timeline from TimelineSegment data due to its intuitive API.21 The  
  concatenate\_videoclips function will be central to this process.24 For future performance optimization, direct  
  **FFmpeg** calls can be integrated, as they are significantly faster for simple operations.26

#### **EvaluationAgent**

This agent is the core of the self-correction loop. It uses a Gemini-powered tool to critique the rendered video.

* **Critique Tool (Gemini):** This tool takes the rendered video and the original user prompt as input. It queries the Gemini model with a prompt designed to elicit actionable feedback, such as:"You are a professional video editor. The user requested '{user\_prompt}'. Analyze this video and provide specific, constructive feedback on its pacing, thematic coherence, and visual quality. Suggest concrete changes to better match the user's intent."

#### **RefinementAgent**

This agent translates natural language into structured commands.

* **Command Parsing Tool (Gemini):** Inspired by the ExpressEdit paper, this tool uses Gemini to parse feedback (from the EvaluationAgent or user) into a JSON object.3 The prompt will define a schema for possible intents like  
  REPLACE\_CONTENT or ADJUST\_PACING, including parameters for temporal scope and content filters.

### **2.4. User Interface (UI) Design**

A minimal web GUI will be built using **Gradio**, chosen for its speed and simplicity in creating interfaces for ML applications, which is more suitable for an MVP than a full-stack framework like Flask.

* **Layout:** A gr.Blocks layout will be used for customization.  
* **Components:**  
  * gr.UploadButton for uploading multiple photos and videos.  
  * gr.Audio for the music track.  
  * gr.Textbox for the initial prompt and subsequent refinement commands.  
  * gr.Video to display the rendered output.  
* **Workflow:** A "Generate" button will trigger the full autonomous creation process. After viewing the result, the user can type feedback and click a "Refine" button to trigger the user-driven refinement loop.

---

## **3\. Implementation Roadmap**

This roadmap outlines a phased approach to developing the Memory Movie Maker MVP over an estimated 8-week period.

### **Phase 1: Core Backend & Prototyping (Weeks 1-3)**

**Goal:** Establish and validate the fundamental media analysis and video composition pipeline.

* **Week 1:** Project setup, dependency installation (Python, ADK, Gemini SDK, Essentia, MoviePy), and implementation of the ProjectState data models.  
* **Week 2:** Develop the AnalysisAgent's tools. Implement Gemini visual analysis and Essentia audio analysis. Write scripts to test and validate metadata extraction on sample media.  
* **Week 3:** Develop the CompositionAgent's logic. Implement the curation and rhythmic pacing algorithms. Build the MoviePy rendering tool.  
* **Deliverable:** A command-line script that can take a directory of media and a music file as input and produce a single, coherent video output.

### **Phase 2: Agentic Architecture & Self-Correction (Weeks 4-6)**

**Goal:** Refactor the core logic into the ADK multi-agent framework and implement the autonomous refinement loop.

* **Week 4:** Structure the project using ADK. Wrap the analysis and composition logic from Phase 1 into the AnalysisAgent and CompositionAgent. Implement the RootAgent to orchestrate a single-pass generation.  
* **Week 5:** Implement the EvaluationAgent, including prompt engineering for the critique tool. Implement the RefinementAgent and the NLP-to-JSON command parsing logic.  
* **Week 6:** Integrate all agents. Implement the self-correction loop within the RootAgent, allowing it to cycle through composition, evaluation, and refinement 2-3 times before finalizing the output.  
* **Deliverable:** A CLI-driven application that demonstrates the full autonomous creation and self-correction workflow, producing a higher-quality initial video.

### **Phase 3: Web UI & User Interaction (Weeks 7-8)**

**Goal:** Build the user-facing web interface and connect it to the agentic backend for a complete, interactive MVP.

* **Week 7:** Develop the Gradio web application. Implement the UI components for file upload, text input, and video display. Connect the "Generate" button to trigger the RootAgent's full autonomous workflow.  
* **Week 8:** Implement the user-driven refinement loop. Connect the feedback textbox and "Refine" button to a workflow that uses the RefinementAgent and CompositionAgent to re-render the video based on user commands. Final testing and bug fixing.  
* **Deliverable:** A functional MVP web application that fulfills all core user stories, allowing users to generate and conversationally refine their own memory movies.

#### **Works cited**

1. Video Editing Project Timelines: 10 Common Use Cases \- Twine Blog, accessed August 2, 2025, [https://www.twine.net/blog/video-editing-project-timeline/](https://www.twine.net/blog/video-editing-project-timeline/)  
2. arxiv.org, accessed August 2, 2025, [https://arxiv.org/html/2403.17693v1](https://arxiv.org/html/2403.17693v1)  
3. ExpressEdit, accessed August 2, 2025, [https://expressedit.kixlab.org/](https://expressedit.kixlab.org/)  
4. \[Literature Review\] ExpressEdit: Video Editing with Natural Language and Sketching, accessed August 2, 2025, [https://www.themoonlight.io/en/review/expressedit-video-editing-with-natural-language-and-sketching](https://www.themoonlight.io/en/review/expressedit-video-editing-with-natural-language-and-sketching)  
5. 10 Tips To Organize Video Files for Faster Edits \- Iconik, accessed August 2, 2025, [https://www.iconik.io/blog/10-tips-to-organize-video-files-for-faster-edits](https://www.iconik.io/blog/10-tips-to-organize-video-files-for-faster-edits)  
6. ESSENTIA: AN AUDIO ANALYSIS LIBRARY FOR MUSIC INFORMATION RETRIEVAL \- GitHub, accessed August 2, 2025, [https://raw.githubusercontent.com/wiki/doctorfree/MusicPlayerPlus/Essentia\_An\_Audio\_Analysis\_Library\_for\_M.pdf](https://raw.githubusercontent.com/wiki/doctorfree/MusicPlayerPlus/Essentia_An_Audio_Analysis_Library_for_M.pdf)  
7. Multimodal AI | Google Cloud, accessed August 2, 2025, [https://cloud.google.com/use-cases/multimodal-ai](https://cloud.google.com/use-cases/multimodal-ai)  
8. Image understanding | Gemini API | Google AI for Developers, accessed August 2, 2025, [https://ai.google.dev/gemini-api/docs/image-understanding](https://ai.google.dev/gemini-api/docs/image-understanding)  
9. Video understanding | Gemini API | Google AI for Developers, accessed August 2, 2025, [https://ai.google.dev/gemini-api/docs/video-understanding](https://ai.google.dev/gemini-api/docs/video-understanding)  
10. Design multimodal prompts | Generative AI on Vertex AI \- Google Cloud, accessed August 2, 2025, [https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/design-multimodal-prompts](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/design-multimodal-prompts)  
11. Image understanding | Generative AI on Vertex AI \- Google Cloud, accessed August 2, 2025, [https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-understanding](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/image-understanding)  
12. essentia \- PyPI, accessed August 2, 2025, [https://pypi.org/project/essentia/](https://pypi.org/project/essentia/)  
13. ESSENTIA: an Audio Analysis Library for Music Information Retrieval \- ResearchGate, accessed August 2, 2025, [https://www.researchgate.net/publication/256104772\_ESSENTIA\_an\_Audio\_Analysis\_Library\_for\_Music\_Information\_Retrieval](https://www.researchgate.net/publication/256104772_ESSENTIA_an_Audio_Analysis_Library_for_Music_Information_Retrieval)  
14. Homepage — Essentia 2.1-beta6-dev documentation, accessed August 2, 2025, [https://essentia.upf.edu/](https://essentia.upf.edu/)  
15. Essentia Python examples — Essentia 2.1-beta6-dev documentation, accessed August 2, 2025, [https://essentia.upf.edu/essentia\_python\_examples.html](https://essentia.upf.edu/essentia_python_examples.html)  
16. Algorithms reference — Essentia 2.1-beta6-dev documentation, accessed August 2, 2025, [https://essentia.upf.edu/algorithms\_reference.html](https://essentia.upf.edu/algorithms_reference.html)  
17. EssentiaExtractor \- MTG projects, accessed August 2, 2025, [https://mtg.github.io/essentia.js/docs/api/EssentiaExtractor.html](https://mtg.github.io/essentia.js/docs/api/EssentiaExtractor.html)  
18. Essentia models — Essentia 2.1-beta6-dev documentation, accessed August 2, 2025, [https://essentia.upf.edu/models.html](https://essentia.upf.edu/models.html)  
19. essentia/src/examples/python/essentia\_python\_tutorial.ipynb at master \- GitHub, accessed August 2, 2025, [https://github.com/MTG/essentia/blob/master/src/examples/python/essentia\_python\_tutorial.ipynb](https://github.com/MTG/essentia/blob/master/src/examples/python/essentia_python_tutorial.ipynb)  
20. Automatic home video editing on music \- University of Twente Student Theses, accessed August 2, 2025, [https://essay.utwente.nl/78691/1/weers\_BA\_EEMCS.pdf](https://essay.utwente.nl/78691/1/weers_BA_EEMCS.pdf)  
21. Quick presentation — MoviePy documentation, accessed August 2, 2025, [https://zulko.github.io/moviepy/getting\_started/quick\_presentation.html](https://zulko.github.io/moviepy/getting_started/quick_presentation.html)  
22. MoviePy – Concatenating multiple Video Files \- GeeksforGeeks, accessed August 2, 2025, [https://www.geeksforgeeks.org/python/moviepy-concatenating-multiple-video-files/](https://www.geeksforgeeks.org/python/moviepy-concatenating-multiple-video-files/)  
23. Automating Content Creation with Python: Editing with MoviePy \- DEV Community, accessed August 2, 2025, [https://dev.to/viniciusenari/automating-content-creation-with-python-a-guide-to-building-a-twitch-highlights-bot-part-3-pk9](https://dev.to/viniciusenari/automating-content-creation-with-python-a-guide-to-building-a-twitch-highlights-bot-part-3-pk9)  
24. Introduction to MoviePy \- Python \- GeeksforGeeks, accessed August 2, 2025, [https://www.geeksforgeeks.org/python/introduction-to-moviepy/](https://www.geeksforgeeks.org/python/introduction-to-moviepy/)  
25. Concatenate Videoclips with python \- GitHub Gist, accessed August 2, 2025, [https://gist.github.com/samyarmodabber/a40874d5f77a6bb54fd2d948481e3b39](https://gist.github.com/samyarmodabber/a40874d5f77a6bb54fd2d948481e3b39)  
26. Efficiency Disparity Between MoviePy and FFmpeg · Issue \#2165 \- GitHub, accessed August 2, 2025, [https://github.com/Zulko/moviepy/issues/2165](https://github.com/Zulko/moviepy/issues/2165)  
27. Is using just ffmpeg be faster than moviepy \- Reddit, accessed August 2, 2025, [https://www.reddit.com/r/moviepy/comments/t1sm6k/is\_using\_just\_ffmpeg\_be\_faster\_than\_moviepy/](https://www.reddit.com/r/moviepy/comments/t1sm6k/is_using_just_ffmpeg_be_faster_than_moviepy/)  
28. Video editing with Python | Hacker News, accessed August 2, 2025, [https://news.ycombinator.com/item?id=16297295](https://news.ycombinator.com/item?id=16297295)  
29. ExpressEdit: Video Editing with Natural Language and Sketching \- CEUR-WS.org, accessed August 2, 2025, [https://ceur-ws.org/Vol-3660/paper5.pdf](https://ceur-ws.org/Vol-3660/paper5.pdf)