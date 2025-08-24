"""AI Output Logger - Captures all AI analysis for transparency and debugging."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import threading

logger = logging.getLogger(__name__)


class AIOutputLogger:
    """Singleton logger for capturing all AI interactions and analysis."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the AI output logger."""
        if not hasattr(self, 'initialized'):
            self.entries: List[Dict[str, Any]] = []
            self.project_id: Optional[str] = None
            self.user_prompt: Optional[str] = None
            self.start_time = datetime.now()
            self.output_path: Optional[Path] = None
            self.token_count = 0
            self.initialized = True
    
    def set_project(self, project_id: str, user_prompt: str, output_dir: str = "data/renders", auto_save: bool = True):
        """Set the current project context.
        
        Args:
            project_id: Unique project identifier
            user_prompt: User's original request
            output_dir: Directory for output files
            auto_save: If True, save report after each log entry
        """
        self.project_id = project_id
        self.user_prompt = user_prompt
        self.output_path = Path(output_dir) / f"{project_id}_ai_analysis.txt"
        self.start_time = datetime.now()
        self.entries = []
        self.auto_save = auto_save
        logger.info(f"AI Output Logger initialized for project {project_id}")
        logger.info(f"AI analysis will be saved to: {self.output_path}")
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log_visual_analysis(self, file_path: str, analysis: Dict[str, Any], 
                           prompt: Optional[str] = None, raw_response: Optional[str] = None):
        """Log visual analysis from Gemini.
        
        Args:
            file_path: Path to analyzed media file
            analysis: Parsed analysis results
            prompt: Full prompt sent to LLM
            raw_response: Raw API response text
        """
        # Skip if logger not initialized
        if not self.project_id:
            logger.debug(f"Skipping visual analysis log - logger not initialized")
            return
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "visual_analysis",
            "file": file_path,
            "analysis": analysis,
            "prompt": prompt,
            "raw_response": raw_response
        }
        self.entries.append(entry)
        logger.debug(f"Logged visual analysis for {file_path}")
        self._auto_save_if_enabled()
    
    def log_audio_analysis(self, file_path: str, analysis_type: str, 
                          analysis: Dict[str, Any], prompt: Optional[str] = None,
                          raw_response: Optional[str] = None):
        """Log audio analysis (technical or semantic).
        
        Args:
            file_path: Path to analyzed audio file
            analysis_type: 'technical' (Librosa) or 'semantic' (Gemini)
            analysis: Analysis results
            prompt: Full prompt sent to LLM (for semantic analysis)
            raw_response: Raw API response if applicable
        """
        # Skip if logger not initialized
        if not self.project_id:
            logger.debug(f"Skipping {analysis_type} audio analysis log - logger not initialized")
            return
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": f"audio_analysis_{analysis_type}",
            "file": file_path,
            "analysis": analysis,
            "prompt": prompt,
            "raw_response": raw_response
        }
        self.entries.append(entry)
        logger.debug(f"Logged {analysis_type} audio analysis for {file_path}")
        self._auto_save_if_enabled()
    
    def log_edit_plan(self, plan: Dict[str, Any], prompt: str, 
                     raw_response: Optional[str] = None):
        """Log AI-generated edit plan.
        
        Args:
            plan: Parsed edit plan
            prompt: Prompt sent to AI
            raw_response: Raw API response
        """
        # Skip if logger not initialized
        if not self.project_id:
            logger.debug("Skipping edit plan log - logger not initialized")
            return
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "edit_plan",
            "prompt": prompt,  # Store full prompt
            "plan": plan,
            "raw_response": raw_response
        }
        self.entries.append(entry)
        logger.debug("Logged edit plan")
        self._auto_save_if_enabled()
    
    def log_evaluation(self, video_path: str, evaluation: Dict[str, Any], 
                      iteration: int = 0, prompt: Optional[str] = None,
                      raw_response: Optional[str] = None):
        """Log video evaluation results.
        
        Args:
            video_path: Path to evaluated video
            evaluation: Evaluation results
            iteration: Refinement iteration number
            prompt: Full prompt sent to LLM
            raw_response: Raw API response
        """
        # Skip if logger not initialized
        if not self.project_id:
            logger.debug(f"Skipping evaluation log for iteration {iteration} - logger not initialized")
            return
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "evaluation",
            "iteration": iteration,
            "video": video_path,
            "evaluation": evaluation,
            "prompt": prompt,
            "raw_response": raw_response
        }
        self.entries.append(entry)
        logger.debug(f"Logged evaluation for iteration {iteration}")
        self._auto_save_if_enabled()
    
    def log_refinement(self, feedback: str, commands: Dict[str, Any], 
                      iteration: int = 0, prompt: Optional[str] = None):
        """Log refinement decisions.
        
        Args:
            feedback: Feedback being addressed
            commands: Edit commands generated
            iteration: Refinement iteration number
            prompt: Full prompt sent to LLM
        """
        # Skip if logger not initialized
        if not self.project_id:
            logger.debug(f"Skipping refinement log for iteration {iteration} - logger not initialized")
            return
            
        entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "refinement",
            "iteration": iteration,
            "feedback": feedback,
            "commands": commands,
            "prompt": prompt
        }
        self.entries.append(entry)
        logger.debug(f"Logged refinement for iteration {iteration}")
        self._auto_save_if_enabled()
    
    def add_token_count(self, tokens: int):
        """Add to the total token count.
        
        Args:
            tokens: Number of tokens used in an API call
        """
        self.token_count += tokens
    
    def generate_report(self, final_video_path: str, total_duration: float) -> str:
        """Generate the comprehensive AI analysis report.
        
        Args:
            final_video_path: Path to the final rendered video
            total_duration: Video duration in seconds
            
        Returns:
            The complete report as a string
        """
        processing_time = (datetime.now() - self.start_time).total_seconds()
        
        report = []
        report.append("=" * 80)
        report.append("MEMORY MOVIE AI ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Project ID: {self.project_id}")
        report.append(f"Created: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"User Prompt: {self.user_prompt}")
        report.append("")
        
        # Group entries by phase
        visual_entries = [e for e in self.entries if e['type'] == 'visual_analysis']
        audio_entries = [e for e in self.entries if 'audio_analysis' in e['type']]
        edit_entries = [e for e in self.entries if e['type'] == 'edit_plan']
        eval_entries = [e for e in self.entries if e['type'] == 'evaluation']
        refine_entries = [e for e in self.entries if e['type'] == 'refinement']
        
        # Phase 1: Media Analysis
        if visual_entries or audio_entries:
            report.append("=" * 80)
            report.append("PHASE 1: MEDIA ANALYSIS")
            report.append("=" * 80)
            report.append("")
            
            # Visual Analysis
            for entry in visual_entries:
                report.append(f"[Visual Analysis - {Path(entry['file']).name}]")
                report.append(f"Timestamp: {entry['timestamp']}")
                # Include prompt if available
                if 'prompt' in entry and entry['prompt']:
                    report.append("\nPROMPT SENT TO LLM:")
                    report.append("-" * 40)
                    # Include FULL prompt without truncation
                    report.append(entry['prompt'])
                    report.append("-" * 40)
                    report.append("")
                if 'analysis' in entry and entry['analysis']:
                    analysis = entry['analysis']
                    if isinstance(analysis, dict):
                        report.append(f"  Description: {analysis.get('description', 'N/A')}")
                        report.append(f"  Aesthetic Score: {analysis.get('aesthetic_score', 'N/A')}")
                        report.append(f"  Main Subjects: {', '.join(analysis.get('main_subjects', []))}")
                        report.append(f"  Tags: {', '.join(analysis.get('tags', []))}")
                        
                        # Include notable segments for videos
                        if 'notable_segments' in analysis:
                            report.append("  Notable Segments:")
                            for seg in analysis['notable_segments'][:3]:  # First 3 segments
                                report.append(f"    - {seg.get('start_time', 0):.1f}s-{seg.get('end_time', 0):.1f}s: {seg.get('description', '')}")
                report.append("")
            
            # Audio Analysis
            technical_audio = [e for e in audio_entries if 'technical' in e['type']]
            semantic_audio = [e for e in audio_entries if 'semantic' in e['type']]
            
            for entry in technical_audio:
                report.append(f"[Technical Audio Analysis - {Path(entry['file']).name}]")
                report.append(f"Timestamp: {entry['timestamp']}")
                if 'analysis' in entry and entry['analysis']:
                    analysis = entry['analysis']
                    if isinstance(analysis, dict):
                        report.append(f"  Tempo: {analysis.get('tempo_bpm', 'N/A')} BPM")
                        report.append(f"  Duration: {analysis.get('duration', 'N/A')}s")
                        beats = analysis.get('beat_timestamps', [])
                        report.append(f"  Beats Detected: {len(beats)}")
                        if 'vibe' in analysis:
                            vibe = analysis['vibe']
                            report.append(f"  Mood: {vibe.get('mood', 'N/A')}")
                            report.append(f"  Energy: {vibe.get('energy', 'N/A')}")
                report.append("")
            
            for entry in semantic_audio:
                report.append(f"[Semantic Audio Analysis - {Path(entry['file']).name}]")
                report.append(f"Timestamp: {entry['timestamp']}")
                
                # Include prompt if available
                if 'prompt' in entry and entry['prompt']:
                    report.append("\nPROMPT SENT TO LLM:")
                    report.append("-" * 40)
                    # Include FULL prompt without truncation
                    report.append(entry['prompt'])
                    report.append("-" * 40)
                    report.append("")
                    
                if 'analysis' in entry and entry['analysis']:
                    analysis = entry['analysis']
                    if isinstance(analysis, dict):
                        report.append(f"  Summary: {analysis.get('summary', 'N/A')}")
                        report.append(f"  Musical Structure: {analysis.get('musical_structure_summary', 'N/A')}")
                        
                        # Key moments
                        if 'key_moments' in analysis:
                            report.append("  Key Moments:")
                            for moment in analysis['key_moments'][:3]:
                                report.append(f"    - {moment}")
                report.append("")
        
        # Phase 2: Edit Planning
        if edit_entries:
            report.append("=" * 80)
            report.append("PHASE 2: EDIT PLANNING")
            report.append("=" * 80)
            report.append("")
            
            for entry in edit_entries:
                report.append(f"[AI Edit Plan Generated]")
                report.append(f"Timestamp: {entry['timestamp']}")
                
                # Include prompt if available
                if 'prompt' in entry and entry['prompt']:
                    report.append("\nPROMPT SENT TO LLM:")
                    report.append("-" * 40)
                    # Include FULL prompt without truncation
                    report.append(entry['prompt'])
                    report.append("-" * 40)
                    report.append("")
                    
                if 'plan' in entry and entry['plan']:
                    plan = entry['plan']
                    if isinstance(plan, dict):
                        segments = plan.get('segments', [])
                        report.append(f"  Total Segments: {len(segments)}")
                        report.append(f"  Target Duration: {plan.get('total_duration', 'N/A')}s")
                        report.append(f"  Narrative Structure: {plan.get('narrative_structure', 'N/A')}")
                        report.append(f"  Pacing Strategy: {plan.get('pacing_strategy', 'N/A')}")
                        report.append(f"  Music Sync Notes: {plan.get('music_sync_notes', 'N/A')}")
                        report.append(f"  Variety Score: {plan.get('variety_score', 'N/A')}")
                        report.append(f"  Story Coherence: {plan.get('story_coherence', 'N/A')}")
                        
                        # Show all segments with full details
                        report.append("")
                        report.append("  DETAILED SEGMENT PLAN:")
                        report.append("  " + "-" * 76)
                        for i, seg in enumerate(segments):
                            report.append(f"  Segment {i+1}:")
                            report.append(f"    Media ID: {seg.get('media_id', 'N/A')}")
                            report.append(f"    Start Time: {seg.get('start_time', 0):.1f}s")
                            report.append(f"    Duration: {seg.get('duration', 0):.1f}s")
                            if seg.get('trim_start') is not None or seg.get('trim_end') is not None:
                                report.append(f"    Trim: {seg.get('trim_start', 0):.1f}s - {seg.get('trim_end', 'end')}")
                            report.append(f"    Transition: {seg.get('transition_type', 'cut')}")
                            if seg.get('story_beat'):
                                report.append(f"    Story Beat: {seg.get('story_beat')}")
                            if seg.get('reasoning'):
                                report.append(f"    Reasoning: {seg.get('reasoning')}")
                            report.append("")
                report.append("")
        
        # Phase 3: Evaluation & Refinement
        if eval_entries or refine_entries:
            report.append("=" * 80)
            report.append("PHASE 3: EVALUATION & REFINEMENT")
            report.append("=" * 80)
            report.append("")
            
            # Group by iteration
            max_iteration = max([e.get('iteration', 0) for e in eval_entries + refine_entries] + [0])
            
            for iteration in range(max_iteration + 1):
                iter_evals = [e for e in eval_entries if e.get('iteration', 0) == iteration]
                iter_refines = [e for e in refine_entries if e.get('iteration', 0) == iteration]
                
                if iter_evals or iter_refines:
                    report.append(f"[Iteration {iteration + 1}]")
                    
                    for entry in iter_evals:
                        # Include prompt if available
                        if 'prompt' in entry and entry['prompt']:
                            report.append("\n  PROMPT SENT TO LLM:")
                            report.append("  " + "-" * 38)
                            # Show first 1500 chars of prompt
                            prompt_preview = entry['prompt'][:1500]
                            if len(entry['prompt']) > 1500:
                                prompt_preview += "\n  ... [truncated for display, full prompt saved]"
                            # Indent the prompt for better formatting
                            prompt_lines = prompt_preview.split('\n')
                            for line in prompt_lines:
                                report.append(f"  {line}")
                            report.append("  " + "-" * 38)
                            report.append("")
                        
                        if 'evaluation' in entry and entry['evaluation']:
                            eval_data = entry['evaluation']
                            if isinstance(eval_data, dict):
                                report.append(f"  Score: {eval_data.get('overall_score', 'N/A')}/10")
                                report.append(f"  Recommendation: {eval_data.get('recommendation', 'N/A')}")
                                
                                strengths = eval_data.get('strengths', [])
                                if strengths:
                                    report.append("  Strengths:")
                                    for s in strengths[:3]:
                                        report.append(f"    • {s}")
                                
                                issues = eval_data.get('weaknesses', []) + eval_data.get('technical_issues', [])
                                if issues:
                                    report.append("  Issues:")
                                    for issue in issues[:3]:
                                        report.append(f"    • {issue}")
                    
                    for entry in iter_refines:
                        if 'commands' in entry:
                            report.append("  Refinements Applied:")
                            commands = entry['commands']
                            if isinstance(commands, dict):
                                for key, value in commands.items():
                                    report.append(f"    • {key}: {str(value)[:100]}")
                    report.append("")
        
        # Final Summary
        report.append("=" * 80)
        report.append("FINAL OUTPUT SUMMARY")
        report.append("=" * 80)
        report.append(f"Video Path: {final_video_path}")
        report.append(f"Duration: {total_duration:.2f} seconds")
        report.append(f"Total Processing Time: {processing_time:.2f} seconds")
        report.append(f"AI API Calls: {len(self.entries)}")
        if self.token_count > 0:
            report.append(f"Estimated Tokens Used: {self.token_count}")
        report.append("")
        report.append("=" * 80)
        report.append(f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def save_report(self, final_video_path: str, total_duration: float) -> str:
        """Generate and save the AI analysis report.
        
        Args:
            final_video_path: Path to the final rendered video
            total_duration: Video duration in seconds
            
        Returns:
            Path to the saved report file
        """
        if not self.output_path:
            raise ValueError("Output path not set. Call set_project() first.")
        
        report = self.generate_report(final_video_path, total_duration)
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the report
        with open(self.output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"AI analysis report saved to {self.output_path}")
        return str(self.output_path)
    
    def _auto_save_if_enabled(self):
        """Save the report immediately if auto-save is enabled."""
        if not hasattr(self, 'output_path') or not self.output_path:
            logger.debug("Auto-save skipped: output path not set")
            return
            
        if not hasattr(self, 'auto_save') or not self.auto_save:
            logger.debug("Auto-save skipped: auto_save is disabled")
            return
            
        try:
            # Generate partial report with placeholder values
            report = self.generate_report(
                final_video_path="[In Progress]",
                total_duration=0
            )
            
            # Save the current state
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(report)
                f.write("\n\n[Report is being updated in real-time...]")
            
            logger.info(f"Auto-saved AI analysis to {self.output_path} ({len(self.entries)} entries)")
        except Exception as e:
            logger.error(f"Failed to auto-save report to {self.output_path}: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def reset(self):
        """Reset the logger for a new project."""
        self.entries = []
        self.project_id = None
        self.user_prompt = None
        self.start_time = datetime.now()
        self.output_path = None
        self.token_count = 0
        self.auto_save = True


# Global singleton instance
ai_logger = AIOutputLogger()