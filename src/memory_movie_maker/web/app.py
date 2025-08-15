"""Gradio web interface for Memory Movie Maker."""

import gradio as gr
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import tempfile
import shutil
from pathlib import Path
import logging
import json

from ..agents.root_agent import RootAgent
from ..models.project_state import ProjectState


logger = logging.getLogger(__name__)


class MemoryMovieMakerApp:
    """Gradio application for Memory Movie Maker."""
    
    def __init__(self):
        """Initialize the application."""
        self.root_agent = RootAgent()
        self.current_project_state: Optional[ProjectState] = None
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"Initialized app with temp directory: {self.temp_dir}")
    
    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""
        with gr.Blocks(title="Memory Movie Maker", theme=gr.themes.Soft()) as app:
            gr.Markdown(
                """
                # <� Memory Movie Maker
                
                Transform your photos and videos into beautiful memory movies with AI-powered editing.
                """
            )
            
            with gr.Tabs():
                # Tab 1: Create New Video
                with gr.TabItem("Create New Video"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            media_files = gr.File(
                                label="Upload Media Files",
                                file_count="multiple",
                                file_types=["image", "video"],
                                elem_id="media_upload"
                            )
                            
                            music_file = gr.File(
                                label="Background Music (Optional)",
                                file_count="single",
                                file_types=["audio"],
                                elem_id="music_upload"
                            )
                            
                            prompt = gr.Textbox(
                                label="Describe Your Video",
                                placeholder="E.g., Create a romantic vacation montage with smooth transitions",
                                lines=3
                            )
                            
                            with gr.Row():
                                duration = gr.Slider(
                                    minimum=10,
                                    maximum=300,
                                    value=60,
                                    step=5,
                                    label="Duration (seconds)"
                                )
                                
                                style = gr.Dropdown(
                                    choices=["auto", "smooth", "dynamic", "fast"],
                                    value="auto",
                                    label="Style"
                                )
                            
                            auto_refine = gr.Checkbox(
                                label="Auto-refine for best quality",
                                value=True
                            )
                            
                            create_btn = gr.Button(
                                "<� Create Memory Movie",
                                variant="primary",
                                size="lg"
                            )
                        
                        with gr.Column(scale=1):
                            output_video = gr.Video(
                                label="Generated Video",
                                elem_id="output_video"
                            )
                            
                            creation_log = gr.Textbox(
                                label="Creation Log",
                                lines=10,
                                max_lines=20,
                                interactive=False
                            )
                            
                            with gr.Row():
                                download_btn = gr.Button(
                                    "=� Download Video",
                                    visible=False
                                )
                                
                                refine_btn = gr.Button(
                                    "=' Refine Video",
                                    visible=False
                                )
                    
                    # Event handlers
                    create_btn.click(
                        fn=self.create_video,
                        inputs=[media_files, music_file, prompt, duration, style, auto_refine],
                        outputs=[output_video, creation_log, download_btn, refine_btn]
                    )
                
                # Tab 2: Refine Existing Video
                with gr.TabItem("Refine Video"):
                    with gr.Row():
                        with gr.Column():
                            gr.Markdown(
                                """
                                ### Current Video
                                Click "Refine Video" from the Create tab to load a video here.
                                """
                            )
                            
                            current_video = gr.Video(
                                label="Current Video",
                                interactive=False
                            )
                            
                            evaluation_results = gr.Textbox(
                                label="Evaluation Results",
                                lines=8,
                                interactive=False
                            )
                            
                            feedback = gr.Textbox(
                                label="Your Feedback",
                                placeholder="E.g., Make the transitions slower, extend clips at 0:15",
                                lines=3
                            )
                            
                            apply_feedback_btn = gr.Button(
                                "( Apply Feedback",
                                variant="primary"
                            )
                        
                        with gr.Column():
                            refined_video = gr.Video(
                                label="Refined Video"
                            )
                            
                            refinement_log = gr.Textbox(
                                label="Refinement Log",
                                lines=10,
                                interactive=False
                            )
                    
                    # Connect refine button to load current video
                    refine_btn.click(
                        fn=self.load_for_refinement,
                        inputs=[output_video],
                        outputs=[current_video, evaluation_results]
                    )
                    
                    apply_feedback_btn.click(
                        fn=self.apply_feedback,
                        inputs=[feedback],
                        outputs=[refined_video, refinement_log]
                    )
                
                # Tab 3: Examples & Help
                with gr.TabItem("Examples & Help"):
                    gr.Markdown(
                        """
                        ## =� How to Use
                        
                        ### 1. Upload Your Media
                        - Select multiple photos and/or videos
                        - Optionally add background music
                        - Supported formats: JPG, PNG, MP4, MOV, MP3, WAV
                        
                        ### 2. Describe Your Vision
                        - Be specific about the mood and style
                        - Mention any special requirements
                        - Examples:
                          - "Create an energetic sports montage with fast cuts"
                          - "Make a calm, nostalgic family video with soft transitions"
                          - "Dynamic travel video synced to the beat"
                        
                        ### 3. Choose Settings
                        - **Duration**: Target length of your video
                        - **Style**: 
                          - Auto: AI chooses based on content
                          - Smooth: Gentle transitions, slower pacing
                          - Dynamic: Beat-synced, energetic cuts
                          - Fast: Quick cuts, high energy
                        - **Auto-refine**: Automatically improve quality (slower but better)
                        
                        ### 4. Refine Your Video
                        - Review the AI evaluation
                        - Provide specific feedback
                        - Examples:
                          - "Make clip at 0:15 longer by 2 seconds"
                          - "Use crossfade transition at 0:30"
                          - "Remove the clip at 0:45"
                        
                        ## <� Tips for Best Results
                        
                        1. **Media Quality**: Use high-resolution photos/videos
                        2. **Variety**: Include diverse shots and angles
                        3. **Music Match**: Choose music that fits your vision
                        4. **Clear Prompts**: Be specific about what you want
                        5. **Iterate**: Use refinement to perfect your video
                        
                        ## � Keyboard Shortcuts
                        
                        - `Space`: Play/pause video
                        - `�/�`: Seek backward/forward
                        - `�/�`: Volume up/down
                        """
                    )
            
            gr.Markdown(
                """
                ---
                <center>
                Made with d using Google ADK and Gemini | 
                <a href="https://github.com/your-repo/memory-movie-maker">GitHub</a>
                </center>
                """
            )
        
        return app
    
    async def create_video_async(
        self,
        media_files: List[str],
        music_file: Optional[str],
        prompt: str,
        duration: int,
        style: str,
        auto_refine: bool
    ) -> Tuple[str, str]:
        """Create video asynchronously."""
        try:
            # Prepare media paths
            media_paths = []
            if media_files:
                for file in media_files:
                    if isinstance(file, dict) and 'name' in file:
                        media_paths.append(file['name'])
                    else:
                        media_paths.append(str(file))
            
            music_path = None
            if music_file:
                if isinstance(music_file, dict) and 'name' in music_file:
                    music_path = music_file['name']
                else:
                    music_path = str(music_file)
            
            # Create video
            result = await self.root_agent.create_memory_movie(
                media_paths=media_paths,
                user_prompt=prompt,
                music_path=music_path,
                target_duration=int(duration),
                style=style,
                auto_refine=auto_refine
            )
            
            if result["status"] == "success":
                self.current_project_state = result["project_state"]
                
                # Create log
                log_lines = [
                    " Video created successfully!",
                    f"=� Output: {Path(result['video_path']).name}",
                    f"� Duration: {duration} seconds",
                    f"<� Style: {style}"
                ]
                
                if auto_refine:
                    log_lines.extend([
                        "",
                        "= Auto-refinement Results:",
                        f"   Iterations: {result.get('refinement_iterations', 0)}",
                        f"   Final Score: {result.get('final_score', 'N/A')}/10"
                    ])
                    
                    if self.current_project_state.evaluation_results:
                        eval_results = self.current_project_state.evaluation_results
                        if eval_results.get('strengths'):
                            log_lines.append("\n Strengths:")
                            for strength in eval_results['strengths'][:3]:
                                log_lines.append(f"  ✓ {strength}")
                        
                        if eval_results.get('weaknesses'):
                            log_lines.append("\n� Areas for improvement:")
                            for weakness in eval_results['weaknesses'][:2]:
                                log_lines.append(f"  • {weakness}")
                
                return result['video_path'], "\n".join(log_lines)
            else:
                return None, f"L Error: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            return None, f"L Error: {str(e)}"
    
    def create_video(
        self,
        media_files: List[str],
        music_file: Optional[str],
        prompt: str,
        duration: int,
        style: str,
        auto_refine: bool
    ) -> Tuple[Optional[str], str, gr.update, gr.update]:
        """Create video (synchronous wrapper)."""
        if not media_files:
            return None, "L Please upload media files", gr.update(visible=False), gr.update(visible=False)
        
        if not prompt:
            return None, "L Please describe your video", gr.update(visible=False), gr.update(visible=False)
        
        # Run async function
        video_path, log = asyncio.run(
            self.create_video_async(media_files, music_file, prompt, duration, style, auto_refine)
        )
        
        if video_path:
            return video_path, log, gr.update(visible=True), gr.update(visible=True)
        else:
            return None, log, gr.update(visible=False), gr.update(visible=False)
    
    def load_for_refinement(
        self,
        current_video_path: Optional[str]
    ) -> Tuple[Optional[str], str]:
        """Load video for refinement."""
        if not current_video_path or not self.current_project_state:
            return None, "L No video to refine. Create a video first."
        
        # Get evaluation results
        if self.current_project_state.evaluation_results:
            eval_results = self.current_project_state.evaluation_results
            
            eval_text = [
                f"=� Overall Score: {eval_results.get('overall_score', 'N/A')}/10",
                f"=� Recommendation: {eval_results.get('recommendation', 'N/A').replace('_', ' ').title()}",
                ""
            ]
            
            if eval_results.get('strengths'):
                eval_text.append(" Strengths:")
                for strength in eval_results['strengths']:
                    eval_text.append(f"  • {strength}")
                eval_text.append("")
            
            if eval_results.get('weaknesses'):
                eval_text.append("❌ Issues:")
                for weakness in eval_results['weaknesses']:
                    eval_text.append(f"  • {weakness}")
                eval_text.append("")
            
            if eval_results.get('specific_edits'):
                eval_text.append("✏️ Suggested Edits:")
                for edit in eval_results['specific_edits'][:5]:
                    eval_text.append(f"  • [{edit['timestamp']}] {edit['issue']}")
                    eval_text.append(f"    → {edit['suggestion']}")
            
            return current_video_path, "\n".join(eval_text)
        else:
            return current_video_path, "No evaluation results available. The video was likely created without auto-refinement."
    
    async def apply_feedback_async(
        self,
        feedback: str
    ) -> Tuple[Optional[str], str]:
        """Apply feedback asynchronously."""
        try:
            if not self.current_project_state:
                return None, "L No project loaded"
            
            result = await self.root_agent.process_user_feedback(
                project_state=self.current_project_state,
                user_feedback=feedback
            )
            
            if result["status"] == "success":
                self.current_project_state = result["project_state"]
                
                log = [
                    " Feedback applied successfully!",
                    f"=� New video: {Path(result['video_path']).name}",
                    "",
                    "Changes applied based on your feedback."
                ]
                
                return result['video_path'], "\n".join(log)
            else:
                return None, f"L Error: {result.get('error', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Feedback processing failed: {e}")
            return None, f"L Error: {str(e)}"
    
    def apply_feedback(
        self,
        feedback: str
    ) -> Tuple[Optional[str], str]:
        """Apply feedback (synchronous wrapper)."""
        if not feedback:
            return None, "L Please provide feedback"
        
        video_path, log = asyncio.run(self.apply_feedback_async(feedback))
        return video_path, log
    
    def cleanup(self):
        """Clean up temporary files."""
        try:
            shutil.rmtree(self.temp_dir)
            logger.info("Cleaned up temporary directory")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


def launch_app(share: bool = False, port: int = 7860):
    """Launch the Gradio application.
    
    Args:
        share: If True, create a public share link
        port: Port to run the server on
    """
    app_instance = MemoryMovieMakerApp()
    interface = app_instance.create_interface()
    
    try:
        interface.launch(
            share=share,
            server_port=port,
            server_name="0.0.0.0",
            show_error=True
        )
    finally:
        app_instance.cleanup()


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    launch_app(share=False)