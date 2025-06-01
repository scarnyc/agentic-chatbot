#!/usr/bin/env python3
"""
Writing tools that call GPT-4o-mini for content generation.
Provides intelligent writing assistance for various content types.
"""

import logging
import os
import re
from typing import Dict, Any, Optional
from langchain.tools import tool
import openai

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = None
try:
    openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
except Exception as e:
    logger.warning(f"Could not initialize OpenAI client: {e}")

def detect_writing_request(prompt: str) -> Dict[str, Any]:
    """
    Analyze a prompt to detect writing requests and extract relevant details.
    
    Args:
        prompt: User's input prompt
        
    Returns:
        Dictionary with analysis results
    """
    prompt_lower = prompt.lower()
    
    # Define writing request patterns
    writing_patterns = {
        'email': ['email', 'e-mail', 'message to', 'write to', 'send to'],
        'blog_post': ['blog post', 'blog', 'article', 'write about'],
        'linkedin': ['linkedin', 'professional post', 'career post'],
        'letter': ['letter', 'formal letter', 'business letter'],
        'proposal': ['proposal', 'business proposal', 'project proposal'],
        'essay': ['essay', 'academic writing', 'research paper'],
        'social_media': ['tweet', 'facebook post', 'instagram', 'social media'],
        'marketing': ['ad copy', 'marketing', 'sales copy', 'promotional'],
        'report': ['report', 'summary', 'analysis', 'findings']
    }
    
    # Tone indicators
    tone_patterns = {
        'professional': ['professional', 'formal', 'business', 'corporate'],
        'casual': ['casual', 'informal', 'friendly', 'relaxed'],
        'persuasive': ['persuasive', 'convincing', 'compelling', 'sales'],
        'educational': ['educational', 'informative', 'tutorial', 'guide']
    }
    
    # Length indicators
    length_patterns = {
        'short': ['short', 'brief', 'concise', 'quick'],
        'medium': ['medium', 'standard', 'normal'],
        'long': ['long', 'detailed', 'comprehensive', 'extensive']
    }
    
    detected_type = None
    detected_tone = 'professional'  # default
    detected_length = 'medium'  # default
    
    # Detect content type
    for content_type, keywords in writing_patterns.items():
        if any(keyword in prompt_lower for keyword in keywords):
            detected_type = content_type
            break
    
    # Detect tone
    for tone, keywords in tone_patterns.items():
        if any(keyword in prompt_lower for keyword in keywords):
            detected_tone = tone
            break
    
    # Detect length
    for length, keywords in length_patterns.items():
        if any(keyword in prompt_lower for keyword in keywords):
            detected_length = length
            break
    
    # Check for general writing indicators
    general_writing_keywords = [
        'write', 'draft', 'compose', 'create', 'help me write',
        'can you write', 'please write', 'generate', 'produce'
    ]
    
    is_writing_request = (
        detected_type is not None or 
        any(keyword in prompt_lower for keyword in general_writing_keywords)
    )
    
    return {
        'is_writing_request': is_writing_request,
        'content_type': detected_type or 'general',
        'tone': detected_tone,
        'length': detected_length,
        'original_prompt': prompt
    }

@tool
def analyze_writing_request(prompt: str) -> str:
    """
    Analyze a user prompt to detect if it's a writing request and extract key details.
    
    Args:
        prompt: The user's input prompt to analyze
        
    Returns:
        Analysis results indicating if it's a writing request and extracted details
    """
    try:
        analysis = detect_writing_request(prompt)
        
        if analysis['is_writing_request']:
            return f"""Writing request detected!

**Content Type:** {analysis['content_type']}
**Suggested Tone:** {analysis['tone']}
**Suggested Length:** {analysis['length']}
**Original Request:** {analysis['original_prompt'][:100]}...

This appears to be a request for writing assistance. I can help generate this content using the generate_content or smart_writing_assistant tools."""
        else:
            return "No writing request detected in this prompt."
            
    except Exception as e:
        logger.error(f"Error analyzing writing request: {e}")
        return f"Error analyzing prompt: {str(e)}"

@tool
def generate_content(content_type: str, prompt: str, tone: str = "professional", 
                    length: str = "medium", additional_context: str = "") -> str:
    """
    Generate content using GPT-4o-mini based on specified parameters.
    
    Args:
        content_type: Type of content (email, blog_post, linkedin, etc.)
        prompt: The specific request or topic
        tone: Writing tone (professional, casual, persuasive, educational)
        length: Content length (short, medium, long)
        additional_context: Any additional context or requirements
        
    Returns:
        Generated content based on the parameters
    """
    try:
        if not openai_client:
            return "OpenAI client not available. Please ensure OPENAI_API_KEY is set."
        
        # Build the system prompt based on content type
        content_templates = {
            'email': "You are writing a professional email. Be clear, concise, and appropriate for business communication.",
            'blog_post': "You are writing a blog post. Create engaging, informative content with a clear structure.",
            'linkedin': "You are writing a LinkedIn post. Be professional yet engaging, suitable for career networking.",
            'letter': "You are writing a formal letter. Use proper business letter format and tone.",
            'proposal': "You are writing a business proposal. Be persuasive, detailed, and professional.",
            'social_media': "You are writing social media content. Be engaging, concise, and platform-appropriate.",
            'marketing': "You are writing marketing copy. Be persuasive, benefit-focused, and action-oriented.",
            'report': "You are writing a professional report. Be factual, well-structured, and analytical."
        }
        
        system_prompt = content_templates.get(content_type, 
            "You are a professional writing assistant. Create high-quality content based on the user's request.")
        
        # Add tone and length guidance
        tone_guidance = {
            'professional': "Use a professional, formal tone appropriate for business contexts.",
            'casual': "Use a casual, friendly tone that feels natural and approachable.",
            'persuasive': "Use a persuasive tone that convinces and motivates the reader.",
            'educational': "Use an educational tone that informs and teaches clearly."
        }
        
        length_guidance = {
            'short': "Keep the content brief and concise, around 50-150 words.",
            'medium': "Write a moderate length piece, around 150-400 words.",
            'long': "Create comprehensive, detailed content, 400+ words."
        }
        
        full_system_prompt = f"""{system_prompt}

{tone_guidance.get(tone, '')}
{length_guidance.get(length, '')}

{additional_context if additional_context else ''}

Please generate content that is well-structured, error-free, and appropriate for the specified context."""
        
        # Generate content using GPT-4o-mini
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        generated_content = response.choices[0].message.content
        
        return f"""**Generated {content_type.replace('_', ' ').title()}:**

{generated_content}

---
*Generated using GPT-4o-mini with {tone} tone, {length} length*"""
        
    except Exception as e:
        logger.error(f"Error generating content: {e}")
        return f"Error generating content: {str(e)}"

@tool
def smart_writing_assistant(prompt: str) -> str:
    """
    Intelligent writing assistant that automatically detects writing requests and generates appropriate content.
    
    Args:
        prompt: User's request which may contain a writing task
        
    Returns:
        Generated content or guidance based on the detected writing request
    """
    try:
        # First analyze the prompt
        analysis = detect_writing_request(prompt)
        
        if not analysis['is_writing_request']:
            return """I don't detect a specific writing request in your prompt. 

To help you with writing, try requests like:
- "Write an email to..."
- "Create a LinkedIn post about..."
- "Draft a blog post on..."
- "Compose a professional letter for..."

What would you like me to help you write?"""
        
        # If it's a writing request, generate the content
        return generate_content.invoke({
            "content_type": analysis['content_type'],
            "prompt": analysis['original_prompt'],
            "tone": analysis['tone'],
            "length": analysis['length'],
            "additional_context": ""
        })
        
    except Exception as e:
        logger.error(f"Error in smart writing assistant: {e}")
        return f"Error processing your request: {str(e)}"

@tool
def get_writing_templates() -> str:
    """
    Get available writing templates and examples for different content types.
    
    Returns:
        List of available templates and usage examples
    """
    return """**📝 Writing Templates & Examples**

**📧 Email Templates:**
- Professional inquiry: "I'm reaching out regarding..."
- Follow-up: "Following up on our previous conversation..."
- Thank you: "Thank you for your time and consideration..."
- Feedback request: "I would appreciate your feedback on..."

**💼 LinkedIn Posts:**
- Career milestone: "Excited to share that I've just..."
- Industry insight: "Here's what I've learned about [industry trend]..."
- Professional achievement: "Proud to announce that our team..."
- Thought leadership: "After [X years] in [industry], I've observed..."

**📄 Blog Posts:**
- How-to guide: "Step-by-step guide to [topic]"
- Industry analysis: "The current state of [industry] and what's next"
- Personal story: "What I learned from [experience]"
- Tips and tricks: "5 ways to improve your [skill/process]"

**🏢 Business Writing:**
- Proposal: "Executive summary, problem statement, solution..."
- Report: "Introduction, methodology, findings, recommendations..."
- Meeting summary: "Agenda items, decisions made, action items..."
- Business letter: "Formal introduction, purpose, request, closing..."

**📈 Marketing Content:**
- Product description: "Features, benefits, value proposition..."
- Social media: "Engaging hooks, clear message, call-to-action..."
- Ad copy: "Attention-grabbing headline, persuasive body, strong CTA..."

**Usage Examples:**
- "Write a professional email to request a meeting about the project timeline"
- "Create a LinkedIn post celebrating our team's recent product launch"
- "Draft a blog post explaining the benefits of remote work for productivity"
- "Compose a business proposal for implementing a new customer service system"

**Need help with any of these? Just ask me to write the specific content you need!**"""

# Export tools for LangChain integration
__all__ = ['analyze_writing_request', 'generate_content', 'smart_writing_assistant', 'get_writing_templates']